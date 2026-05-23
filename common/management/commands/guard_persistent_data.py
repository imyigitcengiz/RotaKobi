"""Deploy öncesi/sonrası SQLite ve /data volume güvenliği."""

from django.core.management.base import BaseCommand, CommandError

from common.data_persistence import (
    DataPersistenceError,
    auto_backup_sqlite,
    check_after_migrate,
    check_before_migrate,
    data_dir_looks_ephemeral,
    data_root,
    db_path,
    is_containerized_production,
    require_persistent_volume,
)


class Command(BaseCommand):
    help = 'Kalıcı /data volume ve db.sqlite3 bütünlüğünü kontrol eder; otomatik yedek alır.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phase',
            choices=('pre', 'post', 'backup', 'status'),
            default='pre',
            help='pre: migrate öncesi kontrol+yedek, post: marker güncelle, backup: yalnız yedek',
        )

    def handle(self, *args, **options):
        phase = options['phase']
        root = data_root()
        db = db_path()

        if phase == 'status':
            self._print_status(root, db)
            return

        if phase == 'backup':
            dest = auto_backup_sqlite(root)
            if dest:
                self.stdout.write(self.style.SUCCESS(f'Yedek alındı: {dest}'))
            else:
                self.stdout.write('Yedeklenecek veritabanı yok.')
            return

        if phase == 'pre':
            try:
                check_before_migrate()
            except DataPersistenceError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(self.style.SUCCESS('Kalıcı veri kontrolü OK (migrate öncesi).'))
            return

        if phase == 'post':
            payload = check_after_migrate()
            if payload:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Veri işareti güncellendi: {payload.get("db_bytes")} bayt, '
                        f'{payload.get("auth_user_count")} kullanıcı.'
                    )
                )
            return

    def _print_status(self, root, db):
        self.stdout.write(f'DATA root: {root}')
        self.stdout.write(f'DB path:   {db}')
        self.stdout.write(f'DB exists: {db.is_file()}')
        if db.is_file():
            self.stdout.write(f'DB size:   {db.stat().st_size} bayt')
        self.stdout.write(f'Container: {is_containerized_production()}')
        self.stdout.write(f'Require volume: {require_persistent_volume()}')
        self.stdout.write(f'Ephemeral /data: {data_dir_looks_ephemeral(root)}')
