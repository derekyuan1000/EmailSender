from flask import Flask, render_template, request
from flask_mail import Mail, Message
import os
import re
import smtplib

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
# MAIL CONFIG
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME', ''))
# BCC HERE
app.config['HIDDEN_BCC'] = os.getenv('HIDDEN_BCC', '').strip()

mail = Mail(app)


def _parse_emails(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r'[;,]', value)
    return [p.strip() for p in parts if p.strip()]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/send', methods=['POST'])
def send_email():
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        return "Mail credentials are not configured. Set MAIL_USERNAME and MAIL_PASSWORD (e.g., via .env).", 500

    to_raw = request.form.get('to')
    cc_raw = request.form.get('cc')
    bcc_raw = request.form.get('bcc')
    subject = request.form.get('subject') or ''
    body = request.form.get('body') or ''

    to_list = _parse_emails(to_raw)
    cc_list = _parse_emails(cc_raw)
    bcc_list = _parse_emails(bcc_raw)

    hidden_bcc = _parse_emails(app.config.get('HIDDEN_BCC'))
    if hidden_bcc:
        existing = {e.lower() for e in bcc_list}
        bcc_list.extend([e for e in hidden_bcc if e.lower() not in existing])

    if not to_list:
        return "'To' is required.", 400

    msg = Message(subject,
                  sender=app.config.get('MAIL_DEFAULT_SENDER') or app.config['MAIL_USERNAME'],
                  recipients=to_list,
                  cc=cc_list,
                  bcc=bcc_list)

    msg.body = body

    html_body = re.sub(r'(https?://[^\s]+)', r'<a href="\1">\1</a>', body)
    msg.html = html_body.replace('\n', '<br>')

    try:
        mail.send(msg)
    except smtplib.SMTPAuthenticationError as e:
        return ("SMTP authentication failed. Verify username/app password and provider settings. "
                f"Details: {e.smtp_error.decode(errors='ignore') if hasattr(e, 'smtp_error') else str(e)}"), 500
    except smtplib.SMTPException as e:
        return f"SMTP error: {str(e)}", 500

    return "Email sent successfully!"


if __name__ == '__main__':
    app.run(debug=True)
