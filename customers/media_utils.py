from __future__ import annotations

from django.core.exceptions import ValidationError

from common.media_files import is_allowed_upload

from .models import Customer, CustomerMedia

_MAX_UPLOAD_BYTES = 52 * 1024 * 1024


def _validate_upload_file(uploaded) -> None:
    if uploaded.size > _MAX_UPLOAD_BYTES:
        raise ValidationError(f'Dosya çok büyük (en fazla {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB).')
    if not is_allowed_upload(uploaded.name):
        raise ValidationError('Bu dosya türü yüklenemez.')


def ingest_customer_media_uploads(
    request,
    *,
    customer: Customer,
    service=None,
    scope: str = CustomerMedia.SCOPE_CUSTOMER,
    field_names: tuple[str, ...] = ('customer_media', 'media_files', 'images'),
) -> list[CustomerMedia]:
    """Form POST veya API ile gelen dosyaları CustomerMedia olarak kaydeder."""
    created: list[CustomerMedia] = []
    seen_names: set[str] = set()

    for field in field_names:
        for uploaded in request.FILES.getlist(field):
            _validate_upload_file(uploaded)
            key = f'{field}:{uploaded.name}:{uploaded.size}'
            if key in seen_names:
                continue
            seen_names.add(key)
            media = CustomerMedia.objects.create(
                customer=customer,
                service=service if scope == CustomerMedia.SCOPE_SERVICE else None,
                scope=scope,
                file=uploaded,
                title=uploaded.name,
                uploaded_by=request.user if request.user.is_authenticated else None,
            )
            created.append(media)
    return created
