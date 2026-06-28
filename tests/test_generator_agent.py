import unittest

from agents.generator_agent import GeneratorAgent


class GeneratorAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = GeneratorAgent.__new__(GeneratorAgent)

    def test_extract_code_strips_python_fence(self):
        code = self.agent._extract_code("```python\nprint('ok')\n```")
        self.assertEqual(code, "print('ok')")

    def test_validate_code_requires_scene_construct(self):
        valid = "from manim import *\nclass Demo(Scene):\n    def construct(self):\n        pass\n"
        self.agent._validate_code(valid)
        with self.assertRaises(ValueError):
            self.agent._validate_code("from manim import *\nclass Demo(Scene):\n    pass\n")


if __name__ == "__main__":
    unittest.main()
