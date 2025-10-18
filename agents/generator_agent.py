import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class GeneratorAgent:
    """
    GeneratorAgent
    ---------------
    Converts a structured story plan into:
    1. Valid Manim Python code
    2. Narration text for TTS
    3. A self-descriptive filename for the generated files
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.6):
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "generator_prompt.txt"
        )
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_text = f.read()

        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_template(self.prompt_text)

    def generate(self, story_plan: dict) -> dict:
        plan_json = json.dumps(story_plan, indent=2)
        chain = self.prompt | self.llm
        response = chain.invoke({"story_plan": plan_json}).content

        concept = story_plan.get("concept", "concept_visualization").lower()
        safe_name = re.sub(r"[^a-z0-9_]+", "_", concept).strip("_") or "visualization"

        scene_narrations = []
        for scene in story_plan.get("scenes", []):
            narration = scene.get("narration", "").strip()
            if narration:
                scene_narrations.append(
                    {"title": scene.get("title", "Scene"), "narration": narration}
                )

        return {
            "file_name": safe_name,
            "code": response,
            "scene_narrations": scene_narrations,
        }

