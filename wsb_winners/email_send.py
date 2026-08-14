"""通过 google-workspace 的 google_api.py Gmail CLI 发送邮件。"""
from __future__ import annotations

import subprocess

from . import config


def send_email(subject: str, html_body: str) -> tuple[bool, str]:
    """发送 HTML 邮件到 MAIL_TO。返回 (ok, err)。"""
    try:
        cmd = [
            "python3", config.GMAIL_CLI, "gmail", "send",
            "--to", config.MAIL_TO,
            "--subject", subject,
            "--body", html_body, "--html",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return True, ""
        return False, (r.stderr or r.stdout)[-400:]
    except Exception as e:  # noqa: BLE001
        return False, str(e)[-400:]