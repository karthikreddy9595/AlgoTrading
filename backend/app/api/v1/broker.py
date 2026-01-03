"""
Generic Broker API endpoints for plugin-based broker management.

Provides unified endpoints that work with any registered broker plugin.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User, BrokerConnection
from brokers.registry import broker_registry
from brokers.factory import BrokerFactory

router = APIRouter(prefix="/broker", tags=["Broker"])


# ==================== Schemas ====================


class BrokerInfo(BaseModel):
    """Basic broker information."""

    name: str
    display_name: str
    description: str
    auth_type: str
    logo_url: Optional[str]


class BrokerCapabilitiesResponse(BaseModel):
    """Broker capabilities."""

    trading: bool
    market_data: bool
    historical_data: bool
    streaming: bool
    options: bool
    futures: bool
    equity: bool
    commodities: bool
    currency: bool


class BrokerDetailResponse(BaseModel):
    """Detailed broker information."""

    name: str
    display_name: str
    version: str
    description: str
    auth_type: str
    requires_api_key: bool
    requires_api_secret: bool
    requires_totp: bool
    token_expiry_hours: int
    exchanges: List[str]
    capabilities: BrokerCapabilitiesResponse
    logo_url: Optional[str]


class BrokerConnectionStatus(BaseModel):
    """Broker connection status."""

    broker: str
    connected: bool
    expires_at: Optional[str]
    needs_refresh: bool


class ApiKeyConnectionRequest(BaseModel):
    """Request for API key-based connection."""

    api_key: str
    api_secret: str
    totp: Optional[str] = None


# ==================== List Available Brokers ====================


@router.get("/available", response_model=List[BrokerInfo])
async def list_available_brokers():
    """
    List all available broker plugins.
    """
    brokers = []
    for metadata in broker_registry.list_brokers_with_metadata():
        brokers.append(
            BrokerInfo(
                name=metadata.name,
                display_name=metadata.display_name,
                description=metadata.description,
                auth_type=metadata.auth_config.auth_type,
                logo_url=metadata.logo_url,
            )
        )
    return brokers


@router.get("/{broker_name}/info", response_model=BrokerDetailResponse)
async def get_broker_info(broker_name: str):
    """
    Get detailed information about a specific broker.
    """
    metadata = broker_registry.get_metadata(broker_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Broker '{broker_name}' not found",
        )

    return BrokerDetailResponse(
        name=metadata.name,
        display_name=metadata.display_name,
        version=metadata.version,
        description=metadata.description,
        auth_type=metadata.auth_config.auth_type,
        requires_api_key=metadata.auth_config.requires_api_key,
        requires_api_secret=metadata.auth_config.requires_api_secret,
        requires_totp=metadata.auth_config.requires_totp,
        token_expiry_hours=metadata.auth_config.token_expiry_hours,
        exchanges=metadata.exchanges,
        capabilities=BrokerCapabilitiesResponse(
            trading=metadata.capabilities.trading,
            market_data=metadata.capabilities.market_data,
            historical_data=metadata.capabilities.historical_data,
            streaming=metadata.capabilities.streaming,
            options=metadata.capabilities.options,
            futures=metadata.capabilities.futures,
            equity=metadata.capabilities.equity,
            commodities=metadata.capabilities.commodities,
            currency=metadata.capabilities.currency,
        ),
        logo_url=metadata.logo_url,
    )


# ==================== OAuth Flow (Generic) ====================


@router.get("/{broker_name}/login")
async def broker_oauth_login(
    broker_name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Initiate OAuth login for any broker.
    Returns the authorization URL to redirect the user to.
    """
    metadata = broker_registry.get_metadata(broker_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Broker '{broker_name}' not found",
        )

    if metadata.auth_config.auth_type != "oauth":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broker '{broker_name}' does not support OAuth. Use API key authentication.",
        )

    # Get broker config from settings
    config = _get_broker_config(broker_name)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Broker '{broker_name}' is not configured on this server",
        )

    # Generate auth URL
    auth_url = BrokerFactory.get_auth_url(
        broker_name,
        config,
        state=str(current_user.id),
    )

    if not auth_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth not configured for {broker_name}",
        )

    return {"auth_url": auth_url}


@router.get("/{broker_name}/callback")
async def broker_oauth_callback(
    broker_name: str,
    request: Request,
    auth_code: Optional[str] = None,
    code: Optional[str] = None,
    state: Optional[str] = None,
    s: Optional[str] = None,  # Status parameter (broker-specific)
    db: AsyncSession = Depends(get_db),
):
    """
    Handle OAuth callback for any broker.
    Exchanges auth code for access token and stores the connection.
    """
    authorization_code = auth_code or code

    if not authorization_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided",
        )

    if s == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization failed",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State parameter missing",
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
        # Get broker config
        config = _get_broker_config(broker_name)

        # Exchange code for token
        token_data = await BrokerFactory.exchange_token(
            broker_name,
            config,
            authorization_code,
        )

        access_token = token_data.get("access_token")
        if not access_token:
            raise Exception("No access token in response")

        # Get token expiry from metadata
        metadata = broker_registry.get_metadata(broker_name)
        expiry_hours = metadata.auth_config.token_expiry_hours if metadata else 12

        # Upsert broker connection
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == broker_name,
            )
        )
        connection = result.scalar_one_or_none()

        if connection:
            connection.access_token = access_token
            connection.api_key = config.get("app_id", config.get("api_key", ""))
            connection.token_expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
            connection.is_active = True
            connection.updated_at = datetime.utcnow()
        else:
            connection = BrokerConnection(
                user_id=user.id,
                broker=broker_name,
                api_key=config.get("app_id", config.get("api_key", "")),
                access_token=access_token,
                token_expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
                is_active=True,
            )
            db.add(connection)

        await db.commit()

        # Redirect to frontend
        frontend_url = (
            settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
        )
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=success"
        )

    except Exception as e:
        print(f"OAuth error for {broker_name}: {e}")
        frontend_url = (
            settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
        )
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=error&message={str(e)}"
        )


# ==================== API Key Connection ====================


@router.post("/{broker_name}/connect")
async def broker_api_key_connect(
    broker_name: str,
    connection_data: ApiKeyConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect to a broker using API key/secret (non-OAuth brokers).
    """
    metadata = broker_registry.get_metadata(broker_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Broker '{broker_name}' not found",
        )

    if metadata.auth_config.auth_type == "oauth":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broker '{broker_name}' requires OAuth authentication. Use the login endpoint.",
        )

    try:
        # Try to connect with the provided credentials
        broker = await BrokerFactory.create_and_connect(
            broker_name,
            {
                "api_key": connection_data.api_key,
                "api_secret": connection_data.api_secret,
            },
        )

        # Verify connection by getting profile
        profile = await broker.get_profile()
        await broker.disconnect()

        # Get token expiry from metadata
        expiry_hours = metadata.auth_config.token_expiry_hours

        # Save connection
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == current_user.id,
                BrokerConnection.broker == broker_name,
            )
        )
        connection = result.scalar_one_or_none()

        if connection:
            connection.api_key = connection_data.api_key
            connection.api_secret = connection_data.api_secret
            connection.token_expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
            connection.is_active = True
            connection.updated_at = datetime.utcnow()
        else:
            connection = BrokerConnection(
                user_id=current_user.id,
                broker=broker_name,
                api_key=connection_data.api_key,
                api_secret=connection_data.api_secret,
                token_expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
                is_active=True,
            )
            db.add(connection)

        await db.commit()

        return {"message": f"Connected to {broker_name} successfully", "profile": profile}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect: {str(e)}",
        )


# ==================== Connection Management ====================


@router.get("/{broker_name}/status", response_model=BrokerConnectionStatus)
async def get_broker_status(
    broker_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get connection status for a specific broker.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == broker_name,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or not connection.is_active:
        return BrokerConnectionStatus(
            broker=broker_name,
            connected=False,
            expires_at=None,
            needs_refresh=False,
        )

    # Check token expiry
    is_expired = connection.token_expiry and connection.token_expiry < datetime.utcnow()

    return BrokerConnectionStatus(
        broker=broker_name,
        connected=not is_expired,
        expires_at=connection.token_expiry.isoformat() if connection.token_expiry else None,
        needs_refresh=is_expired,
    )


@router.post("/{broker_name}/disconnect")
async def disconnect_broker(
    broker_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect from a broker.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == broker_name,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No connection found for {broker_name}",
        )

    connection.is_active = False
    connection.access_token = None
    await db.commit()

    return {"message": f"Disconnected from {broker_name}"}


@router.get("/{broker_name}/profile")
async def get_broker_profile(
    broker_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get broker profile and account information.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == broker_name,
            BrokerConnection.is_active == True,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not connected to {broker_name}",
        )

    try:
        config = _get_broker_config(broker_name)
        broker = await BrokerFactory.create_and_connect(
            broker_name,
            {
                "api_key": connection.api_key,
                "api_secret": connection.api_secret,
                "access_token": connection.access_token,
                "client_id": config.get("app_id", connection.api_key),
            },
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
            detail=f"Broker API error: {str(e)}",
        )


# ==================== Helper Functions ====================


def _get_broker_config(broker_name: str) -> dict:
    """Get broker configuration from settings based on broker name."""
    config_mapping = {
        "fyers": {
            "app_id": settings.FYERS_APP_ID,
            "secret_key": settings.FYERS_SECRET_KEY,
            "redirect_uri": settings.FYERS_REDIRECT_URI,
        },
        # Add more brokers here as they are added
        # "zerodha": {
        #     "api_key": settings.ZERODHA_API_KEY,
        #     "api_secret": settings.ZERODHA_API_SECRET,
        #     "redirect_uri": settings.ZERODHA_REDIRECT_URI,
        # },
    }
    return config_mapping.get(broker_name, {})
