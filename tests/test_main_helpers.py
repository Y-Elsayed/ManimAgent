import os
import tempfile
import unittest

from main import ensure_dirs, safe_project_name


class MainHelperTests(unittest.TestCase):
    def test_safe_project_name_creates_unique_project_paths(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                first = safe_project_name("Eigen Values!")
                os.makedirs(first)
                second = safe_project_name("Eigen Values!")
                self.assertTrue(first.endswith(os.path.join("projects", "eigen_values")))
                self.assertTrue(second.endswith(os.path.join("projects", "eigen_values_1")))
            finally:
                os.chdir(cwd)

    def test_ensure_dirs_creates_expected_subfolders(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ensure_dirs(tmp)
            for path in paths:
                self.assertTrue(os.path.isdir(path))


if __name__ == "__main__":
    unittest.main()
