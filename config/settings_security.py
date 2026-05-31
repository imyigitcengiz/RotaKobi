"""
Üretim güvenlik ayarları — config.settings sonunda import edilir.

Ortam değişkenleri:
  DJANGO_SECURE_SSL=1          HTTPS redirect + güvenli çerezler + HSTS
  DJANGO_CSP_ENABLED=1           Content-Security-Policy (django-csp gerekmez; SecurityMiddleware header)
  DJANGO_SESSION_COOKIE_AGE      Oturum süresi (saniye, varsayılan 43200 = 12 saat)
"""

from __future__ import annotations

import os

_IS_PROD = not os.environ.get('DJANGO_DEBUG', '1').lower() in ('1', 'true', 'yes')
_USE_SSL = os.environ.get('DJANGO_SECURE_SSL', '').lower() in ('1', 'true', 'yes')

# --- Parola politikası (kurumsal minimum) ---
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
try:
    import argon2  # noqa: F401

    PASSWORD_HASHERS.insert(0, 'django.contrib.auth.hashers.Argon2PasswordHasher')
except ImportError:
    pass

# --- Oturum ---
SESSION_COOKIE_AGE = int(os.environ.get('DJANGO_SESSION_COOKIE_AGE', '43200'))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

if _IS_PROD:
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

if _IS_PROD and _USE_SSL:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get(
        'DJANGO_HSTS_INCLUDE_SUBDOMAINS', '1',
    ).lower() in ('1', 'true', 'yes')
    SECURE_HSTS_PRELOAD = os.environ.get('DJANGO_HSTS_PRELOAD', '0').lower() in ('1', 'true', 'yes')

# CSP: DJANGO_CSP_ENABLED=1 → common.middleware_csp.ContentSecurityPolicyMiddleware
