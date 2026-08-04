from urllib.parse import urlparse
from flask import request, redirect, url_for


def safe_redirect_back(default_endpoint):
    """Redirect to the referring page only if it's on this site.

    request.referrer is attacker-controlled (it's just a header the client
    sends), so blindly trusting it -- especially in the CSRF error handler,
    which fires exactly when a cross-site request was blocked -- would bounce
    the user straight to whatever site sent the forged request.
    """
    ref = request.referrer
    if ref and urlparse(ref).netloc == urlparse(request.host_url).netloc:
        return redirect(ref)
    return redirect(url_for(default_endpoint))


def any_blank(*values):
    """True if any of the given form values is missing, empty, or whitespace-only."""
    return any(not (v or '').strip() for v in values)


def excel_safe(val):
    """Neutralize formula-injection payloads (CWE-1236) before writing to a cell.

    name/skills/company_name reach here from admin input and bulk CSV upload.
    A value like =cmd|'/c calc'!A1 sits in the DB as plain text but becomes a
    live formula the moment someone opens the exported .xlsx in Excel.
    """
    if isinstance(val, str) and val[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + val
    return val
