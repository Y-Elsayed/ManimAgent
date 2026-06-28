import unittest

from nodes.syntax_guard_node import SyntaxGuardNode


class SyntaxGuardNodeTests(unittest.TestCase):
    def test_sanitize_injects_audio_only_into_scene_classes(self):
        code = """
class Helper:
    pass

class Demo(Scene):
    def construct(self):
        self.play(Write(Text("Hi")))
"""
        result = SyntaxGuardNode(enable_audio_mixin=True, replace_play_calls=True).sanitize(code)
        self.assertIn("class Demo(AudioMixin, Scene):", result["code"])
        self.assertIn("class Helper:", result["code"])
        self.assertIn("self.play_with_audio", result["code"])
        self.assertTrue(result["diagnostics"]["syntax_valid"])


if __name__ == "__main__":
    unittest.main()
