from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

from core_settings.backup import (
    FACTORY_RESET_CONFIRM_PHRASE,
    export_backup_response,
    export_brand_backup_response,
    export_sqlite_response,
    factory_reset_database,
    import_backup_file,
    import_brand_backup_file,
    import_sqlite_file,
)
from core_settings.models import BusinessBrand
from users.impersonation import get_real_user
from users.models import PlatformAuditLog
from users.platform_audit import log_platform_audit


def _finish_database_restore_response(request, *, redirect_name: str, ok: bool, msg: str):
    """
    SQLite / tam JSON yedeği oturum tablosunu da değiştirir.
    Yanıtta eski session kaydını güncellemeye çalışmak SessionInterrupted üretir.
    """
    if ok:
        logout(request)
        messages.success(
            request,
            f'{msg} Veritabanı değişti — lütfen tekrar giriş yapın.',
        )
        return redirect('login')
    messages.error(request, msg)
    return redirect(redirect_name)


def handle_system_backup_post(request, *, redirect_name: str):
    if 'export_brand_backup' in request.POST:
        brand_id = request.POST.get('brand_id', '').strip()
        if not brand_id.isdigit():
            messages.error(request, 'Geçerli bir marka seçin.')
            return redirect(redirect_name)
        try:
            brand = BusinessBrand.objects.get(pk=int(brand_id))
            log_platform_audit(
                request,
                action=PlatformAuditLog.ACTION_BRAND_BACKUP_EXPORT,
                brand=brand,
                detail=brand.name,
            )
            return export_brand_backup_response(int(brand_id))
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(redirect_name)
        except Exception as exc:
            messages.error(request, f'Marka yedeği alınamadı: {exc}')
            return redirect(redirect_name)

    if 'import_brand_backup' in request.POST:
        brand_id = request.POST.get('brand_id', '').strip()
        if not brand_id.isdigit():
            messages.error(request, 'Geçerli bir hedef marka seçin.')
            return redirect(redirect_name)
        replace = request.POST.get('replace_brand_data') == 'on'
        ok, msg = import_brand_backup_file(
            request.FILES.get('brand_backup_file'),
            int(brand_id),
            replace_existing=replace,
        )
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect(redirect_name)

    if 'export_backup' in request.POST:
        try:
            log_platform_audit(request, action=PlatformAuditLog.ACTION_BACKUP_EXPORT)
            return export_backup_response()
        except Exception as exc:
            messages.error(request, f'Yedekleme sırasında hata oluştu: {exc}')
            return redirect(redirect_name)

    if 'import_backup' in request.POST:
        ok, msg = import_backup_file(request.FILES.get('backup_file'))
        return _finish_database_restore_response(
            request, redirect_name=redirect_name, ok=ok, msg=msg,
        )

    if 'export_sqlite' in request.POST:
        try:
            log_platform_audit(request, action=PlatformAuditLog.ACTION_BACKUP_EXPORT, detail='sqlite')
            return export_sqlite_response()
        except Exception as exc:
            messages.error(request, f'SQLite indirme hatası: {exc}')
            return redirect(redirect_name)

    if 'import_sqlite' in request.POST:
        ok, msg = import_sqlite_file(request.FILES.get('sqlite_file'))
        return _finish_database_restore_response(
            request, redirect_name=redirect_name, ok=ok, msg=msg,
        )

    if 'factory_reset_database' in request.POST:
        return _handle_factory_reset_post(request, redirect_name=redirect_name)

    return redirect(redirect_name)


def _handle_factory_reset_post(request, *, redirect_name: str):
    confirm = (request.POST.get('confirm_phrase') or '').strip().upper()
    if confirm != FACTORY_RESET_CONFIRM_PHRASE:
        messages.error(request, f'Onay metni hatalı. Tam olarak {FACTORY_RESET_CONFIRM_PHRASE} yazın.')
        return redirect(redirect_name)

    if request.POST.get('acknowledge_data_loss') != 'on':
        messages.error(request, 'Devam etmek için veri kaybı onay kutusunu işaretleyin.')
        return redirect(redirect_name)

    password = request.POST.get('password') or ''
    user = get_real_user(request)
    if not user.check_password(password):
        messages.error(request, 'Mevcut şifreniz doğrulanamadı.')
        return redirect(redirect_name)

    try:
        ok, msg = factory_reset_database(backup_before=True)
    except Exception as exc:
        messages.error(request, f'Veritabanı sıfırlanırken hata oluştu: {exc}')
        return redirect(redirect_name)

    if ok:
        logout(request)
        messages.success(request, msg)
        return redirect('login')

    messages.error(request, msg)
    return redirect(redirect_name)
