"""Entry point. Render's start command runs this file directly.

The extension/util re-exports below look unused but aren't dead code --
scripts/init_passwords.py and the whole test suite do `from app import app,
mysql` / `import app as app_module`, so removing them breaks both.
"""
from placement_analytics import create_app
from placement_analytics.extensions import mysql, limiter, csrf  # noqa: F401
from placement_analytics.utils import safe_redirect_back, any_blank, excel_safe  # noqa: F401

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
