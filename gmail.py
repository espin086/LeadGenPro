from dotenv import load_dotenv
import os
from email.message import EmailMessage
import ssl
import smtplib


def send_email(sender, receiver, subject, body, bcc=None):
    """
    Sends an email using Gmail SMTP with optional BCC.

    Parameters:
    sender (str): The email address of the sender.
    receiver (str): The email address of the receiver.
    subject (str): The subject of the email.
    body (str): The content of the email.
    bcc (str, optional): Comma-separated BCC email addresses. Default is None.

    Returns:
    None
    """
    # Load the password from the environment variable
    password = os.getenv('EMAIL_PASSWORD')

    # Create the email
    em = EmailMessage()
    em['From'] = sender
    em['To'] = receiver
    em['Subject'] = subject
    em.set_content(body)

    if bcc:
        em['Bcc'] = bcc
        recipients = [receiver] + bcc.split(',')
    else:
        recipients = [receiver]

    context = ssl.create_default_context()

    # Send the email via Gmail SMTP
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(sender, password)
            server.sendmail(sender, recipients, em.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Get sender and BCC from environment variables
    SENDER = os.getenv('EMAIL_SENDER')

    # Define your email parameters
    receiver = "jj.espinoza.la@gmail.com"
    subject = "email from Python"
    body = """
    Email from python
    """
    bcc = "bump@go.rebump.cc"  # Example of BCC addresses

    # Call the send_email function
    send_email(SENDER, receiver, subject, body, bcc=bcc)