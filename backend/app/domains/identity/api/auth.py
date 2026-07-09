from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domains.identity.api.dependencies import get_current_user
from app.domains.identity.models import User
from app.domains.identity.schemas import LoginRequest, LoginResponse, TokenResponse, UserResponse
from app.domains.identity.services import AuthService
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    max_age = settings.jwt_refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=f"{settings.api_prefix}/auth",
        max_age=max_age,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=f"{settings.api_prefix}/auth",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    service = AuthService(session)
    ip_address = _client_ip(request)
    user_agent = request.headers.get("user-agent")

    try:
        result, refresh_token = await service.login(
            payload, ip_address=ip_address, user_agent=user_agent
        )
    except ValueError as exc:
        code = str(exc)
        if code == "rate_limit_exceeded":
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=code) from exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc

    _set_refresh_cookie(response, refresh_token)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    token = request.cookies.get(settings.refresh_token_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    service = AuthService(session)
    try:
        access_token, expires_in, new_refresh = await service.refresh(
            token,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    settings = get_settings()
    token = request.cookies.get(settings.refresh_token_cookie_name)
    service = AuthService(session)
    await service.logout(token)
    _clear_refresh_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
