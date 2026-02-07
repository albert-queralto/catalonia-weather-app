import smtplib
from email.mime.text import MIMEText
from app.core.config import settings

EMAIL_USERNAME = settings.email_username
EMAIL_PASSWORD = settings.email_password

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USERNAME
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())