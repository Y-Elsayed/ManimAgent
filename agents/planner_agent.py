import json
import os
import re


class PlannerAgent:
    """
    PlannerAgent
    -------------
    Takes a concept and produces a structured visual explanation plan
    using the modern LangChain v1.x interface.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate

        self.llm = ChatOpenAI(model=model, temperature=temperature)

        # Load prompt from file
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "planner_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read().strip()

        self.prompt = ChatPromptTemplate.from_template(
            self.prompt_template
        )

    def plan(self, concept: str):
        """Generate a structured story plan for the given concept."""
        chain = self.prompt | self.llm
        last_error = None

        for attempt in range(2):
            response = chain.invoke({"concept": concept}).content
            try:
                plan = self._parse_response(response)
                self._validate_plan(plan)
                return plan
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                print(f"[PlannerAgent] Invalid JSON/storyboard response on attempt {attempt + 1}: {e}")

        raise ValueError(f"PlannerAgent failed to produce a valid storyboard: {last_error}")

    def _parse_response(self, response: str):
        text = response.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start:end + 1]
        return json.loads(text)

    def _validate_plan(self, plan):
        if not isinstance(plan, dict):
            raise ValueError("Plan must be a JSON object")
        if not isinstance(plan.get("concept"), str) or not plan["concept"].strip():
            raise ValueError("Plan missing non-empty concept")
        scenes = plan.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            raise ValueError("Plan must include at least one scene")

        required_scene_fields = ("title", "narration", "visuals", "key_points")
        for i, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise ValueError(f"Scene {i} must be an object")
            for field in required_scene_fields:
                if field not in scene:
                    raise ValueError(f"Scene {i} missing {field}")
            if not isinstance(scene["title"], str) or not scene["title"].strip():
                raise ValueError(f"Scene {i} missing title")
            if not isinstance(scene["narration"], str):
                raise ValueError(f"Scene {i} narration must be a string")
            if not isinstance(scene["visuals"], list):
                raise ValueError(f"Scene {i} visuals must be a list")
            if not isinstance(scene["key_points"], list):
                raise ValueError(f"Scene {i} key_points must be a list")
