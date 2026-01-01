"""
API endpoints for user notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Notification, NotificationPreference

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user notifications.
    """
    query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    if notification_type:
        query = query.where(Notification.type == notification_type)

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "data": n.data,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get count of unread notifications.
    """
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    count = result.scalar()

    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a notification as read.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True
    await db.commit()

    return {"message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all notifications as read.
    """
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    await db.commit()

    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a notification.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    await db.delete(notification)
    await db.commit()

    return {"message": "Notification deleted"}


@router.get("/preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user notification preferences.
    """
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Return defaults
        return {
            "email_enabled": True,
            "sms_enabled": False,
            "in_app_enabled": True,
            "trade_alerts": True,
            "daily_summary": True,
            "risk_alerts": True,
        }

    return {
        "email_enabled": preferences.email_enabled,
        "sms_enabled": preferences.sms_enabled,
        "in_app_enabled": preferences.in_app_enabled,
        "trade_alerts": preferences.trade_alerts,
        "daily_summary": preferences.daily_summary,
        "risk_alerts": preferences.risk_alerts,
    }


@router.put("/preferences")
async def update_notification_preferences(
    preferences_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user notification preferences.
    """
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Create new preferences
        preferences = NotificationPreference(user_id=current_user.id)
        db.add(preferences)

    # Update fields
    allowed_fields = [
        "email_enabled",
        "sms_enabled",
        "in_app_enabled",
        "trade_alerts",
        "daily_summary",
        "risk_alerts",
    ]

    for field in allowed_fields:
        if field in preferences_data:
            setattr(preferences, field, preferences_data[field])

    await db.commit()
    await db.refresh(preferences)

    return {
        "email_enabled": preferences.email_enabled,
        "sms_enabled": preferences.sms_enabled,
        "in_app_enabled": preferences.in_app_enabled,
        "trade_alerts": preferences.trade_alerts,
        "daily_summary": preferences.daily_summary,
        "risk_alerts": preferences.risk_alerts,
    }
