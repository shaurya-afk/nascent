from app.models.repository import Repository
from app.models.repository_files import RepositoryFile

from sqlalchemy import select
from sqlalchemy.orm import selectinload


class RepositoryService:
    @staticmethod
    async def create_repo(session, github_url: str):
        repo = Repository(github_url=github_url)

        session.add(repo)
        await session.flush()

        return repo

    @staticmethod
    async def store_files(session, repo_id, summaries):
        for summary in summaries:
            file = RepositoryFile(
                repository_id=repo_id,
                name=summary["name"],
                path=summary["path"],
                summary=summary["summary"],
            )

            session.add(file)

    @staticmethod
    async def get_repo_by_url(session, github_url: str) -> Repository | None:
        stmt = select(Repository).where(Repository.github_url == github_url)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_repo_by_id(session, repo_id) -> Repository | None:
        stmt = select(Repository).where(Repository.id == repo_id)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_repo_files(session, github_url: str) -> Repository | None:
        stmt = (
            select(Repository)
            .options(selectinload(Repository.files))
            .where(Repository.github_url == github_url)
        )

        result = await session.execute(stmt)

        return result.scalar_one_or_none()
