from datetime import datetime, timedelta, UTC
import jwt
import httpx

from app.core.config import settings

class GitHubService:
    def generate_jwt(self) -> str:
        private_key = settings.github_private_key

        now = datetime.now(UTC)

        payload = {
            "iat":int(now.timestamp()),
            "exp":int((now + timedelta(minutes=10)).timestamp()),
            "iss":str(settings.github_app_id)
        }

        token = jwt.encode(
            payload=payload,
            key=private_key,
            algorithm="RS256"
        )

        return token
    
    async def get_installation_token(self, installation_id: int) -> str:
        jwt_token = self.generate_jwt()

        url = (
            f"https://api.github.com/app/installations/"
            f"{installation_id}/access_tokens"
        )

        headers = {
            "Authorization":f"Bearer {jwt_token}",
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(
                url,
                headers=headers
            )

            res.raise_for_status()

            data = res.json()

            return data["token"]
        
    async def get_repos(self, installation_token: str):
        url = (
            "https://api.github.com/installation/repositories"
        )

        headers = {
            "Authorization":f"Bearer {installation_token}",
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient() as client:
            res = await client.get(
                url,
                headers=headers
            )

            res.raise_for_status()
            
            return res.json()
        
    async def create_pull_request(
        self,
        installation_token: str,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str | None = None,
    ) -> str:
        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/pulls"
        )

        headers = {
            "Authorization": f"Bearer {installation_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        payload = {
            "title": title,
            "head": head,
            "base": base,
            "body": body or "",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

        return data["html_url"]