import os
import tempfile
import unittest

from services.storage_service import StorageService


class StorageServicePathTest(unittest.TestCase):
    def test_storage_path_is_absolute_and_not_plain_relative_filename(self):
        service = StorageService("subscriptions.json")
        path = service.get_storage_path()

        self.assertTrue(os.path.isabs(path))
        self.assertNotEqual(path, "subscriptions.json")


if __name__ == "__main__":
    unittest.main()
