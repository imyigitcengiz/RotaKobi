import os

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from common.module_toggle_views import module_toggle_api
from analytics.views import (
    CapabilitiesHubView,
    HomeView,
    ModuleHubView,
    PublicLandingView,
)
from common.media_views import serve_media_file
from common.views import IntroducerKnowledgeBaseView, healthz
from common.shell_api import (
    notification_mark_read_api,
    notifications_api,
    notifications_mark_all_read_api,
    quick_search_api,
)

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('api/hizli-arama/', quick_search_api, name='quick_search_api'),
    path('api/bildirimler/', notifications_api, name='notifications_api'),
    path('api/bildirimler/tumu-okundu/', notifications_mark_all_read_api, name='notifications_mark_all_read_api'),
    path('api/bildirimler/<int:pk>/okundu/', notification_mark_read_api, name='notification_mark_read_api'),
    path('admin/', admin.site.urls),
    path('', PublicLandingView.as_view(), name='landing'),
    path('bilgi-bankasi/', IntroducerKnowledgeBaseView.as_view(), name='introducer_knowledge_base'),
    path('panel/', HomeView.as_view(), name='home'),
    path('panel/moduller/toggle/', module_toggle_api, name='module_toggle_api'),
    path('panel/moduller/', ModuleHubView.as_view(), name='module_hub'),
    path('panel/yetenekler/', CapabilitiesHubView.as_view(), name='capabilities_hub'),
    path('', include('users.urls')),
    path('services-dashboard/', include('config.services_dashboard_urls')),
    path('tools/', include('config.tools_urls')),
    path('sales-lead/', include('config.sales_lead_urls')),
    path('contact/', include('config.contact_urls')),
    path('iletisim/', include('config.outreach_urls')),
    path('muhasebe/', include('config.accounting_urls')),
    path('crm/', include('config.crm_urls')),
    path('ortak/', include('config.ortak_urls')),
    path('chat/', include('chat.urls')),
    path('ayarlar/', include('config.site_settings_urls')),
]

_serve_media = os.environ.get('DJANGO_SERVE_MEDIA', '1').lower() not in ('0', 'false', 'no')
if _serve_media:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media_file, name='serve_media'),
    ]
elif settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
