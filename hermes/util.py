"""
Project-wide utilities.
"""

import logging
import random
import requests
import smtplib
import string

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .settings import settings


log = logging.getLogger(__name__)


def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    """Generate a random ID of specified length

    Args:
        size: the length of the id to generate
        chars: the characters to use

    Returns:
        string of random id generated
    """
    return ''.join(random.choice(chars) for _ in range(size))


def slack_message(message):
    """Post a message to Slack if a webhook as been defined.

    Args:
        message: the content of the Slack post
    """
    if not settings.slack_webhook:
        return

    if settings.slack_proxyhost:
        proxies = {
            "http": "http://{}".format(settings.slack_proxyhost),
            "https": "http://{}".format(settings.slack_proxyhost)
        }
    else:
        proxies = None

    json = {
        "text": message,
        "username": "Hermes Log",
        "icon_emoji": ":hermes:",
    }
    try:
        log.debug("{} {}".format(settings.slack_webhook, json))
        response = requests.post(
            settings.slack_webhook, json=json, proxies=proxies
        )
    except Exception as exc:
        log.warn("Error writing to Slack: {}".format(exc.message))


def email_message(recipients, subject, message, html_message=None, cc=None, sender=None):
    """Email a message to a user.

    Args:
        subject: the subject of the email we wish to send
        message: the content of the email we wish to send
        recipients: the email address to whom we wish to send the email
        html_message: optional html formatted message we wish to send
        cc: optional list of email addresses to carbon copy
        sender: optional sender email address
    """

    if not settings.email_notifications:
        return

    if isinstance(recipients, basestring):
        recipients = recipients.split(",")
    if isinstance(settings.email_always_copy, basestring):
        extra_recipients = settings.email_always_copy.split(",")
    else:
        extra_recipients = [settings.email_always_copy]

    if cc and isinstance(cc, basestring):
        extra_recipients.append(cc)
    elif cc:
        extra_recipients.extend(cc)

    # If this is the dev environment, we need to only send to the dev recipient
    # and put a tag explaining what would have happened

    if settings.environment == "dev":
        recipients_statement = "To: {}   CC: {}\n".format(
            recipients, extra_recipients
        )
        subject = "[DEV] {}".format(subject)
        message = (
            "[DEV]: Sent to {}\nOriginally addressed as: {}\n\n{}".format(
                settings.dev_email_recipient,
                recipients_statement,
                message
            )
        )
        if html_message:
            html_message = (
                "<p><strong>DEV:</strong> Sent to {}<br />"
                "Originally addressed as: {}<br/></p>{}".format(
                    settings.dev_email_recipient,
                    recipients_statement,
                    html_message
                )
            )
        recipients = [settings.dev_email_recipient]
        extra_recipients = []

    part1 = MIMEText(message, 'plain')
    if html_message:
        part2 = MIMEText(html_message, 'html')
    else:
        part2 = None

    if part1 and part2:
        msg = MIMEMultipart('alternative')
        msg.attach(part1)
        msg.attach(part2)
    else:
        msg = part1

    msg["Subject"] = subject
    msg["From"] = settings.email_sender_address if not sender else sender
    msg["To"] = ", ".join(recipients)
    msg["Cc"] = ", ".join(extra_recipients)

    logging.debug("Sending email: From {}, To {}, Msg: {}".format(
        settings.email_sender_address,
        recipients + extra_recipients,
        msg.as_string()
    ))

    try:
        smtp = smtplib.SMTP("localhost")
        smtp.sendmail(
            settings.email_sender_address,
            recipients + extra_recipients,
            msg.as_string()
        )
        smtp.quit()
    except Exception as exc:
        log.warn("Error sending email: {}".format(exc.message))


class PluginHelper(object):
    @classmethod
    def request_get(cls, path="", params={}, server=None):
        """Make an HTTP GET request for the given path

        Args:
            path: the full path to the resource
            params: the query parameters to send
            server: the server to talk to, default is query_server
        Returns:
            the http response
        """

        if not server:
            server = settings.query_server

        response = requests.get(server + path, params=params)

        return response

    @classmethod
    def request_post(cls, path="", params={}, json_body={}, server=None):
        """Make an HTTP POST request for the given path

        Args:
            path: the full path to the resource
            params: the query params to send
            json_body: the body of the message in JSON format
            server: the server to talk to, default is query_server
        Returns:
            the http response
        """

        if not server:
            server = settings.query_server

        response = requests.post(
            server + path, params=params, json=json_body
        )

        return response
