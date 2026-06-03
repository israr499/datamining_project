

import os
import smtplib
import random
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import dns.resolver
except ImportError:
    dns = None



SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD", "").strip()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def is_valid_email_format(email):
    if not email:
        return False

    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email) is not None


def get_email_domain(email):
    try:
        return email.split("@")[1].lower().strip()
    except Exception:
        return ""


def has_valid_mx_record(domain):
    try:
        if dns is None:
            return False

        answers = dns.resolver.resolve(domain, "MX")
        return len(answers) > 0

    except Exception:
        return False


def is_valid_email(email):
    if not is_valid_email_format(email):
        return False

    domain = get_email_domain(email)

    if not domain:
        return False

    if not has_valid_mx_record(domain):
        return False

    return True


def validate_email_with_reason(email):
    if not is_valid_email_format(email):
        return {
            "success": False,
            "message": "Invalid email format."
        }

    domain = get_email_domain(email)

    if not domain:
        return {
            "success": False,
            "message": "Invalid email domain."
        }

    if dns is None:
        return {
            "success": False,
            "message": "Email validation package is missing. Please install dnspython."
        }

    if not has_valid_mx_record(domain):
        return {
            "success": False,
            "message": "Email domain does not exist or cannot receive emails."
        }

    return {
        "success": True,
        "message": "Email format and domain are valid."
    }



def generate_otp():
    return str(random.randint(100000, 999999))




def send_otp_email(receiver_email, otp_code):
    try:
        email_check = validate_email_with_reason(receiver_email)

        if not email_check["success"]:
            return email_check

        if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
            return {
                "success": False,
                "message": "Email sender is not configured. Please set SENDER_EMAIL and SENDER_APP_PASSWORD in environment variables."
            }

        subject = "ElectroGuard Email Verification OTP"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f9fb; padding: 20px;">
                <div style="max-width: 550px; margin: auto; background: white; padding: 25px; border-radius: 14px; border-top: 5px solid #2E86AB;">
                    <h2 style="color: #2E86AB;">ElectroGuard Verification</h2>

                    <p>Hello,</p>

                    <p>Your OTP code for ElectroGuard account verification is:</p>

                    <div style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1B4F6E; margin: 25px 0;">
                        {otp_code}
                    </div>

                    <p>This OTP is valid for a short time. Please do not share it with anyone.</p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 25px 0;">

                    <p style="font-size: 13px; color: #777;">
                        ElectroGuard - Smart Electricity Anomaly Detection System
                    </p>
                </div>
            </body>
        </html>
        """

        text_body = f"""
ElectroGuard Email Verification

Your OTP code is: {otp_code}

Please do not share this OTP with anyone.
"""

        message = MIMEMultipart("alternative")
        message["From"] = SENDER_EMAIL
        message["To"] = receiver_email
        message["Subject"] = subject

        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
        server.quit()

        return {
            "success": True,
            "message": "OTP sent successfully."
        }

    except smtplib.SMTPRecipientsRefused:
        return {
            "success": False,
            "message": "Email address was rejected by the mail server."
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Sender email authentication failed. Check Gmail App Password."
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send OTP: {str(e)}"
        }



if __name__ == "__main__":
    test_email = input("Enter receiver email: ").strip()
    otp = generate_otp()

    print(f"Generated OTP: {otp}")
    result = send_otp_email(test_email, otp)
    print(result)