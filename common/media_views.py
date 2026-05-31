"""Üretimde medya dosyası sunumu (/media/...) — giriş zorunlu."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.views.decorators.http import require_GET

from common.media_access import user_can_access_media_path


@require_GET
@login_required
def serve_media_file(request, path: str):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if not media_root.is_dir():
        raise Http404('Medya dizini yok.')

    relative = path.lstrip('/')
    if not user_can_access_media_path(request.user, relative):
        return HttpResponseForbidden('Bu dosyaya erişim yetkiniz yok.')

    target = (media_root / relative).resolve()

    try:
        target.relative_to(media_root)
    except ValueError:
        raise Http404('Geçersiz yol.') from None

    if not target.is_file():
        raise Http404('Dosya bulunamadı.')

    content_type, _ = mimetypes.guess_type(target.name)
    response = FileResponse(
        target.open('rb'),
        content_type=content_type or 'application/octet-stream',
    )
    response['Cache-Control'] = 'private, max-age=3600'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
