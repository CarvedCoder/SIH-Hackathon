# notification_service.py

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

# Import your database models
from backend.api.models.database import AuthorityAlerts, HazardReport, SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthorityNotificationService:
    def __init__(self):
        # Email configuration (Gmail)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_address = os.getenv("GMAIL_ADDRESS", "your-email@gmail.com")
        self.email_password = os.getenv("GMAIL_APP_PASSWORD", "your-app-password")  # Use App Password, not regular password
        
        # Twilio SMS configuration
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "your-account-sid")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "your-auth-token")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")
        
        # Initialize Twilio client
        try:
            self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.twilio_client = None
        
        # Authority contact information
        self.authority_contacts = {
            'coast_guard': {
                'email': ['coastguard.ops@example.gov.in'],
                'phone': ['+919876543210'],
                'name': 'Indian Coast Guard Operations'
            },
            'disaster_management': {
                'email': ['ndma.alerts@example.gov.in', 'sdma.alerts@example.gov.in'],
                'phone': ['+919876543211', '+919876543212'],
                'name': 'National/State Disaster Management Authority'
            },
            'navy': {
                'email': ['navy.maritime@example.gov.in'],
                'phone': ['+919876543213'],
                'name': 'Indian Navy Maritime Operations'
            },
            'police': {
                'email': ['marine.police@example.gov.in'],
                'phone': ['+919876543214'],
                'name': 'Marine Police'
            },
            'fire_dept': {
                'email': ['fire.emergency@example.gov.in'],
                'phone': ['+919876543215'],
                'name': 'Fire and Rescue Services'
            },
            'medical_emergency': {
                'email': ['emergency.medical@example.gov.in'],
                'phone': ['+919876543216', '108'],  # Including emergency number
                'name': 'Emergency Medical Services'
            },
            'port_authority': {
                'email': ['port.operations@example.gov.in'],
                'phone': ['+919876543217'],
                'name': 'Port Authority Operations'
            }
        }
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)

    def get_db(self):
        """Get database session"""
        db = SessionLocal()
        try:
            return db
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if db:
                db.close()
            raise

    def format_alert_message(self, alert: AuthorityAlerts, report: HazardReport) -> Dict[str, str]:
        """Format alert message for email and SMS"""
        
        # Priority emoji/indicator
        priority_indicators = {
            'urgent': '🚨 URGENT',
            'high_priority': '⚠️ HIGH PRIORITY',
            'standard': '📢 ALERT',
            'informational': 'ℹ️ INFO'
        }
        
        priority = priority_indicators.get(alert.status, '📢 ALERT')
        
        # Format location
        location = f"{report.location_name or 'Unknown'} ({report.latitude:.4f}, {report.longitude:.4f})"
        
        # Email subject and body
        email_subject = f"{priority}: {report.hazard_type.replace('_', ' ').title()} - {location}"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d9534f;">{priority}</h2>
            
            <h3>Hazard Report Details:</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Alert ID:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Report ID:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{report.id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Hazard Type:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{report.hazard_type.replace('_', ' ').title()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Location:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Severity:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{report.severity}/5</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Priority Score:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{report.priority_score:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Description:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{report.description}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Time Reported:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{report.timestamp.strftime('%Y-%m-%d %H:%M:%S IST')}</td>
                </tr>
            </table>
            
            <h3>Alert Message:</h3>
            <p style="background-color: #f0f0f0; padding: 10px; border-left: 4px solid #d9534f;">
                {alert.message}
            </p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated alert from the Coastal Hazard Reporting System.<br>
                Please take appropriate action based on the severity and nature of the hazard.<br>
                Dashboard: <a href="http://localhost:8001/dashboard">View Full Dashboard</a>
            </p>
        </body>
        </html>
        """
        
        # SMS body (shorter version)
        sms_body = (
            f"{priority}\n"
            f"Type: {report.hazard_type.replace('_', ' ').title()}\n"
            f"Location: {report.location_name or 'Check coordinates'}\n"
            f"Coords: {report.latitude:.4f},{report.longitude:.4f}\n"
            f"Severity: {report.severity}/5\n"
            f"Message: {alert.message[:100]}..."
            if len(alert.message) > 100 else alert.message
        )
        
        return {
            'email_subject': email_subject,
            'email_body': email_body,
            'sms_body': sms_body
        }

    def send_email(self, to_addresses: List[str], subject: str, body: str) -> bool:
        """Send email notification via Gmail"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_address
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = subject
            
            # Attach HTML body
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            # Connect to Gmail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_addresses}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_sms(self, phone_numbers: List[str], message: str) -> List[Dict]:
        """Send SMS notification via Twilio"""
        results = []
        
        if not self.twilio_client:
            logger.error("Twilio client not initialized")
            return results
        
        for phone in phone_numbers:
            try:
                message_obj = self.twilio_client.messages.create(
                    body=message[:1600],  # SMS character limit
                    from_=self.twilio_phone_number,
                    to=phone
                )
                
                results.append({
                    'phone': phone,
                    'status': 'sent',
                    'sid': message_obj.sid
                })
                logger.info(f"SMS sent successfully to {phone}")
                
            except Exception as e:
                logger.error(f"Failed to send SMS to {phone}: {e}")
                results.append({
                    'phone': phone,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results

    async def process_alert(self, alert_id: str) -> Dict:
        """Process a single alert and send notifications"""
        db = self.get_db()
        try:
            # Get alert and related report
            alert = db.query(AuthorityAlerts).filter(AuthorityAlerts.id == alert_id).first()
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            
            report = db.query(HazardReport).filter(HazardReport.id == alert.report_id).first()
            if not report:
                raise ValueError(f"Report {alert.report_id} not found")
            
            # Get contact information
            contacts = self.authority_contacts.get(alert.authority_type, {})
            if not contacts:
                logger.warning(f"No contacts found for authority type: {alert.authority_type}")
                return {'status': 'no_contacts'}
            
            # Format messages
            messages = self.format_alert_message(alert, report)
            
            # Send notifications
            results = {
                'alert_id': alert_id,
                'authority_type': alert.authority_type,
                'email_results': [],
                'sms_results': []
            }
            
            # Send emails
            if contacts.get('email'):
                email_sent = self.send_email(
                    contacts['email'],
                    messages['email_subject'],
                    messages['email_body']
                )
                results['email_results'] = {
                    'recipients': contacts['email'],
                    'status': 'sent' if email_sent else 'failed'
                }
            
            # Send SMS
            if contacts.get('phone'):
                sms_results = self.send_sms(
                    contacts['phone'],
                    messages['sms_body']
                )
                results['sms_results'] = sms_results
            
            # Update alert status in database (optional)
            alert.notification_sent = True
            alert.notification_timestamp = datetime.now()
            db.commit()
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing alert {alert_id}: {e}")
            return {
                'alert_id': alert_id,
                'status': 'error',
                'error': str(e)
            }
        finally:
            db.close()

    async def process_pending_alerts(self) -> List[Dict]:
        """Process all pending alerts that haven't been notified"""
        db = self.get_db()
        try:
            # Get unprocessed alerts
            pending_alerts = db.query(AuthorityAlerts).filter(
                AuthorityAlerts.notification_sent == None
            ).all()
            
            results = []
            for alert in pending_alerts:
                result = await self.process_alert(alert.id)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing pending alerts: {e}")
            return []
        finally:
            db.close()

    async def monitor_alerts(self, interval: int = 30):
        """Continuously monitor for new alerts and send notifications"""
        logger.info(f"Starting alert monitor with {interval}s interval")
        
        while True:
            try:
                results = await self.process_pending_alerts()
                if results:
                    logger.info(f"Processed {len(results)} alerts")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(interval)


# Standalone functions for testing
def test_email_notification():
    """Test email notification"""
    service = AuthorityNotificationService()
    
    # Test email
    result = service.send_email(
        ['test@example.com'],
        'Test Alert: Coastal Hazard',
        '<h1>Test Alert</h1><p>This is a test notification.</p>'
    )
    print(f"Email test result: {result}")


def test_sms_notification():
    """Test SMS notification"""
    service = AuthorityNotificationService()
    
    # Test SMS
    result = service.send_sms(
        ['+919876543210'],
        'Test Alert: Coastal hazard detected. This is a test message.'
    )
    print(f"SMS test results: {result}")


async def main():
    """Main function to run the notification service"""
    service = AuthorityNotificationService()
    
    # Process any pending alerts once
    results = await service.process_pending_alerts()
    print(f"Processed {len(results)} pending alerts")
    
    # Start continuous monitoring
    await service.monitor_alerts(interval=30)


if __name__ == "__main__":
    # Run the service
    asyncio.run(main())