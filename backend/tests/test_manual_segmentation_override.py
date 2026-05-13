import unittest
from unittest import mock

from backend import main


class ManualSegmentationOverrideTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_override_replaces_visible_reference_metadata(self):
        source_sop = {
            "id": "sop-1",
            "steps": [
                {
                    "stepNo": 1,
                    "description": "拆机检查",
                    "demoVideo": {"mediaId": "media-1", "name": "demo.mp4"},
                    "referenceSummary": "旧摘要",
                    "roiHint": "旧 ROI",
                    "substeps": [{"title": "旧关键帧", "timestampSec": 1.0}],
                    "referenceFrames": ["old-frame"],
                }
            ],
        }
        bundle = {
            "referenceFrames": ["new-frame-a", "new-frame-b"],
            "analysisFrames": [],
            "referenceSummary": "管理员手动切帧：步骤 1 / 拆机检查",
            "referenceFeatures": {"sampleTimestamps": [0.0, 2.0]},
            "substeps": [
                {"title": "手动关键帧 1", "timestampSec": 0.0},
                {"title": "手动关键帧 2", "timestampSec": 2.0},
            ],
            "roiHint": "",
        }
        captured = {}

        def fake_update_sop(_sop_id, updater):
            updated = updater(source_sop)
            captured["step"] = updated["steps"][0]
            return updated

        with mock.patch.object(main, "get_sop", return_value=source_sop), mock.patch.object(
            main, "get_media", return_value={"path": "demo.mp4"}
        ), mock.patch.object(
            main, "rebuild_reference_bundle_from_video", return_value=bundle
        ), mock.patch.object(
            main, "update_sop", side_effect=fake_update_sop
        ), mock.patch.object(
            main, "serialize_sop_detail", side_effect=lambda item: item
        ):
            response = await main.update_step_segmentation_override(
                "sop-1", 1, main.ManualSegmentationRequest(timestamps=[0.0, 2.0]), {"role": "admin"}
            )

        self.assertTrue(response["success"])
        self.assertEqual(captured["step"]["referenceSummary"], bundle["referenceSummary"])
        self.assertEqual(captured["step"]["referenceFrames"], bundle["referenceFrames"])
        self.assertEqual(captured["step"]["substeps"], bundle["substeps"])


if __name__ == "__main__":
    unittest.main()
