import importlib
import unittest


class ModuleExportTests(unittest.TestCase):
    def test_backend_main_imports_as_package(self):
        module = importlib.import_module("backend.main")

        self.assertTrue(callable(module.run_sop_evaluation))

    def test_video_exposes_build_reference_bundle(self):
        module = importlib.import_module("backend.video")

        self.assertTrue(callable(module.build_reference_bundle))


if __name__ == "__main__":
    unittest.main()
