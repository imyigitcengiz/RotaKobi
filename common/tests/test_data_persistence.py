"""Kalıcı /data volume algılama."""

import unittest
from pathlib import Path
from unittest.mock import patch

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=[],
        SECRET_KEY='test',
    )
    django.setup()

from common.data_persistence import (  # noqa: E402
    data_dir_is_persistent,
    data_dir_looks_ephemeral,
)


def _resolved_data():
    return Path('/data')


class DataPersistenceMountTests(unittest.TestCase):
    def test_mount_point_is_persistent(self):
        with patch.object(Path, 'resolve', return_value=_resolved_data()):
            with patch('common.data_persistence._is_mount_point', return_value=True):
                self.assertTrue(data_dir_is_persistent(Path('/data')))
                self.assertFalse(data_dir_looks_ephemeral(Path('/data')))

    def test_overlay_directory_is_ephemeral(self):
        with patch.object(Path, 'resolve', return_value=_resolved_data()):
            with patch('common.data_persistence._is_mount_point', return_value=False):
                with patch('common.data_persistence._is_listed_in_mountinfo', return_value=False):
                    with patch('common.data_persistence._is_listed_in_mounts', return_value=False):
                        self.assertFalse(data_dir_is_persistent(Path('/data')))
                        self.assertTrue(data_dir_looks_ephemeral(Path('/data')))

    def test_mountinfo_listing_is_persistent(self):
        with patch.object(Path, 'resolve', return_value=_resolved_data()):
            with patch('common.data_persistence._is_mount_point', return_value=False):
                with patch('common.data_persistence._is_listed_in_mountinfo', return_value=True):
                    self.assertTrue(data_dir_is_persistent(Path('/data')))

    def test_mounts_listing_is_persistent(self):
        with patch.object(Path, 'resolve', return_value=_resolved_data()):
            with patch('common.data_persistence._is_mount_point', return_value=False):
                with patch('common.data_persistence._is_listed_in_mountinfo', return_value=False):
                    with patch('common.data_persistence._is_listed_in_mounts', return_value=True):
                        self.assertTrue(data_dir_is_persistent(Path('/data')))


if __name__ == '__main__':
    unittest.main()
