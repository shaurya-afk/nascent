from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.oauth import oauth
from app.core.database import get_db
from app.models.user import User

router = APIRouter()

@router.get("/auth/github/login")
async def login(req: Request):
    redirect_uri = req.url_for("github_callback")

    return await oauth.github.authorize_redirect(
        req,
        redirect_uri,
    )

@router.get("/auth/github/callback", name="github_callback")
async def callback(req: Request, session: AsyncSession = Depends(get_db)):
    token = await oauth.github.authorize_access_token(req)

    resp = await oauth.github.get(
        "user",
        token=token
    )

    github_user = resp.json()

    user = await session.scalar(
        select(User).where(
            User.github_id == github_user["id"]
        )
    )

    if user is None:
        user = User(
            github_id = github_user["id"],
            github_username = github_user["login"]
        )

        session.add(user)
        await session.flush()
    else:
        user.github_username = github_user["login"]

    await session.commit()

    req.session["user_id"] = str(user.id)

    return RedirectResponse(
        url="http://localhost:3000/dashboard",
        status_code=302
    )

@router.get("/auth/me")
async def me(req: Request, session: AsyncSession = Depends(get_db)):
    user_id = req.session.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="not authenticated."
        )
    
    stmt = select(User).where(
        User.id == user_id
    )

    user = await session.scalar(stmt)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="user not found."
        )
    
    return{
        "id":str(user.id),
        "github_id":user.github_id,
        "github_username":user.github_username,
        "github_installation_id":user.github_installation_id
    }

@router.get("/auth/github/install")
async def install_github():
    return RedirectResponse(
        "https://github.com/apps/nascent-afk/installations/new"
    )

@router.get("/auth/github/install/callback")
async def github_install_callback(req: Request, session: AsyncSession = Depends(get_db)):
    user_id = req.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="not authenticated."
        )
    
    installation_id = req.query_params.get("installation_id")
    if installation_id is None:
        raise HTTPException(
            status_code=400,
            detail="missing installation_id"
        )

    user = await session.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user.github_installation_id = int(installation_id)
    await session.commit()

    return RedirectResponse(
        url="http://localhost:3000/dashboard",
        status_code=302,
    )

@router.post("/auth/logout")
async def logout(req: Request, session: AsyncSession = Depends(get_db)):
    req.session.clear()

    return{"success":True}