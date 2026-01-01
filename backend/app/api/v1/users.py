from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash
from app.api.deps import get_current_user
from app.models import User, BrokerConnection
from app.schemas import (
    UserResponse,
    UserUpdate,
    PasswordChange,
    BrokerConnectionCreate,
    BrokerConnectionResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user information.
    """
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.phone is not None:
        current_user.phone = user_data.phone

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post("/me/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user password.
    """
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth-only accounts",
        )

    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.get("/me/broker-connections", response_model=list[BrokerConnectionResponse])
async def get_broker_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all broker connections for current user.
    """
    result = await db.execute(
        select(BrokerConnection).where(BrokerConnection.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/me/broker-connections", response_model=BrokerConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_broker_connection(
    connection_data: BrokerConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new broker connection.
    """
    # Check if connection already exists
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.broker == connection_data.broker,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broker connection for {connection_data.broker} already exists",
        )

    connection = BrokerConnection(
        user_id=current_user.id,
        broker=connection_data.broker,
        api_key=connection_data.api_key,
        api_secret=connection_data.api_secret,
    )

    db.add(connection)
    await db.commit()
    await db.refresh(connection)

    return connection


@router.delete("/me/broker-connections/{connection_id}")
async def delete_broker_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a broker connection.
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == connection_id,
            BrokerConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker connection not found",
        )

    await db.delete(connection)
    await db.commit()

    return {"message": "Broker connection deleted"}
