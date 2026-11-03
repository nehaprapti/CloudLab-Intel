"""
CloudLab Intelligence - Secure Email OTP Delivery Service
Supports real email delivery using SMTP (Gmail, Outlook, College Mail).
Dispatches branded, high-priority HTML verification emails with 6-digit OTP codes
to student email addresses with zero cost.
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    os.environ[key] = val
        except Exception:
            pass


def get_env_var(key, default=None):
    if key not in os.environ:
        load_dotenv()
    return os.environ.get(key, default)


class EmailProvider:
    """
    Handles dispatching real OTP verification emails to student inboxes.
    """
    def __init__(self):
        self.smtp_server = get_env_var("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(get_env_var("SMTP_PORT", "587"))

    def is_configured(self) -> bool:
        """Returns True if sender email and app password are set in .env."""
        email = get_env_var("SMTP_EMAIL", "").strip()
        pwd = get_env_var("SMTP_PASSWORD", "").strip()
        return bool(email and pwd and "@" in email and "your_" not in email)

    def send_otp_email(self, to_email: str, otp_code: str, student_name: str = "Student", pc_id: str = "Lab Workstation") -> dict:
        """
        Sends a branded HTML verification email containing the 6-digit OTP to to_email.
        """
        sender_email = get_env_var("SMTP_EMAIL", "").strip()
        sender_password = get_env_var("SMTP_PASSWORD", "").strip().replace(" ", "")

        if not self.is_configured():
            return {
                "success": False,
                "error": "Email service not configured. Please add SMTP_EMAIL and SMTP_PASSWORD in .env file."
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"CloudLab Intelligence: Verification Code is {otp_code}"
            msg["From"] = f"CloudLab Intelligence <{sender_email}>"
            msg["To"] = to_email
            msg["X-Priority"] = "1"  # High priority header for instant mobile push

            # Plain text fallback
            text_content = (
                f"Hello {student_name},\n\n"
                f"Your CloudLab Intelligence workstation verification code is: {otp_code}\n\n"
                f"Workstation: {pc_id}\n"
                f"Valid for 5 minutes. Do not share this OTP with anyone.\n\n"
                f"Sona College of Technology • Department of Information Technology (Batch 10)"
            )

            # Branded HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
                .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; padding: 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }}
                .header p {{ margin: 6px 0 0; font-size: 12px; opacity: 0.9; }}
                .content {{ padding: 28px 24px; color: #1e293b; text-align: center; }}
                .greeting {{ font-size: 15px; margin-bottom: 12px; color: #334155; }}
                .info-box {{ background: #f1f5f9; border-radius: 8px; padding: 10px 16px; margin: 16px 0; font-size: 13px; color: #475569; }}
                .otp-box {{ background: #eff6ff; border: 2px dashed #3b82f6; border-radius: 12px; padding: 16px; margin: 24px 0; display: inline-block; width: 85%; }}
                .otp-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #2563eb; font-weight: 700; margin-bottom: 6px; }}
                .otp-code {{ font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #1e3a8a; font-family: monospace; }}
                .expiry {{ font-size: 12px; color: #ef4444; font-weight: 600; margin-top: 8px; }}
                .footer {{ background: #f8fafc; border-top: 1px solid #f1f5f9; padding: 16px; font-size: 11px; color: #94a3b8; text-align: center; }}
              </style>
            </head>
            <body>
              <div class="container">
                <div class="header">
                  <h1>CloudLab Intelligence</h1>
                  <p>Sona College of Technology • Dept of Information Technology</p>
                </div>
                <div class="content">
                  <div class="greeting">Hello <b>{student_name}</b>,</div>
                  <p style="font-size: 13px; color: #64748b; margin: 0 0 16px;">
                    Use the verification code below to authenticate your lab workstation session.
                  </p>
                  <div class="otp-box">
                    <div class="otp-label">Workstation One-Time Password</div>
                    <div class="otp-code">{otp_code}</div>
                    <div class="expiry">⏱ Valid for 5 minutes</div>
                  </div>
                  <div class="info-box">
                    🖥 <b>Assigned PC:</b> {pc_id}<br/>
                    🔒 Do not share this OTP with anyone. Proxy login is strictly monitored.
                  </div>
                </div>
                <div class="footer">
                  Batch 10 (2026-27) • IT Department Computer Laboratory<br/>
                  This is an automated security email. Please do not reply.
                </div>
              </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Connect and send via SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=12.0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [to_email], msg.as_string())
            server.quit()

            return {
                "success": True,
                "provider": "smtp_email",
                "recipient": to_email
            }
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "error": "Gmail Authentication Failed: Please check your SMTP_EMAIL and 16-letter App Password in .env file."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Email delivery error: {str(e)}"
            }

    def send_report_email(self, to_email: str, title: str, pdf_path: str, summary: dict = None, remarks: str = "") -> dict:
        """
        Sends an academic PDF report as an email attachment to any entered staff/administrator email.
        """
        to_email = (to_email or "").strip().lower()
        if not to_email or "@" not in to_email:
            return {"success": False, "error": "Invalid recipient email address."}

        sender_email = get_env_var("SMTP_EMAIL", "").strip()
        sender_password = get_env_var("SMTP_PASSWORD", "").strip().replace(" ", "")

        if not self.is_configured():
            return {
                "success": False,
                "error": "Email service not configured. Please add SMTP_EMAIL and SMTP_PASSWORD in .env file."
            }

        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"CloudLab Intelligence: {title}"
            msg["From"] = f"CloudLab Intelligence <{sender_email}>"
            msg["To"] = to_email

            body_container = MIMEMultipart("alternative")

            summary = summary or {}
            student_name = summary.get("student_name", "")
            reg_no = summary.get("reg_no", "")
            focus_score = summary.get("focus_score", "N/A")
            total_duration = summary.get("total_duration", "")
            total_students = summary.get("total_students", "")

            details_html = ""
            if student_name or reg_no:
                details_html += f"<tr><td style='padding:8px 12px;font-weight:600;color:#475569;'>Student:</td><td style='padding:8px 12px;'><b>{student_name}</b> ({reg_no})</td></tr>"
            if focus_score != "N/A":
                details_html += f"<tr><td style='padding:8px 12px;font-weight:600;color:#475569;'>Focus Score:</td><td style='padding:8px 12px;'><b style='color:#059669;'>{focus_score}%</b></td></tr>"
            if total_duration:
                details_html += f"<tr><td style='padding:8px 12px;font-weight:600;color:#475569;'>Duration:</td><td style='padding:8px 12px;'>{total_duration}</td></tr>"
            if total_students:
                details_html += f"<tr><td style='padding:8px 12px;font-weight:600;color:#475569;'>Total Students:</td><td style='padding:8px 12px;'><b>{total_students} Students</b></td></tr>"
            if remarks:
                details_html += f"<tr><td style='padding:8px 12px;font-weight:600;color:#475569;'>Faculty Remarks:</td><td style='padding:8px 12px;'><i>{remarks}</i></td></tr>"

            plain_text = (
                f"CloudLab Intelligence Academic Report\n\n"
                f"{title}\n"
                f"Generated on: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}\n"
                f"Recipient: {to_email}\n\n"
                f"Please find the attached official academic report PDF.\n\n"
                f"Sona College of Technology • Department of Information Technology (Batch 10)"
            )

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
                .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; padding: 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
                .header p {{ margin: 6px 0 0; font-size: 12px; opacity: 0.9; }}
                .content {{ padding: 24px; color: #1e293b; }}
                .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; background: #eff6ff; color: #1d4ed8; font-weight: 700; font-size: 12px; margin-bottom: 14px; border: 1px solid #bfdbfe; }}
                .table-box {{ width: 100%; border-collapse: collapse; margin: 16px 0; background: #f8fafc; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; font-size: 13px; }}
                .footer {{ background: #f8fafc; border-top: 1px solid #f1f5f9; padding: 16px; font-size: 11px; color: #94a3b8; text-align: center; }}
              </style>
            </head>
            <body>
              <div class="container">
                <div class="header">
                  <h1>CloudLab Intelligence</h1>
                  <p>Sona College of Technology • Dept of Information Technology</p>
                </div>
                <div class="content">
                  <div class="badge">Official Academic Report Dispatch</div>
                  <h2 style="font-size:16px;margin:0 0 10px;color:#0f172a;">{title}</h2>
                  <p style="font-size:13px;color:#64748b;margin:0 0 16px;">
                    This official academic audit report has been generated by the CloudLab Intelligence platform and dispatched to your staff email. The complete report is attached as a PDF document.
                  </p>
                  <table class="table-box">
                    {details_html}
                  </table>
                  <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:12px;color:#065f46;font-size:12px;margin-top:16px;">
                    📎 <b>Attached Document:</b> {os.path.basename(pdf_path) if pdf_path else 'Report.pdf'} (Attached below)
                  </div>
                </div>
                <div class="footer">
                  Batch 10 (2026-27) • IT Department Computer Laboratory<br/>
                  Confidential Academic Record • Sona College of Technology
                </div>
              </div>
            </body>
            </html>
            """

            body_container.attach(MIMEText(plain_text, "plain"))
            body_container.attach(MIMEText(html_content, "html"))
            msg.attach(body_container)

            # Attach PDF
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
                attach_name = os.path.basename(pdf_path)
                pdf_attachment.add_header("Content-Disposition", "attachment", filename=attach_name)
                msg.attach(pdf_attachment)

            # Connect and send via SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=18.0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [to_email], msg.as_string())
            server.quit()

            return {
                "success": True,
                "provider": "smtp_email",
                "recipient": to_email,
                "message": f"Report successfully delivered to {to_email} via Gmail SMTP."
            }
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "error": "Gmail Authentication Failed: Please check your SMTP_EMAIL and 16-letter App Password in .env file."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Email delivery error: {str(e)}"
            }


# Global singleton instance
email_provider = EmailProvider()
