"""
Report generation service for trade history, portfolio reports, etc.
"""

import csv
import io
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models import (
    User,
    StrategySubscription,
    Order,
    Trade,
    Position,
    Strategy,
)


class ReportService:
    """Service for generating various reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_trade_report_csv(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subscription_id: Optional[str] = None,
    ) -> str:
        """
        Generate CSV report of trades.

        Returns CSV string.
        """
        # Get user's subscriptions
        sub_query = select(StrategySubscription.id).where(
            StrategySubscription.user_id == user_id
        )

        if subscription_id:
            sub_query = sub_query.where(StrategySubscription.id == subscription_id)

        result = await self.db.execute(sub_query)
        subscription_ids = [str(row[0]) for row in result.all()]

        if not subscription_ids:
            return self._create_csv_string(
                ["No trades found"],
                []
            )

        # Get trades
        query = select(Trade).where(Trade.subscription_id.in_(subscription_ids))

        if start_date:
            query = query.where(Trade.entry_time >= start_date)
        if end_date:
            query = query.where(Trade.entry_time <= end_date)

        query = query.order_by(Trade.entry_time.desc())

        result = await self.db.execute(query)
        trades = result.scalars().all()

        # Get strategy names
        strategy_names = await self._get_strategy_names_for_subscriptions(subscription_ids)

        # Create CSV
        headers = [
            "Trade ID",
            "Strategy",
            "Symbol",
            "Exchange",
            "Side",
            "Quantity",
            "Entry Price",
            "Exit Price",
            "P&L",
            "P&L %",
            "Entry Time",
            "Exit Time",
            "Duration",
            "Status",
        ]

        rows = []
        for trade in trades:
            strategy_name = strategy_names.get(str(trade.subscription_id), "Unknown")
            duration = ""
            if trade.exit_time and trade.entry_time:
                duration_secs = (trade.exit_time - trade.entry_time).total_seconds()
                duration = self._format_duration(int(duration_secs))

            rows.append([
                str(trade.id),
                strategy_name,
                trade.symbol,
                trade.exchange,
                trade.side,
                trade.quantity,
                float(trade.entry_price),
                float(trade.exit_price) if trade.exit_price else "",
                float(trade.pnl) if trade.pnl else "",
                f"{float(trade.pnl_percent):.2f}%" if trade.pnl_percent else "",
                trade.entry_time.isoformat() if trade.entry_time else "",
                trade.exit_time.isoformat() if trade.exit_time else "",
                duration,
                trade.status,
            ])

        return self._create_csv_string(headers, rows)

    async def generate_order_report_csv(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subscription_id: Optional[str] = None,
    ) -> str:
        """
        Generate CSV report of orders.

        Returns CSV string.
        """
        # Get user's subscriptions
        sub_query = select(StrategySubscription.id).where(
            StrategySubscription.user_id == user_id
        )

        if subscription_id:
            sub_query = sub_query.where(StrategySubscription.id == subscription_id)

        result = await self.db.execute(sub_query)
        subscription_ids = [str(row[0]) for row in result.all()]

        if not subscription_ids:
            return self._create_csv_string(
                ["No orders found"],
                []
            )

        # Get orders
        query = select(Order).where(Order.subscription_id.in_(subscription_ids))

        if start_date:
            query = query.where(Order.created_at >= start_date)
        if end_date:
            query = query.where(Order.created_at <= end_date)

        query = query.order_by(Order.created_at.desc())

        result = await self.db.execute(query)
        orders = result.scalars().all()

        # Get strategy names
        strategy_names = await self._get_strategy_names_for_subscriptions(subscription_ids)

        # Create CSV
        headers = [
            "Order ID",
            "Broker Order ID",
            "Strategy",
            "Symbol",
            "Exchange",
            "Type",
            "Transaction",
            "Quantity",
            "Price",
            "Trigger Price",
            "Filled Qty",
            "Filled Price",
            "Status",
            "Reason",
            "Created At",
        ]

        rows = []
        for order in orders:
            strategy_name = strategy_names.get(str(order.subscription_id), "Unknown")

            rows.append([
                str(order.id),
                order.broker_order_id or "",
                strategy_name,
                order.symbol,
                order.exchange,
                order.order_type,
                order.transaction_type,
                order.quantity,
                float(order.price) if order.price else "",
                float(order.trigger_price) if order.trigger_price else "",
                order.filled_quantity or "",
                float(order.filled_price) if order.filled_price else "",
                order.status,
                order.reason or "",
                order.created_at.isoformat() if order.created_at else "",
            ])

        return self._create_csv_string(headers, rows)

    async def generate_portfolio_summary(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Generate portfolio summary data.

        Returns dictionary with portfolio metrics.
        """
        # Get active subscriptions
        result = await self.db.execute(
            select(StrategySubscription).where(
                StrategySubscription.user_id == user_id,
                StrategySubscription.status.in_(["active", "paused", "stopped"]),
            )
        )
        subscriptions = result.scalars().all()

        if not subscriptions:
            return {
                "total_capital": 0,
                "total_pnl": 0,
                "total_pnl_percent": 0,
                "today_pnl": 0,
                "active_strategies": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "strategies": [],
            }

        subscription_ids = [str(sub.id) for sub in subscriptions]

        # Calculate totals
        total_capital = sum(float(sub.capital_allocated) for sub in subscriptions)
        total_pnl = sum(float(sub.current_pnl) for sub in subscriptions)
        today_pnl = sum(float(sub.today_pnl) for sub in subscriptions)

        # Get trade statistics
        result = await self.db.execute(
            select(
                func.count(Trade.id).label("total"),
                func.sum(
                    func.case(
                        (Trade.pnl > 0, 1),
                        else_=0
                    )
                ).label("winning"),
                func.sum(
                    func.case(
                        (Trade.pnl < 0, 1),
                        else_=0
                    )
                ).label("losing"),
            ).where(
                Trade.subscription_id.in_(subscription_ids),
                Trade.status == "closed",
            )
        )
        trade_stats = result.one()

        total_trades = trade_stats.total or 0
        winning_trades = int(trade_stats.winning or 0)
        losing_trades = int(trade_stats.losing or 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Get strategy details
        strategy_names = await self._get_strategy_names_for_subscriptions(subscription_ids)

        strategies = []
        for sub in subscriptions:
            strategies.append({
                "subscription_id": str(sub.id),
                "strategy_id": str(sub.strategy_id),
                "strategy_name": strategy_names.get(str(sub.id), "Unknown"),
                "status": sub.status,
                "capital_allocated": float(sub.capital_allocated),
                "current_pnl": float(sub.current_pnl),
                "today_pnl": float(sub.today_pnl),
                "is_paper_trading": sub.is_paper_trading,
            })

        return {
            "total_capital": total_capital,
            "total_pnl": total_pnl,
            "total_pnl_percent": (total_pnl / total_capital * 100) if total_capital > 0 else 0,
            "today_pnl": today_pnl,
            "active_strategies": len([s for s in subscriptions if s.status == "active"]),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "strategies": strategies,
        }

    async def generate_performance_report(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate detailed performance report.

        Returns dictionary with performance metrics.
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get subscriptions
        result = await self.db.execute(
            select(StrategySubscription.id).where(
                StrategySubscription.user_id == user_id
            )
        )
        subscription_ids = [str(row[0]) for row in result.all()]

        if not subscription_ids:
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "trades": {
                    "total": 0,
                    "winning": 0,
                    "losing": 0,
                    "breakeven": 0,
                },
                "pnl": {
                    "total": 0,
                    "average": 0,
                    "best": 0,
                    "worst": 0,
                },
                "daily_pnl": [],
            }

        # Get trades in period
        result = await self.db.execute(
            select(Trade).where(
                Trade.subscription_id.in_(subscription_ids),
                Trade.entry_time >= start_date,
                Trade.entry_time <= end_date,
                Trade.status == "closed",
            ).order_by(Trade.entry_time)
        )
        trades = result.scalars().all()

        # Calculate trade statistics
        total_trades = len(trades)
        winning = sum(1 for t in trades if t.pnl and t.pnl > 0)
        losing = sum(1 for t in trades if t.pnl and t.pnl < 0)
        breakeven = total_trades - winning - losing

        # P&L statistics
        pnl_values = [float(t.pnl) for t in trades if t.pnl]
        total_pnl = sum(pnl_values) if pnl_values else 0
        avg_pnl = total_pnl / len(pnl_values) if pnl_values else 0
        best_pnl = max(pnl_values) if pnl_values else 0
        worst_pnl = min(pnl_values) if pnl_values else 0

        # Daily P&L
        daily_pnl = {}
        for trade in trades:
            if trade.exit_time and trade.pnl:
                date_key = trade.exit_time.date().isoformat()
                if date_key not in daily_pnl:
                    daily_pnl[date_key] = 0
                daily_pnl[date_key] += float(trade.pnl)

        daily_pnl_list = [
            {"date": date, "pnl": pnl}
            for date, pnl in sorted(daily_pnl.items())
        ]

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "trades": {
                "total": total_trades,
                "winning": winning,
                "losing": losing,
                "breakeven": breakeven,
                "win_rate": round(winning / total_trades * 100, 2) if total_trades > 0 else 0,
            },
            "pnl": {
                "total": round(total_pnl, 2),
                "average": round(avg_pnl, 2),
                "best": round(best_pnl, 2),
                "worst": round(worst_pnl, 2),
            },
            "daily_pnl": daily_pnl_list,
        }

    async def _get_strategy_names_for_subscriptions(
        self,
        subscription_ids: List[str],
    ) -> Dict[str, str]:
        """Get strategy names for subscriptions."""
        result = await self.db.execute(
            select(StrategySubscription.id, Strategy.name)
            .join(Strategy, StrategySubscription.strategy_id == Strategy.id)
            .where(StrategySubscription.id.in_(subscription_ids))
        )

        return {str(row[0]): row[1] for row in result.all()}

    def _create_csv_string(self, headers: List[str], rows: List[List[Any]]) -> str:
        """Create CSV string from headers and rows."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        return output.getvalue()

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"


# PDF Generation using reportlab (optional, requires reportlab package)
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFReportGenerator:
    """PDF report generator using ReportLab."""

    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab package is required for PDF generation")

    def generate_portfolio_pdf(
        self,
        portfolio_data: Dict[str, Any],
        user_name: str,
    ) -> bytes:
        """Generate PDF portfolio report."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
        )
        story.append(Paragraph("Portfolio Report", title_style))
        story.append(Paragraph(f"Generated for: {user_name}", styles["Normal"]))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 20))

        # Summary section
        story.append(Paragraph("Summary", styles["Heading2"]))
        summary_data = [
            ["Metric", "Value"],
            ["Total Capital", f"Rs. {portfolio_data['total_capital']:,.2f}"],
            ["Total P&L", f"Rs. {portfolio_data['total_pnl']:,.2f}"],
            ["Total P&L %", f"{portfolio_data['total_pnl_percent']:.2f}%"],
            ["Today's P&L", f"Rs. {portfolio_data['today_pnl']:,.2f}"],
            ["Active Strategies", str(portfolio_data['active_strategies'])],
            ["Total Trades", str(portfolio_data['total_trades'])],
            ["Win Rate", f"{portfolio_data['win_rate']:.2f}%"],
        ]

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Strategies section
        if portfolio_data.get("strategies"):
            story.append(Paragraph("Strategy Performance", styles["Heading2"]))

            strategy_data = [
                ["Strategy", "Capital", "P&L", "Status"],
            ]
            for strat in portfolio_data["strategies"]:
                strategy_data.append([
                    strat["strategy_name"],
                    f"Rs. {strat['capital_allocated']:,.2f}",
                    f"Rs. {strat['current_pnl']:,.2f}",
                    strat["status"].upper(),
                ])

            strategy_table = Table(strategy_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1 * inch])
            strategy_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(strategy_table)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_trade_report_pdf(
        self,
        trades: List[Dict[str, Any]],
        user_name: str,
        period: str,
    ) -> bytes:
        """Generate PDF trade report."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
        )
        story.append(Paragraph("Trade Report", title_style))
        story.append(Paragraph(f"Generated for: {user_name}", styles["Normal"]))
        story.append(Paragraph(f"Period: {period}", styles["Normal"]))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 20))

        if trades:
            # Trade table
            trade_data = [
                ["Symbol", "Side", "Qty", "Entry", "Exit", "P&L"],
            ]
            for trade in trades[:50]:  # Limit to 50 trades for PDF
                trade_data.append([
                    trade.get("symbol", ""),
                    trade.get("side", ""),
                    str(trade.get("quantity", 0)),
                    f"{trade.get('entry_price', 0):.2f}",
                    f"{trade.get('exit_price', 0):.2f}" if trade.get("exit_price") else "-",
                    f"{trade.get('pnl', 0):.2f}" if trade.get("pnl") else "-",
                ])

            trade_table = Table(
                trade_data,
                colWidths=[1.2 * inch, 0.8 * inch, 0.6 * inch, 1 * inch, 1 * inch, 1 * inch]
            )
            trade_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            story.append(trade_table)

            if len(trades) > 50:
                story.append(Spacer(1, 10))
                story.append(Paragraph(
                    f"Showing 50 of {len(trades)} trades. Download CSV for complete list.",
                    styles["Italic"]
                ))
        else:
            story.append(Paragraph("No trades found for this period.", styles["Normal"]))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
