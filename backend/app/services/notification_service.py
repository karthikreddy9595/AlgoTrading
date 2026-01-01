"""
Notification service for email, SMS, and in-app notifications.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models import Notification, NotificationPreference, User


class NotificationType(str, Enum):
    TRADE = "trade"
    ORDER = "order"
    RISK_ALERT = "risk_alert"
    SYSTEM = "system"
    STRATEGY = "strategy"
    DAILY_SUMMARY = "daily_summary"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"


class BaseNotifier(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a notification."""
        pass


class EmailNotifier(BaseNotifier):
    """Email notification sender using SMTP."""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = None,
    ):
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_user = smtp_user or settings.SMTP_USER
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.from_email = from_email or settings.FROM_EMAIL

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an email notification."""
        if not self.smtp_host or not self.smtp_user:
            print("Email not configured, skipping...")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = self.from_email
            msg["To"] = recipient

            # HTML template
            html_content = self._create_html_template(title, message, data)
            text_content = message

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
            )

            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def _create_html_template(
        self, title: str, message: str, data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create HTML email template."""
        data_section = ""
        if data:
            data_items = "".join(
                f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee;'><strong>{k}</strong></td>"
                f"<td style='padding: 8px; border-bottom: 1px solid #eee;'>{v}</td></tr>"
                for k, v in data.items()
            )
            data_section = f"""
            <table style='width: 100%; border-collapse: collapse; margin-top: 20px;'>
                {data_items}
            </table>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9fafb; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{settings.APP_NAME}</h1>
                </div>
                <div class="content">
                    <h2>{title}</h2>
                    <p>{message}</p>
                    {data_section}
                </div>
                <div class="footer">
                    <p>This is an automated message from {settings.APP_NAME}</p>
                    <p>Please do not reply to this email</p>
                </div>
            </div>
        </body>
        </html>
        """


class SMSNotifier(BaseNotifier):
    """SMS notification sender using HTTP API (MSG91/Twilio compatible)."""

    def __init__(
        self,
        api_key: str = None,
        sender_id: str = None,
        provider: str = "msg91",  # msg91 or twilio
    ):
        self.api_key = api_key or settings.SMS_API_KEY
        self.sender_id = sender_id or settings.SMS_SENDER_ID
        self.provider = provider

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an SMS notification."""
        if not self.api_key:
            print("SMS not configured, skipping...")
            return False

        try:
            # Format phone number
            phone = recipient.replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = f"+91{phone}"  # Default to India

            # Construct message
            sms_message = f"{title}: {message}"
            if len(sms_message) > 160:
                sms_message = sms_message[:157] + "..."

            if self.provider == "msg91":
                return await self._send_msg91(phone, sms_message)
            elif self.provider == "twilio":
                return await self._send_twilio(phone, sms_message)

            return False

        except Exception as e:
            print(f"Failed to send SMS: {e}")
            return False

    async def _send_msg91(self, phone: str, message: str) -> bool:
        """Send SMS via MSG91."""
        url = "https://api.msg91.com/api/v5/flow/"

        payload = {
            "sender": self.sender_id,
            "route": "4",
            "country": "91",
            "sms": [{"message": message, "to": [phone]}],
        }

        headers = {"authkey": self.api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code == 200

    async def _send_twilio(self, phone: str, message: str) -> bool:
        """Send SMS via Twilio."""
        # Twilio requires account SID and auth token
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_FROM_NUMBER

        if not all([account_sid, auth_token, from_number]):
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        data = {"From": from_number, "To": phone, "Body": message}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data, auth=(account_sid, auth_token))
            return response.status_code in [200, 201]


class InAppNotifier(BaseNotifier):
    """In-app notification storage."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send(
        self,
        recipient: str,  # user_id
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store notification in database."""
        try:
            notification = Notification(
                user_id=recipient,
                type=data.get("type", "system") if data else "system",
                title=title,
                message=message,
                data=data,
            )
            self.db.add(notification)
            await self.db.commit()
            return True
        except Exception as e:
            print(f"Failed to store in-app notification: {e}")
            await self.db.rollback()
            return False


class NotificationService:
    """
    Main notification service that orchestrates sending notifications
    across multiple channels based on user preferences.
    """

    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.email_notifier = EmailNotifier()
        self.sms_notifier = SMSNotifier()

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> Dict[str, bool]:
        """
        Send notification to user across configured channels.

        Returns dict of channel -> success status.
        """
        results = {}

        # Get user and preferences
        user = await self._get_user(user_id)
        if not user:
            return {"error": False}

        preferences = await self._get_preferences(user_id)

        # Determine channels to use
        if channels is None:
            channels = self._get_channels_for_type(notification_type, preferences)

        # Prepare notification data
        notification_data = data or {}
        notification_data["type"] = notification_type.value

        # Send to each channel
        for channel in channels:
            if channel == NotificationChannel.EMAIL and user.email:
                results["email"] = await self.email_notifier.send(
                    user.email, title, message, notification_data
                )

            elif channel == NotificationChannel.SMS and user.phone:
                results["sms"] = await self.sms_notifier.send(
                    user.phone, title, message, notification_data
                )

            elif channel == NotificationChannel.IN_APP and self.db:
                in_app_notifier = InAppNotifier(self.db)
                results["in_app"] = await in_app_notifier.send(
                    user_id, title, message, notification_data
                )

        return results

    async def send_trade_notification(
        self,
        user_id: str,
        trade_data: dict,
    ) -> Dict[str, bool]:
        """Send trade execution notification."""
        symbol = trade_data.get("symbol", "Unknown")
        side = trade_data.get("side", "Unknown")
        quantity = trade_data.get("quantity", 0)
        price = trade_data.get("price", 0)

        title = f"Trade Executed: {side} {symbol}"
        message = f"Your order to {side} {quantity} units of {symbol} has been executed at {price}."

        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.TRADE,
            data=trade_data,
        )

    async def send_order_notification(
        self,
        user_id: str,
        order_data: dict,
    ) -> Dict[str, bool]:
        """Send order status notification."""
        symbol = order_data.get("symbol", "Unknown")
        status = order_data.get("status", "unknown")
        order_id = order_data.get("order_id", "")

        title = f"Order {status.title()}: {symbol}"
        message = f"Order {order_id} for {symbol} is now {status}."

        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.ORDER,
            data=order_data,
        )

    async def send_risk_alert(
        self,
        user_id: str,
        alert_data: dict,
    ) -> Dict[str, bool]:
        """Send risk management alert."""
        alert_type = alert_data.get("alert_type", "Risk Alert")
        strategy_name = alert_data.get("strategy_name", "Unknown")

        title = f"Risk Alert: {alert_type}"
        message = alert_data.get("message", f"A risk condition has been triggered for {strategy_name}.")

        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.RISK_ALERT,
            data=alert_data,
            channels=[NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.IN_APP],
        )

    async def send_strategy_notification(
        self,
        user_id: str,
        strategy_data: dict,
    ) -> Dict[str, bool]:
        """Send strategy status notification."""
        strategy_name = strategy_data.get("strategy_name", "Unknown")
        status = strategy_data.get("status", "updated")

        title = f"Strategy {status.title()}: {strategy_name}"
        message = strategy_data.get("message", f"Your strategy {strategy_name} has been {status}.")

        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.STRATEGY,
            data=strategy_data,
        )

    async def _get_user(self, user_id: str) -> Optional[User]:
        """Get user from database."""
        if not self.db:
            return None
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _get_preferences(self, user_id: str) -> Optional[NotificationPreference]:
        """Get user notification preferences."""
        if not self.db:
            return None
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _get_channels_for_type(
        self,
        notification_type: NotificationType,
        preferences: Optional[NotificationPreference],
    ) -> List[NotificationChannel]:
        """Determine which channels to use based on type and preferences."""
        channels = []

        if preferences is None:
            # Default: all channels for important types
            if notification_type in [NotificationType.RISK_ALERT]:
                return [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.IN_APP]
            return [NotificationChannel.EMAIL, NotificationChannel.IN_APP]

        # Always include in-app if enabled
        if preferences.in_app_enabled:
            channels.append(NotificationChannel.IN_APP)

        # Check type-specific preferences
        if notification_type == NotificationType.TRADE and preferences.trade_alerts:
            if preferences.email_enabled:
                channels.append(NotificationChannel.EMAIL)
            if preferences.sms_enabled:
                channels.append(NotificationChannel.SMS)

        elif notification_type == NotificationType.RISK_ALERT and preferences.risk_alerts:
            # Always send risk alerts via all enabled channels
            if preferences.email_enabled:
                channels.append(NotificationChannel.EMAIL)
            if preferences.sms_enabled:
                channels.append(NotificationChannel.SMS)

        elif notification_type == NotificationType.DAILY_SUMMARY and preferences.daily_summary:
            if preferences.email_enabled:
                channels.append(NotificationChannel.EMAIL)

        elif notification_type in [NotificationType.ORDER, NotificationType.STRATEGY]:
            if preferences.trade_alerts:
                if preferences.email_enabled:
                    channels.append(NotificationChannel.EMAIL)

        elif notification_type == NotificationType.SYSTEM:
            if preferences.email_enabled:
                channels.append(NotificationChannel.EMAIL)

        return channels


# Convenience functions for common notifications

async def notify_trade_executed(db: AsyncSession, user_id: str, trade_data: dict):
    """Notify user of trade execution."""
    service = NotificationService(db)
    return await service.send_trade_notification(user_id, trade_data)


async def notify_order_status(db: AsyncSession, user_id: str, order_data: dict):
    """Notify user of order status change."""
    service = NotificationService(db)
    return await service.send_order_notification(user_id, order_data)


async def notify_risk_breach(db: AsyncSession, user_id: str, alert_data: dict):
    """Notify user of risk breach."""
    service = NotificationService(db)
    return await service.send_risk_alert(user_id, alert_data)


async def notify_strategy_status(db: AsyncSession, user_id: str, strategy_data: dict):
    """Notify user of strategy status change."""
    service = NotificationService(db)
    return await service.send_strategy_notification(user_id, strategy_data)
