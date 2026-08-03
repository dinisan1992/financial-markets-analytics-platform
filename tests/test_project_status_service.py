from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from services import project_status_service


class ProjectStatusServiceTests(unittest.TestCase):
    def test_status_file_changes_are_visible_without_streamlit_cache(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            status_file = root / "PROJECT_STATUS.md"
            status_file.write_text("version one", encoding="utf-8")
            with patch.object(project_status_service, "PROJECT_ROOT", root):
                self.assertEqual("version one", project_status_service.load_project_status())
                status_file.write_text("version two", encoding="utf-8")
                self.assertEqual("version two", project_status_service.load_project_status())


if __name__ == "__main__":
    unittest.main()
