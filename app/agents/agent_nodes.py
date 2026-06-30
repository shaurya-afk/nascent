from app.agents.agent_state import AgentState
from app.services.repo_service import RepositoryService
from app.services.git_extraction import GitExtraction
from app.services.git_service import GitService
from app.services.github_service import GitHubService
from app.services.llm import call_llm
from app.models.user import User

from sqlalchemy.ext.asyncio import async_sessionmaker
from langgraph.types import interrupt
from pathlib import Path
from textwrap import dedent
from sqlalchemy import select
from urllib.parse import urlparse
import uuid


class AgentNodes:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.repo_service = RepositoryService()
        # self.db = db
        self.session_factory = session_factory

    async def clone_repo(self, state: AgentState):
        async with self.session_factory() as db:
            git = GitExtraction(state["repo_url"], self.session_factory)
            git._clone_repo()

            return {"workspace": git.workspace}

    async def load_repo(self, state: AgentState):
        async with self.session_factory() as db:
            repo = await self.repo_service.get_all_repo_files(db, state["repo_url"])

        async with self.session_factory() as db:
            print(db.is_active)

        print(f"\nrepo:\n{repo}\n\n")
        if repo:
            print(f"repo id:{repo.id}\n")
            print(f"github url:{repo.github_url}\n")
            print(f"repo files count:{len(repo.files)}\n")

        if repo is None or len(repo.files) == 0:
            return {"repo_cached": False, "repo_id": None, "summaries": []}

        summaries = [
            {"name": file.name, "path": file.path, "summary": file.summary}
            for file in repo.files
        ]

        print(f"LOAD\nsummaries count: {len(summaries)}")

        return {"repo_cached": True, "repo_id": repo.id, "summaries": summaries}

    async def run_repo_extraction(self, state: AgentState):
        async with self.session_factory() as db:
            git_service = GitExtraction(state["repo_url"], self.session_factory)
            res = await git_service.pipeline()

        return {"summaries": res["summary"], "workspace": res["workspace"]}

    def route_repo(self, state: AgentState):
        if state["repo_cached"]:
            return "planner"
        return "extract"

    async def planner(self, state: AgentState):
        prompt = f"""
        You are an expert software architect.

        Your task is NOT to generate code.

        Your task is to analyze the user's request against the repository summary and produce an execution plan for downstream agents.

        ## User Request

        {state["user_query"]}

        ## Repository Summary

        {state["summaries"]}

        ## Instructions

        1. Decide which existing files need to be modified.
        2. Decide which new files need to be created.
        3. Decide whether any existing files should be deleted.
        4. Decide whether database schema changes are required.
        5. Decide whether API endpoints need to be added or modified.
        6. Only reference files that exist in the repository summary.
        7. Always use the exact relative_path provided in the repository summary.
        8. Never invent file paths.
        9. Do NOT generate code.
        10. Return ONLY valid JSON.

        Note: ONLY USE 'create' FOR FILES THAT DO NOT EXIST IN THE REPOSITORY SUMMARY. IF A FILE ALREADY EXISTS, IT MUST BE LISTED UNDER 'modify'.

        Return JSON in exactly this format - use this example ONLY for reference purpose:
        operations are: create, modify, delete

        {{
        "summary": "Short description of the implementation strategy.",

        "modify": [
            {{
            "path": "app/routers/auth.py",
            "operation":"modify",
            "reason": "Authentication endpoints require Google OAuth support."
            }}
        ],

        "create": [
            {{
            "path": "app/services/google_oauth.py",
            "operation":"create",
            "reason": "New service for Google OAuth."
            }}
        ],
        "database_changes": [
            "Add google_id column to users table."
        ],

        "api_changes": [
            "GET /auth/google",
            "GET /auth/google/callback"
        ]
        }}
        """

        res = await call_llm(prompt)

        print(f"PLANNER\n{len(state['summaries'])}")
        return {"plan": res}

    async def context_loader(self, state: AgentState):
        workspace = Path(state["workspace"])

        plan = state["plan"]
        if plan is None:
            raise ValueError("Planner did not return a plan!")

        context = {"modify": [], "create": [], "delete": []}

        # files to edit
        for file in plan.get("modify", []):
            abs_path = workspace / file["path"]

            if not abs_path.exists():
                raise FileNotFoundError(
                    f"{file['path']} does not exist in the cloned repo"
                )

            context["modify"].append(
                {
                    "path": file["path"],
                    "absolute_path": str(abs_path),
                    "reason": file["reason"],
                    "content": abs_path.read_text(encoding="utf-8", errors="ignore"),
                }
            )

        # files to create
        for file in plan.get("create", []):
            context["create"].append(
                {
                    "path": file["path"],
                    "absolute_path": str(workspace / file["path"]),
                    "reason": file["reason"],
                    "content": None,
                }
            )

        # files to delete
        for file in plan.get("delete", []):
            absolute_path = workspace / file["path"]

            context["delete"].append(
                {
                    "path": file["path"],
                    "absolute_path": str(absolute_path),
                    "reason": file["reason"],
                }
            )

        print(f"CONTEXT LOADER\n{len(state['summaries'])}")
        # read those and store in context
        return {"workspace": str(workspace), "context": context}

    def plan_hitl(self, state: AgentState):
        response = interrupt(
            {
                "type": "plan_review",
                "repo_url": state["repo_url"],
                "user_query": state["user_query"],
                "plan": state["plan"],
                "message": "Approve this implementation plan?",
            }
        )

        action = response.get("action")

        if action == "approve":
            return {"plan_approved": True, "planner_feedback": None}

        if action == "reject":
            return {"plan_approved": False, "planner_feedback": response["feedback"]}

    def route_plan(self, state: AgentState):
        if state["plan_approved"]:
            return "generate"
        return "planner"

    def _build_code_generation_prompt(self, state: AgentState) -> str:
        diff_feedback = ""
        if state.get("diff_feedback"):
            diff_feedback = dedent(f"""
                ==========================================================
                    Implementation Feedback

                    The previous implementation was rejected

                    Feedback:
                    {state["diff_feedback"]}

                    Regenerate the implementation using the SAME approved plan while addressing the feedback.
                """)

        database_changes = "\n".join(
            f"- {change}" for change in state["plan"]["database_changes"]
        )

        api_changes = "\n".join(
            f"- {change}" for change in state["plan"]["api_changes"]
        )

        modify_section = ""

        for file in state["context"]["modify"]:
            modify_section += dedent(f"""
            ==================================================

            Path:
            {file["path"]}

            Reason:
            {file["reason"]}

            ---------- BEGIN FILE ----------

            {file["content"]}

            ---------- END FILE ----------

            """)

        create_section = ""

        for file in state["context"]["create"]:
            create_section += dedent(f"""
            ==================================================

            Path:
            {file["path"]}

            Reason:
            {file["reason"]}

            """)

        delete_section = ""

        for file in state["context"]["delete"]:
            delete_section += dedent(f"""
            ==================================================

            Path:
            {file["path"]}

            Reason:
            {file["reason"]}

            """)

        prompt = dedent(f"""
        You are an expert senior software engineer working on an existing production codebase.

        Your task is to implement an already approved engineering plan.

        The planning phase has already been completed and approved.

        ==================================================

        Original User Request

        {state["user_query"]}

        ==================================================

        Approved Goal

        {state["plan"]["summary"]}

        ==================================================

        Database Changes

        {database_changes if database_changes else "None"}

        ==================================================

        API Changes

        {api_changes if api_changes else "None"}

        ==================================================

        Files To Modify

        The following files already exist.

        {modify_section}

        ==================================================

        Files To Create

        The following files do not exist yet.

        {create_section}

        ==================================================

        Files To Delete

        The following files should be removed.

        {delete_section}

        ==================================================

        Implementation Rules

        - Follow the approved plan exactly.
        - Modify ONLY the listed files.
        - Create ONLY the listed files.
        - Delete ONLY the listed files.
        - Do not invent additional files.
        - Do not rename files.
        - Preserve the existing architecture.
        - Preserve the existing coding style.
        - Reuse existing helper functions whenever possible.
        - Avoid unrelated refactoring.
        - Produce production-ready code.
        - Return complete file contents.
        - Never return partial snippets.
        - Return ONLY valid JSON.

        ==================================================

        The response MUST exactly match this schema:

        {{
        "files": [
            {{
            "path": "relative/path.py",
            "operation": "modify",
            "content": "complete file contents"
            }},
            {{
            "path": "relative/path/new_file.py",
            "operation": "create",
            "content": "complete file contents"
            }},
            {{
            "path": "relative/path/old_file.py",
            "operation": "delete"
            }}
        ]
        }}

        If no changes are required, return:

        {{
        "files": []
        }}

        Rules:

        - Always return a top-level object.
        - The object must contain exactly one key named "files".
        - Each file object must contain:
            - path
            - operation
        - "operation" must be one of:
            - modify
            - create
            - delete
        - "content" is REQUIRED for modify and create.
        - "content" MUST NOT be present for delete.
        - Do not include explanations.
        - Do not include markdown.
        - Do not wrap code in triple backticks.
        """)

        prompt += diff_feedback

        return prompt

    async def generate_code(self, state: AgentState):
        prompt = self._build_code_generation_prompt(state)

        response = await call_llm(prompt)

        for file in response["files"]:
            path = Path(state["workspace"]) / file["path"]

            if file["operation"] == "modify":
                path.write_text(file["content"], encoding="utf-8")

            elif file["operation"] == "create":
                path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                path.write_text(
                    file["content"],
                    encoding="utf-8",
                )

            elif file["operation"] == "delete":
                path.unlink()

        return {}

    async def git_diff(self, state: AgentState):
        git = GitService(state["workspace"])

        diff = git.get_diff()

        return {"diff": diff}

    def diff_hitl(self, state: AgentState):
        response = interrupt(
            {
                "type": "diff_review",
                "repo_url": state["repo_url"],
                "user_query": state["user_query"],
                "summary": state["diff"]["summary"],
                "changed_files": state["diff"]["files"],
                "patch": state["diff"]["patch"],
                "message": "Approve these code changes?",
            }
        )

        action = response.get("action")

        if action == "approve":
            return {"diff_approved": True, "diff_feedback": None}
        if action == "reject":
            return {"diff_approved": False, "diff_feedback": response.get("feedback")}

        raise ValueError("unknown action!")

    def route_diff(self, state: AgentState):
        if state["diff_approved"]:
            return "commit"
        return "generate"

    async def git_commit(self, state: AgentState):
        git = GitService(state["workspace"])

        sha = git.commit(state["plan"]["summary"])

        return{
            "commit_sha":sha
        }
    
    async def git_push(self, state: AgentState):
        async with self.session_factory() as db:
            user = await db.scalar(
                select(User).where(
                    User.id == state["user_id"]
                )
            )

        if user is None:
            raise ValueError("user not found")
        
        if user.github_installation_id is None:
            raise ValueError("github app is not connected")
        
        github = GitHubService()

        installation_token = await github.get_installation_token(user.github_installation_id)

        git = GitService(state['workspace'])
        branch_name = f"feature/nascent-{uuid.uuid4().hex[:8]}"

        git.create_branch(branch_name)

        git.push(branch_name, installation_token)

        parsed = urlparse(state["repo_url"])
        owner, repo = parsed.path.strip("/").split("/")
        repo = repo.removesuffix(".git")

        pr_url = await github.create_pull_request(
        installation_token=installation_token,
        owner=owner,
        repo=repo,
        title=state["plan"]["summary"],
        head=branch_name,
        base="main",
        body=f"""
        ## Generated by Nascent

        ### User Request

        {state["user_query"]}

        ### Commit

        {state["commit_sha"]}
        """.strip(),
            )

        return {
            "branch_name": branch_name,
            "pull_request_url": pr_url,
        }