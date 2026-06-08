from django.core.management.base import BaseCommand

from chat.services import ensure_team_thread
from core_settings.models import BusinessBrand


class Command(BaseCommand):
    help = 'Marka başına genel sohbet odasını ve kullanıcı üyeliklerini oluşturur / günceller.'

    def handle(self, *args, **options):
        count = 0
        for brand in BusinessBrand.objects.filter(is_active=True).order_by('pk'):
            thread = ensure_team_thread(brand)
            count += 1
            self.stdout.write(self.style.SUCCESS(f'{brand.name}: thread #{thread.pk}'))
        self.stdout.write(self.style.SUCCESS(f'{count} marka sohbet odası hazır.'))
