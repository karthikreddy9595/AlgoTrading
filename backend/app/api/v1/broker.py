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


class BrokerCredentialsRequest(BaseModel):
    """Request for saving OAuth broker credentials (APP_ID and Secret Key)."""

    app_id: str
    secret_key: str


class BrokerCredentialsResponse(BaseModel):
    """Response after saving broker credentials."""

    message: str
    redirect_uri: str
    credentials_saved: bool


class BrokerRedirectUriResponse(BaseModel):
    """Response containing the redirect URI for broker configuration."""

    broker: str
    redirect_uri: str


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


# ==================== Broker Credentials Management ====================


@router.get("/{broker_name}/redirect-uri", response_model=BrokerRedirectUriResponse)
async def get_broker_redirect_uri(broker_name: str):
    """
    Get the redirect URI that users need to configure in their broker's developer portal.
    """
    metadata = broker_registry.get_metadata(broker_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Broker '{broker_name}' not found",
        )

    redirect_uri = _get_redirect_uri(broker_name)
    if not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Redirect URI not configured for {broker_name}",
        )

    return BrokerRedirectUriResponse(
        broker=broker_name,
        redirect_uri=redirect_uri,
    )


@router.post("/{broker_name}/save-credentials", response_model=BrokerCredentialsResponse)
async def save_broker_credentials(
    broker_name: str,
    credentials: BrokerCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save user's broker API credentials (APP_ID and Secret Key).
    This must be done before initiating OAuth login.
    Returns the redirect URI that user needs to configure in their broker's developer portal.
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
            detail=f"Broker '{broker_name}' does not use OAuth. Use the connect endpoint instead.",
        )

    # Validate credentials are not empty
    if not credentials.app_id or not credentials.secret_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="APP ID and Secret Key are required",
        )

    # Upsert broker connection with credentials (without access_token yet)
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == broker_name,
        )
    )
    connection = result.scalar_one_or_none()

    if connection:
        connection.api_key = credentials.app_id
        connection.api_secret = credentials.secret_key
        connection.updated_at = datetime.utcnow()
        # Keep is_active as False until OAuth is complete
        if not connection.access_token:
            connection.is_active = False
    else:
        connection = BrokerConnection(
            user_id=current_user.id,
            broker=broker_name,
            api_key=credentials.app_id,
            api_secret=credentials.secret_key,
            is_active=False,  # Will be activated after OAuth completes
        )
        db.add(connection)

    await db.commit()

    redirect_uri = _get_redirect_uri(broker_name)

    return BrokerCredentialsResponse(
        message=f"Credentials saved for {broker_name}. Please configure the redirect URI in your broker's developer portal.",
        redirect_uri=redirect_uri,
        credentials_saved=True,
    )


@router.get("/{broker_name}/credentials-status")
async def get_credentials_status(
    broker_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if user has saved their broker credentials.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == broker_name,
        )
    )
    connection = result.scalar_one_or_none()

    has_credentials = connection is not None and connection.api_key and connection.api_secret
    is_connected = connection is not None and connection.is_active and connection.access_token

    return {
        "broker": broker_name,
        "has_credentials": has_credentials,
        "is_connected": is_connected,
        "redirect_uri": _get_redirect_uri(broker_name),
    }


# ==================== OAuth Flow (Generic) ====================


@router.get("/{broker_name}/login")
async def broker_oauth_login(
    broker_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate OAuth login for any broker.
    Returns the authorization URL to redirect the user to.
    User must have saved their credentials first via /save-credentials endpoint.
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

    # Get user's stored credentials from database
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == broker_name,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or not connection.api_key or not connection.api_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please save your API credentials first using the Save Credentials option.",
        )

    # Build config from user's stored credentials
    config = {
        "app_id": connection.api_key,
        "secret_key": connection.api_secret,
        "redirect_uri": _get_redirect_uri(broker_name),
    }

    # Generate auth URL using user's credentials
    auth_url = BrokerFactory.get_auth_url(
        broker_name,
        config,
        state=str(current_user.id),
    )

    if not auth_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to generate OAuth URL for {broker_name}",
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
    Uses user's stored credentials (APP_ID and Secret Key) for token exchange.
    """
    authorization_code = auth_code or code
    frontend_url = (
        settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    )

    if not authorization_code:
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=error&message=Authorization code not provided"
        )

    if s == "error":
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=error&message=Authorization failed"
        )

    if not state:
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=error&message=State parameter missing"
        )

    # Verify user exists
    result = await db.execute(select(User).where(User.id == state))
    user = result.scalar_one_or_none()

    if not user:
        return RedirectResponse(
            url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=error&message=Invalid state parameter"
        )

    try:
        # Get user's stored credentials from database
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user.id,
                BrokerConnection.broker == broker_name,
            )
        )
        connection = result.scalar_one_or_none()

        if not connection or not connection.api_key or not connection.api_secret:
            return RedirectResponse(
                url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=error&message=Credentials not found. Please save your API credentials first."
            )

        # Build config from user's stored credentials
        config = {
            "app_id": connection.api_key,
            "secret_key": connection.api_secret,
            "redirect_uri": _get_redirect_uri(broker_name),
        }

        # Exchange code for token using user's credentials
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

        # Update connection with access token
        connection.access_token = access_token
        connection.token_expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        connection.is_active = True
        connection.updated_at = datetime.utcnow()

        await db.commit()

        return RedirectResponse(
            url=f"{frontend_url}/dashboard/broker?broker={broker_name}&status=success"
        )

    except Exception as e:
        print(f"OAuth error for {broker_name}: {e}")
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
    Uses user's stored credentials.
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
        # Use user's stored credentials (api_key = APP_ID)
        broker = await BrokerFactory.create_and_connect(
            broker_name,
            {
                "api_key": connection.api_key,
                "api_secret": connection.api_secret,
                "access_token": connection.access_token,
                "client_id": connection.api_key,  # Use user's APP_ID
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


def _get_redirect_uri(broker_name: str) -> str:
    """Get the redirect URI for a broker. This is server-controlled."""
    redirect_uri_mapping = {
        "fyers": settings.FYERS_REDIRECT_URI,
        # Add more brokers here as they are added
        # "zerodha": settings.ZERODHA_REDIRECT_URI,
    }
    return redirect_uri_mapping.get(broker_name, "")


def _get_broker_config(broker_name: str) -> dict:
    """
    Get broker configuration from settings based on broker name.
    Note: This is now only used for server-level config like redirect_uri.
    User credentials (app_id, secret_key) should be fetched from BrokerConnection.
    """
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
