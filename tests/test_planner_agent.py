import unittest

from agents.planner_agent import PlannerAgent


class PlannerAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = PlannerAgent.__new__(PlannerAgent)

    def test_parse_response_strips_json_fence(self):
        response = """```json
{"concept":"Gravity","scenes":[{"title":"Hook","narration":"Objects fall.","visuals":["Dot moving downward"],"key_points":["Gravity accelerates mass"]}]}
```"""
        plan = self.agent._parse_response(response)
        self.assertEqual(plan["concept"], "Gravity")

    def test_validate_plan_rejects_missing_scenes(self):
        with self.assertRaises(ValueError):
            self.agent._validate_plan({"concept": "Gravity", "scenes": []})


if __name__ == "__main__":
    unittest.main()
