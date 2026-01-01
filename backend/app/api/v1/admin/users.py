"""
Admin API for user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_admin_user
from app.models import User, StrategySubscription, BrokerConnection
from app.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["Admin - Users"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users (admin only).
    """
    query = select(User)

    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%")
        )

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return result.scalars().all()


@router.get("/stats")
async def get_user_stats(
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user statistics.
    """
    # Total users
    result = await db.execute(select(func.count(User.id)))
    total_users = result.scalar()

    # Active users
    result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = result.scalar()

    # Users with active subscriptions
    result = await db.execute(
        select(func.count(func.distinct(StrategySubscription.user_id))).where(
            StrategySubscription.status == "active"
        )
    )
    trading_users = result.scalar()

    # Users with broker connections
    result = await db.execute(
        select(func.count(func.distinct(BrokerConnection.user_id))).where(
            BrokerConnection.is_active == True
        )
    )
    connected_users = result.scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "trading_users": trading_users,
        "connected_users": connected_users,
    }


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user details (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get subscriptions
    result = await db.execute(
        select(StrategySubscription).where(StrategySubscription.user_id == user_id)
    )
    subscriptions = result.scalars().all()

    # Get broker connections
    result = await db.execute(
        select(BrokerConnection).where(BrokerConnection.user_id == user_id)
    )
    connections = result.scalars().all()

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat(),
        "subscriptions": [
            {
                "id": str(sub.id),
                "strategy_id": str(sub.strategy_id),
                "status": sub.status,
                "capital_allocated": float(sub.capital_allocated),
                "current_pnl": float(sub.current_pnl),
            }
            for sub in subscriptions
        ],
        "broker_connections": [
            {
                "id": str(conn.id),
                "broker": conn.broker,
                "is_active": conn.is_active,
            }
            for conn in connections
        ],
    }


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate a user (admin only).
    """
    if str(user_id) == str(admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    await db.commit()

    return {"message": "User deactivated"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a user (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = True
    await db.commit()

    return {"message": "User activated"}


@router.post("/{user_id}/make-admin")
async def make_admin(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Make a user an admin (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_admin = True
    await db.commit()

    return {"message": "User is now an admin"}


@router.post("/{user_id}/remove-admin")
async def remove_admin(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove admin privileges from a user.
    """
    if str(user_id) == str(admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_admin = False
    await db.commit()

    return {"message": "Admin privileges removed"}
