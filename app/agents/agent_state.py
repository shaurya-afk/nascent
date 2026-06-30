from typing import TypedDict
from uuid import UUID

class ContextFile(TypedDict):
    path: str
    absolute_path: str
    reason: str
    content: str | None

class Context(TypedDict):
    modify: list[ContextFile]
    create: list[ContextFile]
    delete: list[ContextFile]

class FileOperation(TypedDict):
    path: str
    operation: str
    reason: str

class Plan(TypedDict):
    summary: str
    modify: list[FileOperation]
    create: list[FileOperation]
    delete: list[FileOperation]
    database_changes: list[str]
    api_changes: list[str]


class DiffSummary(TypedDict):
    files_changed: str
    additions: str
    deletions: str

class GitDiff(TypedDict):
    patch: str
    files: list[str]
    summary: DiffSummary

class AgentState(TypedDict):
    repo_id: str | None
    repo_url: str

    user_id: UUID
    user_query: str |None

    repo_cached: bool

    summaries: list[dict]

    workspace: str
    context: Context

    plan: Plan 
    plan_approved: bool
    planner_feedback: str

    diff: GitDiff
    diff_approved: bool
    diff_feedback: str | None

    commit_sha: str | None
    branch_name: str| None
    pull_request_url: str| None
    installation_id: int| None