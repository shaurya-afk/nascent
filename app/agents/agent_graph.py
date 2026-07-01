from app.agents.agent_nodes import AgentNodes
from app.agents.agent_state import AgentState

from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import async_sessionmaker


class AgentGraph:
    def __init__(self, session_factor: async_sessionmaker) -> None:
        self.node = AgentNodes(session_factor)
        self.g = StateGraph(AgentState)

    def build(self):
        self.g.add_node("load_repo", self.node.load_repo)
        self.g.add_node("repo_extract", self.node.run_repo_extraction)
        self.g.add_node("planner", self.node.planner)
        self.g.add_node("context_loader", self.node.context_loader)
        self.g.add_node("clone_repo", self.node.clone_repo)
        self.g.add_node("plan_hitl", self.node.plan_hitl)
        self.g.add_node("gen_code", self.node.generate_code)
        self.g.add_node("diff", self.node.git_diff)
        self.g.add_node("diff_hitl", self.node.diff_hitl)
        self.g.add_node("git_commit", self.node.git_commit)
        self.g.add_node("git_push", self.node.git_push)
        self.g.add_node("cleanup", self.node.clean_workspace)

        self.g.add_edge(START, "load_repo")

        self.g.add_conditional_edges(
            "load_repo",
            self.node.route_repo,
            {"planner": "planner", "extract": "repo_extract"},
        )

        self.g.add_edge("repo_extract", "planner")
        self.g.add_edge("planner", "clone_repo")
        self.g.add_edge("clone_repo", "context_loader")
        self.g.add_edge("context_loader", "plan_hitl")

        self.g.add_conditional_edges(
            "plan_hitl",
            self.node.route_plan,
            {
                "generate":"gen_code",
                "planner":"planner"
            }
        )

        self.g.add_edge("gen_code", "diff")
        self.g.add_edge("diff", "diff_hitl")

        self.g.add_conditional_edges("diff_hitl", self.node.route_diff, {
            "commit":"git_commit",
            "generate":"gen_code"
        })

        self.g.add_edge("git_commit", "git_push")
        self.g.add_edge("git_push", "cleanup")

        self.g.add_edge("cleanup", END)

        return self.g
