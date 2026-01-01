"""
API endpoints for report generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
import io

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User
from app.services.report_service import ReportService, PDFReportGenerator, REPORTLAB_AVAILABLE

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/trades/csv")
async def download_trades_csv(
    start_date: Optional[datetime] = Query(None, description="Start date for report"),
    end_date: Optional[datetime] = Query(None, description="End date for report"),
    subscription_id: Optional[str] = Query(None, description="Filter by subscription"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download trade history as CSV.
    """
    report_service = ReportService(db)

    csv_content = await report_service.generate_trade_report_csv(
        user_id=str(current_user.id),
        start_date=start_date,
        end_date=end_date,
        subscription_id=subscription_id,
    )

    # Generate filename
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trades_{date_str}.csv"

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/orders/csv")
async def download_orders_csv(
    start_date: Optional[datetime] = Query(None, description="Start date for report"),
    end_date: Optional[datetime] = Query(None, description="End date for report"),
    subscription_id: Optional[str] = Query(None, description="Filter by subscription"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download order history as CSV.
    """
    report_service = ReportService(db)

    csv_content = await report_service.generate_order_report_csv(
        user_id=str(current_user.id),
        start_date=start_date,
        end_date=end_date,
        subscription_id=subscription_id,
    )

    # Generate filename
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"orders_{date_str}.csv"

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/portfolio/summary")
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio summary report.
    """
    report_service = ReportService(db)

    summary = await report_service.generate_portfolio_summary(
        user_id=str(current_user.id),
    )

    return summary


@router.get("/portfolio/pdf")
async def download_portfolio_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download portfolio report as PDF.
    """
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation is not available. Please install reportlab package.",
        )

    report_service = ReportService(db)
    pdf_generator = PDFReportGenerator()

    # Get portfolio data
    portfolio_data = await report_service.generate_portfolio_summary(
        user_id=str(current_user.id),
    )

    # Generate PDF
    pdf_content = pdf_generator.generate_portfolio_pdf(
        portfolio_data=portfolio_data,
        user_name=current_user.full_name or current_user.email,
    )

    # Generate filename
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"portfolio_report_{date_str}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/performance")
async def get_performance_report(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed performance report.
    """
    report_service = ReportService(db)

    performance = await report_service.generate_performance_report(
        user_id=str(current_user.id),
        start_date=start_date,
        end_date=end_date,
    )

    return performance


@router.get("/trades/pdf")
async def download_trades_pdf(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download trade report as PDF.
    """
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation is not available. Please install reportlab package.",
        )

    from sqlalchemy import select
    from app.models import Trade, StrategySubscription

    # Get trades
    result = await db.execute(
        select(StrategySubscription.id).where(
            StrategySubscription.user_id == current_user.id
        )
    )
    subscription_ids = [str(row[0]) for row in result.all()]

    if not subscription_ids:
        trades = []
    else:
        query = select(Trade).where(
            Trade.subscription_id.in_(subscription_ids),
            Trade.status == "closed",
        )

        if start_date:
            query = query.where(Trade.entry_time >= start_date)
        if end_date:
            query = query.where(Trade.entry_time <= end_date)

        query = query.order_by(Trade.entry_time.desc())

        result = await db.execute(query)
        trade_objects = result.scalars().all()

        trades = [
            {
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price) if t.exit_price else None,
                "pnl": float(t.pnl) if t.pnl else None,
            }
            for t in trade_objects
        ]

    # Generate PDF
    pdf_generator = PDFReportGenerator()

    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()

    period = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

    pdf_content = pdf_generator.generate_trade_report_pdf(
        trades=trades,
        user_name=current_user.full_name or current_user.email,
        period=period,
    )

    # Generate filename
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trade_report_{date_str}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )
