from django.core.management.base import BaseCommand

from chat.services import ensure_team_thread


class Command(BaseCommand):
    help = 'Genel sohbet odasını ve kullanıcı üyeliklerini oluşturur / günceller.'

    def handle(self, *args, **options):
        thread = ensure_team_thread()
        self.stdout.write(self.style.SUCCESS(f'Genel sohbet hazır (thread #{thread.pk}).'))
