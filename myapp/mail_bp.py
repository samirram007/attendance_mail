from flask import Blueprint, current_app
from flask_mail import Message
# from app import mail

bp = Blueprint('mail_bp', __name__)

@bp.route('/send-email')
def send_email():
    msg = Message("Test Subject",
                  recipients=["samirram007@gmail.com","priyanshuchourasia916@gmail.com"])
    msg.body = "This is a test email."
    # Use current_app.extensions to get mail instance dynamically
    # mail.send(msg)
    current_app.extensions.get('mail').send(msg)
    return "Email sent!"

async def send_email_async(subject, body, recipient):
    msg = Message(subject,
                  recipients=[recipient])
    msg.body = body
    # Use current_app.extensions to get mail instance dynamically
    current_app.extensions.get('mail').send(msg)
    return "Email sent!"

@bp.route('/send-email-attachment', methods=['POST'])
def send_email_with_attachment(subject, body, recipient, attachment_path):
    msg = Message(subject,
                  recipients=[recipient])
    msg.body = body

    if attachment_path:
        with current_app.open_resource(attachment_path) as fp:
            msg.attach(attachment_path.split('/')[-1], "application/pdf", fp.read())
    
    current_app.extensions.get('mail').send(msg)