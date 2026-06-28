import ast
import os
import tempfile
import unittest

from pipeline.dsl_builder import SceneDSLBuilder
from pipeline.manim_compiler import ManimCompiler
from pipeline.schemas import SchemaValidationError, validate_scene_dsl
from pipeline.video_assembler import VideoAssembler
from pipeline.visual_critic import VisualCritic


SAMPLE_STORY_PLAN = {
    "concept": "Eigenvectors",
    "scenes": [
        {
            "title": "Special Directions",
            "narration": "Eigenvectors keep their direction during a linear transformation.",
            "visuals": ["A grid transforms while one vector stays on the same line."],
            "key_points": [r"A\vec{v}=\lambda\vec{v}"],
        }
    ],
}


class SceneDSLPipelineTests(unittest.TestCase):
    def test_builder_creates_valid_dsl(self):
        dsl = SceneDSLBuilder().build(SAMPLE_STORY_PLAN)
        data = dsl.to_dict()
        validate_scene_dsl(data)
        self.assertEqual(data["scenes"][0]["scene_type"], "linear_transform_2d")

    def test_validate_scene_dsl_rejects_missing_scenes(self):
        with self.assertRaises(SchemaValidationError):
            validate_scene_dsl({"concept": "Empty", "scenes": []})

    def test_compiler_outputs_valid_python(self):
        dsl = SceneDSLBuilder().build(SAMPLE_STORY_PLAN)
        result = ManimCompiler(use_tts=False).compile(dsl)
        ast.parse(result["code"])
        self.assertIn("class SpecialDirectionsScene(Scene):", result["code"])
        self.assertEqual(result["metadata"]["generator"], "scene_dsl_compiler")

    def test_compiler_supports_manim_voiceover_mode(self):
        dsl = SceneDSLBuilder().build(SAMPLE_STORY_PLAN)
        result = ManimCompiler(use_tts=True, voiceover_mode="manim_voiceover").compile(dsl)
        ast.parse(result["code"])
        self.assertIn("VoiceoverScene", result["code"])
        self.assertIn("with self.voiceover", result["code"])

    def test_visual_critic_writes_report(self):
        dsl = SceneDSLBuilder().build(SAMPLE_STORY_PLAN).to_dict()
        with tempfile.TemporaryDirectory() as tmp:
            report = VisualCritic().evaluate_render_result(
                {"rendered": ["SpecialDirectionsScene"]},
                dsl,
                tmp,
            )
            self.assertTrue(os.path.exists(os.path.join(tmp, "quality_report.json")))
            self.assertTrue(report["passed"])

    def test_video_assembler_writes_manifest_without_clips(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = VideoAssembler().assemble("Demo", [], tmp, "demo")
            self.assertTrue(os.path.exists(result["manifest"]))
            self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
