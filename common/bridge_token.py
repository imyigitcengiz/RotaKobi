"""WhatsApp köprüsü paylaşılan Bearer token."""

from __future__ import annotations

import os
from pathlib import Path

SECRETS_DIR = Path(os.environ.get('COOLOPS_SECRETS_DIR') or os.environ.get('KOBIOPS_SECRETS_DIR') or '/run/kobiops-secrets')
TOKEN_FILENAME = 'whatsapp_bridge_token'


def secrets_token_path() -> Path:
    return SECRETS_DIR / TOKEN_FILENAME


def read_bridge_token() -> str:
    env = os.environ.get('WHATSAPP_BRIDGE_TOKEN', '').strip()
    if env:
        return env
    path = secrets_token_path()
    if path.is_file():
        try:
            return path.read_text(encoding='utf-8').strip()
        except OSError:
            return ''
    return ''


def write_bridge_token(token: str) -> Path | None:
    token = (token or '').strip()
    if not token:
        return None
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    path = secrets_token_path()
    path.write_text(token, encoding='utf-8')
    try:
        os.chmod(path, 0o600)
        os.chmod(SECRETS_DIR, 0o700)
    except OSError:
        pass
    return path


def bridge_auth_headers() -> dict[str, str]:
    token = read_bridge_token()
    if not token:
        return {}
    return {'Authorization': f'Bearer {token}'}
