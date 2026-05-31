"""CSV içe aktarma sihirbazı — önizleme, sütun eşleştirme, içe aktarma."""

from __future__ import annotations

import json
import secrets
import time

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from common.csv_import_registry import import_type_config, list_import_types_for_user, user_can_import_type
from common.csv_import_runner import prepare_import_rows, run_import
from common.csv_io import read_csv_text
from users.mixins import PermissionRequiredMixin

SESSION_PREFIX = 'csv_imp_'
SESSION_TTL = 3600
MAX_ROWS = 2000


def _session_key(token: str) -> str:
    return f'{SESSION_PREFIX}{token}'


def _store_session(request, *, import_type: str, headers: list[str], rows: list[dict]) -> str:
    token = secrets.token_urlsafe(16)
    request.session[_session_key(token)] = {
        'type': import_type,
        'headers': headers,
        'rows': rows[:MAX_ROWS],
        'expires': time.time() + SESSION_TTL,
    }
    request.session.modified = True
    return token


def _load_session(request, token: str) -> dict | None:
    if not token:
        return None
    payload = request.session.get(_session_key(token))
    if not payload:
        return None
    if payload.get('expires', 0) < time.time():
        del request.session[_session_key(token)]
        return None
    return payload


def _clear_session(request, token: str) -> None:
    key = _session_key(token)
    if key in request.session:
        del request.session[key]


def _safe_next_url(request, fallback: str) -> str:
    nxt = (request.GET.get('next') or request.POST.get('next') or '').strip()
    if nxt.startswith('/') and not nxt.startswith('//'):
        return nxt
    return fallback


def _result_message(import_type: str, result: dict) -> str:
    created = result.get('created', 0)
    updated = result.get('updated', 0)
    skipped = result.get('skipped', 0)
    cfg = import_type_config(import_type) or {}
    label = cfg.get('label', import_type)
    parts = [f'{label}: {created} kayıt eklendi.']
    if updated:
        parts.append(f'{updated} güncellendi.')
    if skipped:
        parts.append(f'{skipped} satır atlandı.')
    return ' '.join(parts)


def _fields_payload(import_type: str) -> list[dict]:
    cfg = import_type_config(import_type)
    if not cfg:
        return []
    return [
        {'key': f.key, 'label': f.label, 'required': f.required}
        for f in cfg['fields']
    ]


class CsvImportWizardView(PermissionRequiredMixin, TemplateView):
    template_name = 'common/csv_import_wizard.html'
    permission_any = True
    permission_required = (
        'access.accounting', 'contact.payroll', 'accounting.finance',
        'sales.manage', 'sales.export', 'contact.customers', 'contact.firms',
    )

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        import_type = (self.request.GET.get('type') or self.request.POST.get('type') or '').strip()
        if import_type:
            return user_can_import_type(user, import_type)
        return bool(list_import_types_for_user(user))

    def dispatch(self, request, *args, **kwargs):
        self.import_type = (request.GET.get('type') or request.POST.get('type') or '').strip()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['import_type'] = self.import_type
        ctx['import_types'] = list_import_types_for_user(self.request.user)
        ctx['next_url'] = _safe_next_url(
            self.request,
            reverse(import_type_config(self.import_type)['redirect_name']) if self.import_type else reverse('accounting_data_exchange'),
        )
        if self.import_type:
            cfg = import_type_config(self.import_type)
            ctx['import_label'] = cfg['label']
            ctx['import_hint'] = cfg.get('sample_hint', '')
            ctx['import_fields'] = _fields_payload(self.import_type)
            token = self.request.GET.get('token', '')
            payload = _load_session(self.request, token)
            if payload and payload.get('type') == self.import_type:
                ctx['preview_token'] = token
                ctx['csv_headers'] = payload['headers']
                ctx['preview_rows'] = payload['rows'][:8]
                ctx['preview_matrix'] = [
                    [row.get(h, '') for h in payload['headers']]
                    for row in payload['rows'][:8]
                ]
                ctx['row_count'] = len(payload['rows'])
                _, auto_mapping = prepare_import_rows(
                    payload['rows'][:1],
                    payload['headers'],
                    self.import_type,
                )
                ctx['auto_mapping'] = auto_mapping
                sample_row = payload['rows'][0] if payload['rows'] else {}
                ctx['mapping_rows'] = []
                for field in cfg['fields']:
                    selected = auto_mapping.get(field.key, '')
                    ctx['mapping_rows'].append({
                        'key': field.key,
                        'label': field.label,
                        'required': field.required,
                        'selected_header': selected,
                        'sample': (sample_row.get(selected) or '—')[:60] if selected else '—',
                    })
        return ctx

    def post(self, request, *args, **kwargs):
        import_type = (request.POST.get('type') or '').strip()
        if not user_can_import_type(request.user, import_type):
            messages.error(request, 'Bu CSV türü için yetkiniz yok.')
            return redirect('accounting_data_exchange')

        step = request.POST.get('step', 'upload')
        next_url = _safe_next_url(request, reverse(import_type_config(import_type)['redirect_name']))

        if step == 'upload':
            uploaded = request.FILES.get('file')
            if not uploaded:
                messages.error(request, 'CSV dosyası seçin.')
                return redirect(f'{reverse("csv_import_wizard")}?type={import_type}&next={next_url}')
            raw = uploaded.read()
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]
            text = raw.decode('utf-8-sig', errors='replace')
            headers, rows = read_csv_text(text)
            if not rows:
                messages.error(request, 'CSV dosyasında veri satırı bulunamadı.')
                return redirect(f'{reverse("csv_import_wizard")}?type={import_type}&next={next_url}')
            token = _store_session(request, import_type=import_type, headers=headers, rows=rows)
            return redirect(f'{reverse("csv_import_wizard")}?type={import_type}&token={token}&next={next_url}')

        if step == 'import':
            token = request.POST.get('token', '')
            payload = _load_session(request, token)
            if not payload or payload.get('type') != import_type:
                messages.error(request, 'Önizleme oturumu süresi doldu. Dosyayı tekrar yükleyin.')
                return redirect(f'{reverse("csv_import_wizard")}?type={import_type}&next={next_url}')

            mapping = {}
            for key in request.POST:
                if key.startswith('map_'):
                    mapping[key[4:]] = request.POST.get(key) or ''

            try:
                result = run_import(
                    import_type,
                    payload['rows'],
                    user=request.user,
                    raw_rows=payload['rows'],
                    mapping=mapping,
                    headers=payload['headers'],
                )
                _clear_session(request, token)
                messages.success(request, _result_message(import_type, result))
                if result.get('skipped'):
                    messages.warning(request, f'{result["skipped"]} satır eşleşmedi veya atlandı.')
            except Exception as exc:
                messages.error(request, f'İçe aktarma başarısız: {exc}')
            return redirect(next_url)

        return redirect(f'{reverse("csv_import_wizard")}?type={import_type}&next={next_url}')


@require_http_methods(['POST'])
def csv_import_preview_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Oturum gerekli.'}, status=401)

    import_type = (request.POST.get('type') or '').strip()
    if not user_can_import_type(request.user, import_type):
        return JsonResponse({'ok': False, 'error': 'Yetkiniz yok.'}, status=403)

    uploaded = request.FILES.get('file')
    if not uploaded:
        return JsonResponse({'ok': False, 'error': 'CSV dosyası seçin.'}, status=400)

    raw = uploaded.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    text = raw.decode('utf-8-sig', errors='replace')
    headers, rows = read_csv_text(text)
    if not rows:
        return JsonResponse({'ok': False, 'error': 'Veri satırı yok.'}, status=400)

    token = _store_session(request, import_type=import_type, headers=headers, rows=rows)
    _, auto_mapping = prepare_import_rows(rows[:1], headers, import_type)
    return JsonResponse({
        'ok': True,
        'token': token,
        'headers': headers,
        'fields': _fields_payload(import_type),
        'auto_mapping': auto_mapping,
        'preview_rows': rows[:5],
        'row_count': len(rows),
    })


@require_http_methods(['POST'])
def csv_import_execute_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Oturum gerekli.'}, status=401)

    import_type = (request.POST.get('type') or '').strip()
    if not user_can_import_type(request.user, import_type):
        return JsonResponse({'ok': False, 'error': 'Yetkiniz yok.'}, status=403)

    token = request.POST.get('token', '')
    payload = _load_session(request, token)
    if not payload or payload.get('type') != import_type:
        return JsonResponse({'ok': False, 'error': 'Oturum süresi doldu.'}, status=400)

    mapping_raw = request.POST.get('mapping', '{}')
    try:
        mapping = json.loads(mapping_raw)
    except json.JSONDecodeError:
        mapping = {}

    try:
        result = run_import(
            import_type,
            payload['rows'],
            user=request.user,
            raw_rows=payload['rows'],
            mapping=mapping,
            headers=payload['headers'],
        )
        _clear_session(request, token)
        return JsonResponse({'ok': True, 'result': result, 'message': _result_message(import_type, result)})
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
