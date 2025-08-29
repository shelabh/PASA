# src/actions/email_sender.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def send_email(to_email: str, subject: str, body: str, attachments: list[tuple[str, bytes, str]] | None = None):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise ValueError("Missing EMAIL_ADDRESS or EMAIL_PASSWORD in environment.")

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Attach any files (filename, bytes, mime_type)
        if attachments:
            for filename, file_bytes, mime_type in attachments:
                maintype, subtype = (mime_type.split("/", 1) if "/" in mime_type else ("application", "octet-stream"))
                part = MIMEBase(maintype, subtype)
                part.set_payload(file_bytes)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Secure the connection
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"📧 Email successfully sent to {to_email}")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
