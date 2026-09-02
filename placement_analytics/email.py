"""Outbound email via Resend's HTTP API.

Render (and most PaaS free/starter tiers) block raw outbound SMTP --
smtplib.SMTP(...).connect() fails with "Network is unreachable"
regardless of how correct the mail credentials are, since it's the
platform's network layer refusing the connection, not an auth problem.
Sending over HTTPS instead sidesteps that entirely, since outbound
HTTPS is essentially always allowed.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

RESEND_API_URL = 'https://api.resend.com/emails'


def _mask_email(email):
    local, _, domain = email.partition('@')
    if len(local) <= 2:
        masked_local = local[:1] + '*' * max(len(local) - 1, 1)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f'{masked_local}@{domain}' if domain else masked_local


def send_email(to, subject, body):
    """Best-effort send. Never raises -- callers that already treat mail
    delivery as non-critical (OTP codes, placement notifications) can
    call this without their own try/except."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        logger.warning('RESEND_API_KEY is not set -- email to %s was not sent', _mask_email(to))
        return False

    from_address = os.environ.get('RESEND_FROM_EMAIL', 'Placement Analytics <onboarding@resend.dev>')
    try:
        response = requests.post(
            RESEND_API_URL,
            headers={'Authorization': f'Bearer {api_key}'},
            json={'from': from_address, 'to': [to], 'subject': subject, 'text': body},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error(
            'Failed to send email to %s via Resend (%s)',
            _mask_email(to), type(exc).__name__,
        )
        return False
