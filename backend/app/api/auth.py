from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..services.github_service import github_service
from ..models.schemas import UserProfile

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.get("/me", response_model=UserProfile)
async def get_current_user(token: Optional[str] = Query(None)):
    """Validates GitHub Personal Access Token and returns user profile."""
    try:
        user_data = await github_service.get_authenticated_user(custom_token=token)
        return UserProfile(
            login=user_data.get("login", ""),
            name=user_data.get("name"),
            avatar_url=user_data.get("avatar_url"),
            html_url=user_data.get("html_url"),
            bio=user_data.get("bio"),
            public_repos=user_data.get("public_repos", 0),
            total_private_repos=user_data.get("total_private_repos", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"GitHub authentication failed: {str(e)}")

@router.get("/rate-limit")
async def get_rate_limit_status(token: Optional[str] = Query(None)):
    """Checks the remaining GitHub API rate limits."""
    try:
        data = await github_service.get_rate_limit(custom_token=token)
        rate = data.get("resources", {}).get("core", {})
        return {
            "limit": rate.get("limit", 5000),
            "remaining": rate.get("remaining", 5000),
            "reset": rate.get("reset"),
            "used": rate.get("used", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch rate limit: {str(e)}")

@router.get("/github/login")
async def github_login():
    """Returns the GitHub OAuth login URL or instructions."""
    from ..config import settings
    if not settings.GITHUB_CLIENT_ID:
        return {
            "oauth_enabled": False,
            "message": "GITHUB_CLIENT_ID not configured. Using Fine-grained Personal Access Token (PAT) authentication.",
            "auth_type": "pat"
        }
    
    redirect_uri = settings.GITHUB_REDIRECT_URI
    scope = "repo,user,read:org"
    oauth_url = f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&redirect_uri={redirect_uri}&scope={scope}"
    return {
        "oauth_enabled": True,
        "url": oauth_url,
        "auth_type": "oauth"
    }

@router.get("/github/callback")
async def github_callback(code: str = Query(...)):
    """Handles GitHub OAuth redirect, exchanges code for access token."""
    from ..config import settings
    try:
        access_token = await github_service.exchange_code_for_token(code)
        settings.GITHUB_TOKEN = access_token
        github_service.token = access_token
        return {
            "status": "success",
            "message": "GitHub OAuth authentication successful!",
            "access_token": access_token
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")

