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

    # -------------------------------------------------
    # Sanitize broken Manim patterns before saving
    # -------------------------------------------------
    def _sanitize_manim_code(self, code: str) -> str:
        """
        Fixes invalid Manim code patterns, such as referencing
        variables like 'key_points[0]' before definition inside VGroup(),
        or using self.play(Write(key_points[0]), Write(key_points[1])).
        """

        # Fix VGroup self-references
        pattern = r"(\w+)\s*=\s*VGroup\((.*?)\)"
        matches = re.finditer(pattern, code, re.DOTALL)
        for match in matches:
            var_name = match.group(1)
            body = match.group(2)

            if f"{var_name}[" in body:
                text_objects = re.findall(r"(Text\(.*?\)|MathTex\(.*?\))", body)
                if text_objects:
                    new_lines = []
                    sub_vars = []
                    for idx, text_obj in enumerate(text_objects):
                        sub = f"{var_name}_{idx+1}"
                        prev = f"{var_name}_{idx}" if idx > 0 else None
                        if prev:
                            new_lines.append(f"{sub} = {text_obj}.scale(0.5).next_to({prev}, DOWN)")
                        else:
                            new_lines.append(f"{sub} = {text_obj}.scale(0.5)")
                        sub_vars.append(sub)
                    new_lines.append(f"{var_name} = VGroup({', '.join(sub_vars)})")
                    new_lines.append(f"self.play(" + ", ".join([f'Write({s})' for s in sub_vars]) + ")")
                    code = code.replace(match.group(0), "\n    ".join(new_lines))

        # Fix Write(key_points[0]) style play calls
        code = re.sub(
            r"self\.play\(Write\((\w+)\[[0-9]+\]\)(?:,\s*Write\(\1\[[0-9]+\]\))*\)",
            lambda m: f"self.play(Write({m.group(1)}))",
            code
        )

        return code

    # -------------------------------------------------
    # Generate full output (code + narrations + file name)
    # -------------------------------------------------
    def generate(self, story_plan: dict) -> dict:
        plan_json = json.dumps(story_plan, indent=2)
        chain = self.prompt | self.llm
        response = chain.invoke({"story_plan": plan_json}).content

        # Sanitize generated code
        cleaned_code = self._sanitize_manim_code(response)

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
            "code": cleaned_code,
            "scene_narrations": scene_narrations,
        }
