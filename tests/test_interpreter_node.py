import unittest

from nodes.interpreter_node import InterpreterNode


class InterpreterNodeTests(unittest.TestCase):
    def test_detect_scene_names_with_ast(self):
        code = """
from manim import *

class Intro(Scene):
    def construct(self):
        pass

class Helper:
    pass

class WithAudio(AudioMixin, Scene):
    def construct(self):
        pass
"""
        self.assertEqual(InterpreterNode()._detect_scene_names(code), ["Intro", "WithAudio"])

    def test_validate_code_requires_scene(self):
        ok, error = InterpreterNode()._validate_code("class Helper:\n    pass\n")
        self.assertFalse(ok)
        self.assertIn("No Scene", error)


if __name__ == "__main__":
    unittest.main()
