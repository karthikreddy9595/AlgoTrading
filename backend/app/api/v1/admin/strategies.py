"""
Admin API for strategy management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import re

from app.core.database import get_db
from app.api.deps import get_current_admin_user
from app.models import User, Strategy, StrategyVersion, StrategySubscription
from app.schemas import StrategyCreate, StrategyUpdate, StrategyResponse

router = APIRouter(prefix="/strategies", tags=["Admin - Strategies"])


@router.get("", response_model=List[StrategyResponse])
async def list_all_strategies(
    skip: int = 0,
    limit: int = 50,
    include_inactive: bool = False,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all strategies (admin only).
    """
    query = select(Strategy)

    if not include_inactive:
        query = query.where(Strategy.is_active == True)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return result.scalars().all()


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new strategy (admin only).
    """
    # Check if slug already exists
    result = await db.execute(
        select(Strategy).where(Strategy.slug == strategy_data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy with this slug already exists",
        )

    strategy = Strategy(
        name=strategy_data.name,
        slug=strategy_data.slug,
        description=strategy_data.description,
        long_description=strategy_data.long_description,
        version=strategy_data.version,
        min_capital=strategy_data.min_capital,
        expected_return_percent=strategy_data.expected_return_percent,
        max_drawdown_percent=strategy_data.max_drawdown_percent,
        timeframe=strategy_data.timeframe,
        supported_symbols=strategy_data.supported_symbols,
        tags=strategy_data.tags,
        module_path=strategy_data.module_path,
        class_name=strategy_data.class_name,
        git_repo_url=strategy_data.git_repo_url,
        git_branch=strategy_data.git_branch,
        author="Platform",
    )

    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    # Create initial version
    version = StrategyVersion(
        strategy_id=strategy.id,
        version=strategy_data.version,
        changelog="Initial release",
        is_current=True,
    )
    db.add(version)
    await db.commit()

    return strategy


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific strategy (admin only).
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    return strategy


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    update_data: StrategyUpdate,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a strategy (admin only).
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(strategy, field, value)

    strategy.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(strategy)

    return strategy


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a strategy (soft delete by setting inactive).
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Check if any active subscriptions
    result = await db.execute(
        select(func.count(StrategySubscription.id)).where(
            StrategySubscription.strategy_id == strategy_id,
            StrategySubscription.status == "active",
        )
    )
    active_count = result.scalar()

    if active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete strategy with {active_count} active subscriptions",
        )

    strategy.is_active = False
    strategy.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Strategy deactivated"}


@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a strategy.
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    strategy.is_active = True
    strategy.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Strategy activated"}


@router.get("/{strategy_id}/subscriptions")
async def get_strategy_subscriptions(
    strategy_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all subscriptions for a strategy.
    """
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.strategy_id == strategy_id
        )
    )
    subscriptions = result.scalars().all()

    return [
        {
            "id": str(sub.id),
            "user_id": str(sub.user_id),
            "status": sub.status,
            "capital_allocated": float(sub.capital_allocated),
            "is_paper_trading": sub.is_paper_trading,
            "current_pnl": float(sub.current_pnl),
            "today_pnl": float(sub.today_pnl),
            "created_at": sub.created_at.isoformat(),
        }
        for sub in subscriptions
    ]


@router.get("/{strategy_id}/stats")
async def get_strategy_stats(
    strategy_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics for a strategy.
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Get subscription counts
    result = await db.execute(
        select(func.count(StrategySubscription.id)).where(
            StrategySubscription.strategy_id == strategy_id
        )
    )
    total_subscriptions = result.scalar()

    result = await db.execute(
        select(func.count(StrategySubscription.id)).where(
            StrategySubscription.strategy_id == strategy_id,
            StrategySubscription.status == "active",
        )
    )
    active_subscriptions = result.scalar()

    # Get total capital
    result = await db.execute(
        select(func.sum(StrategySubscription.capital_allocated)).where(
            StrategySubscription.strategy_id == strategy_id
        )
    )
    total_capital = result.scalar() or 0

    # Get total PnL
    result = await db.execute(
        select(func.sum(StrategySubscription.current_pnl)).where(
            StrategySubscription.strategy_id == strategy_id
        )
    )
    total_pnl = result.scalar() or 0

    return {
        "strategy_id": str(strategy_id),
        "name": strategy.name,
        "total_subscriptions": total_subscriptions,
        "active_subscriptions": active_subscriptions,
        "total_capital": float(total_capital),
        "total_pnl": float(total_pnl),
    }
