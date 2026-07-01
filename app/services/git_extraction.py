import tempfile
from git import Repo
from pathlib import Path
import shutil

from app.services.llm import call_llm
from app.services.repo_service import RepositoryService


class GitExtraction:
    IGNORE_PATHS = {
        "tests",
        "test",
        "__pycache__",
        "alembic",
        "migrations",
        ".git",
        "node_modules",
        "dist",
        "build",
    }

    def __init__(self, url: str, session) -> None:
        self.workspace = tempfile.mkdtemp()
        self.url = url
        self.session = session

    def _clone_repo(self):
        try:
            Repo.clone_from(self.url, self.workspace)
        except Exception as e:
            raise Exception(f"Failed to clone the git repo: {self.url}\n{e}")

    def _scan_files(self):
        IGNORE_DIRS = {
            ".git",
            ".venv",
            "venv",
            "env",
            "node_modules",
            "dist",
            "build",
            "target",
            ".next",
            ".idea",
            ".vscode",
            "__pycache__",
        }

        CODE_EXTENSIONS = {
            ".py",
            ".java",
            ".kt",
            ".js",
            ".ts",
            ".tsx",
        }

        files = []

        for file in Path(self.workspace).rglob("*"):
            if not file.is_file():
                continue
            if any(part in IGNORE_DIRS for part in file.parts):
                continue
            if file.suffix in CODE_EXTENSIONS:
                files.append(file)

        return files

    def _map_repo(self, files):
        repo_map = []

        for file in files:
            repo_map.append(
                {
                    "name": file.stem,
                    "absolute_path": str(file),
                    "relative_path": str(file.relative_to(self.workspace)),
                }
            )

        return repo_map

    def _read_file(self, repo_map):
        documents = []

        for file in repo_map:
            try:
                with open(
                    file["absolute_path"], "r", encoding="utf-8", errors="ignore"
                ) as f:
                    content = f.read()

                documents.append(
                    {
                        "name": file["name"],
                        "path": file["relative_path"],
                        "content": content,
                    }
                )
            except Exception:
                continue

        return documents

    def _should_summarize(self, path: str, important_path, ignore_path):
        path = path.lower()

        if any(ignore in path for ignore in ignore_path):
            return False
        return any(important in path for important in important_path)

    def _refine_map(self, documents):
        filtered_docs = []

        for doc in documents:
            path = doc["path"].lower()

            if any(ignore in path for ignore in self.IGNORE_PATHS):
                continue

            filtered_docs.append(doc)

        return filtered_docs

    async def _summarized_documents(self, filtered_documents):
        summaries = []

        for doc in filtered_documents:
            content = doc["content"][:3000]

            prompt = f"""
            Summarize this source file.

            Return:
            - purpose
            - major responsibilities
            - key classes/functions

            File:
            {doc["path"]}

            Code:
            {content}
            """

            summary = await call_llm(prompt)

            summaries.append(
                {"name": doc["name"], "path": doc["path"], "summary": summary}
            )

        return summaries

    def _cleanup(self, workspace: str):
        shutil.rmtree(workspace, ignore_errors=True)

    async def pipeline(self):
        try:
            self._clone_repo()
            print("✅ Git repo cloned successfully!\n")

            files = self._scan_files()
            repo_map = self._map_repo(files)
            print("✅ Repo map made successfully!\n")

            documents = self._read_file(repo_map)
            filtered_documents = self._refine_map(documents)
            print("✅ Filtered documents successfully!\n")

            print("🔨 Preparing summary...\n")
            summaries = await self._summarized_documents(filtered_documents)

            print("🫙 Storing in database...\n")
            try:
                repo = await RepositoryService.get_repo_by_url(self.session, self.url)

                if repo is None:
                    repo = await RepositoryService.create_repo(self.session, self.url)

                print(f"Documents: {len(documents)}")
                print(f"Filtered: {len(filtered_documents)}")
                print(f"Summaries: {len(summaries)}")
                await RepositoryService.store_files(self.session, repo.id, summaries)

                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

            print("✅ Database storing successful!\n")

            print("🎉 Pipeline ran successfully!\n")
        except Exception as e:
            raise RuntimeError("❌ Something went wrong!") from e

        return {
            "extraction": "success",
            "summary": summaries,
            "workspace": self.workspace,
        }
