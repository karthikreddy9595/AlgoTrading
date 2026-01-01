"""
Broker API endpoints for connecting and managing broker accounts.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User, BrokerConnection
from brokers.fyers import FyersBroker

router = APIRouter(prefix="/broker", tags=["Broker"])


@router.get("/fyers/login")
async def fyers_login(
    current_user: User = Depends(get_current_user),
):
    """
    Initiate Fyers OAuth login.
    Redirects user to Fyers authorization page.
    """
    if not settings.FYERS_APP_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fyers integration is not configured",
        )

    # Generate auth URL with user ID as state for CSRF protection
    auth_url = FyersBroker.generate_auth_url(
        client_id=settings.FYERS_APP_ID,
        redirect_uri=settings.FYERS_REDIRECT_URI,
        state=str(current_user.id),
    )

    return {"auth_url": auth_url}


@router.get("/fyers/callback")
async def fyers_callback(
    request: Request,
    auth_code: Optional[str] = None,
    code: Optional[str] = None,
    state: Optional[str] = None,
    s: Optional[str] = None,  # Fyers status parameter
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Fyers OAuth callback.
    Exchanges auth code for access token and stores the connection.
    """
    # Fyers sends code as 'auth_code' or 'code'
    authorization_code = auth_code or code

    if not authorization_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided",
        )

    if s == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fyers authorization failed",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State parameter missing (CSRF protection)",
        )

    # Verify user exists
    result = await db.execute(select(User).where(User.id == state))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    try:
        # Exchange auth code for access token
        token_data = await FyersBroker.exchange_auth_code(
            client_id=settings.FYERS_APP_ID,
            secret_key=settings.FYERS_SECRET_KEY,
            auth_code=authorization_code,
        )

        access_token = token_data.get("access_token")
        if not access_token:
            raise Exception("No access token in response")

        # Check if connection already exists
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == "fyers",
            )
        )
        connection = result.scalar_one_or_none()

        if connection:
            # Update existing connection
            connection.access_token = access_token
            connection.token_expiry = datetime.utcnow() + timedelta(hours=12)
            connection.is_active = True
            connection.updated_at = datetime.utcnow()
        else:
            # Create new connection
            connection = BrokerConnection(
                user_id=user.id,
                broker="fyers",
                api_key=settings.FYERS_APP_ID,
                access_token=access_token,
                token_expiry=datetime.utcnow() + timedelta(hours=12),
                is_active=True,
            )
            db.add(connection)

        await db.commit()

        # Redirect to frontend with success
        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/settings?broker=fyers&status=success"
        )

    except Exception as e:
        print(f"Fyers OAuth error: {e}")
        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/settings?broker=fyers&status=error&message={str(e)}"
        )


@router.post("/fyers/disconnect")
async def fyers_disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect Fyers broker account.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == "fyers",
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fyers connection not found",
        )

    connection.is_active = False
    connection.access_token = None
    await db.commit()

    return {"message": "Fyers disconnected successfully"}


@router.get("/fyers/status")
async def fyers_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Fyers connection status.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == "fyers",
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or not connection.is_active:
        return {
            "connected": False,
            "broker": "fyers",
        }

    # Check token expiry
    is_expired = (
        connection.token_expiry and
        connection.token_expiry < datetime.utcnow()
    )

    return {
        "connected": not is_expired,
        "broker": "fyers",
        "expires_at": connection.token_expiry.isoformat() if connection.token_expiry else None,
        "needs_refresh": is_expired,
    }


@router.get("/fyers/profile")
async def fyers_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Fyers user profile.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == "fyers",
            BrokerConnection.is_active == True,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fyers not connected",
        )

    from brokers.fyers import FyersBroker
    from brokers.base import BrokerCredentials

    broker = FyersBroker()
    credentials = BrokerCredentials(
        api_key=connection.api_key or "",
        api_secret="",
        access_token=connection.access_token,
        client_id=settings.FYERS_APP_ID,
    )

    try:
        connected = await broker.connect(credentials)
        if not connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to Fyers",
            )

        profile = await broker.get_profile()
        margin = await broker.get_margin()
        positions = await broker.get_positions()

        await broker.disconnect()

        return {
            "profile": profile,
            "margin": margin,
            "positions": [
                {
                    "symbol": p.symbol,
                    "exchange": p.exchange,
                    "quantity": p.quantity,
                    "avg_price": float(p.avg_price),
                    "ltp": float(p.ltp),
                    "pnl": float(p.pnl),
                }
                for p in positions
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Fyers API error: {str(e)}",
        )
    finally:
        await broker.disconnect()
