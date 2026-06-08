"""ROUTE_PERMISSIONS ile module_catalog route_prefixes uyumu."""

from django.test import SimpleTestCase

from common.module_catalog import MODULES
from users.permission_catalog import ROUTE_PERMISSIONS


def _route_prefix_covered(module_prefix: str, route_permissions) -> bool:
    for route_path, _ in route_permissions:
        if route_path == module_prefix:
            return True
        if route_path.startswith(module_prefix) or module_prefix.startswith(route_path):
            return True
    return False


class RouteCatalogSyncTests(SimpleTestCase):
    def test_module_route_prefixes_have_permission_entries(self):
        missing: list[str] = []
        for mod in MODULES:
            for prefix in mod.get('route_prefixes', ()):
                if not prefix.startswith('/'):
                    continue
                if _route_prefix_covered(prefix, ROUTE_PERMISSIONS):
                    continue
                missing.append(f'{mod["slug"]}: {prefix}')
        self.assertEqual(missing, [], f'Eksik ROUTE_PERMISSIONS önekleri: {missing}')
