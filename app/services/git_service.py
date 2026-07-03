from pathlib import Path
from git import Repo
from unidiff import PatchSet

class GitService:
    def __init__(self, workspace: str) -> None:
        self.workspace = Path(workspace)
        self.repo = Repo(self.workspace)
        self.origin = self.repo.remote("origin")
        self.original_origin_url = next(self.origin.urls)

    def get_diff(self) -> dict:
        patch = self.repo.git.diff()
        parsed = PatchSet.from_string(patch)

        changed_files: list[str] = []
        additions = 0
        deletions = 0

        for file in parsed:
            changed_files.append(file.path)

            additions += file.added
            deletions += file.removed

        return {
            "patch": patch,
            "files": changed_files,
            "summary": {
                "files_changed": len(changed_files),
                "additions": additions,
                "deletions": deletions,
            },
        }
    
    def commit(self, message: str):
        self.repo.git.add(A=True)

        commit = self.repo.index.commit(message)

        return commit.hexsha
    
    def get_origin_url(self) -> str:
        origin = self.repo.remote("origin")
        return next(origin.urls)
    
    def set_origin_url(self, url: str):
        origin = self.repo.remote("origin")
        origin.set_url(url)

    def build_authenticated_url(self, installation_token: str) -> str:
        installation_token = installation_token.strip()

        origin_url = self.get_origin_url()
        prefix = "https://"

        if not origin_url.startswith(prefix):
            raise ValueError("only https remotes are supported.")
        
        remainder = origin_url[len(prefix):]

        if "@" in remainder:
            remainder = remainder.split("@", 1)[1]

        return f"{prefix}x-access-token:{installation_token}@{remainder}"
    
    def create_branch(self, branch_name: str):
        self.repo.git.checkout("-b", branch_name)

    def push(self, branch_name: str, installation_token: str):
        original = self.original_origin_url

        authenticated = self.build_authenticated_url(installation_token)

        print(repr(original))
        print(repr(authenticated))
        print(repr(installation_token))

        try:
            self.set_origin_url(authenticated)

            self.origin.push(
                refspec=branch_name
            )
        finally:
            self.set_origin_url(original)
    
