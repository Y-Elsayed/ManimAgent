import os
import json
import re
import ast
from typing import Dict, Any, List


class GeneratorAgent:
    """
    Generates Manim Python code with real geometric visuals using LLM.
    Creates proper Manim primitives: Circle, Arrow, NumberPlane, Graph, etc.
    """

    def __init__(self, model: str = "gpt-5", temperature: float = 0.3, 
                 use_tts: bool = True, tts_voice: str = "onyx"):
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate

        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "generator_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_text = f.read().strip()

        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_template(self.prompt_text)
        self.use_tts = use_tts
        self.tts_voice = tts_voice

    @staticmethod
    def _slugify(name: str) -> str:
        name = (name or "visualization").lower()
        name = re.sub(r"[^a-z0-9_]+", "_", name).strip("_")
        return name[:40] or "visualization"

    @staticmethod
    def _extract_code(text: str) -> str:
        """Extract Python code from LLM response."""
        # Remove markdown fences
        fence_pattern = r"```(?:python)?\s*([\s\S]*?)```"
        match = re.search(fence_pattern, text)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _build_prompt_context(self, story_plan: Dict[str, Any]) -> str:
        """Build enhanced prompt with TTS and visual instructions."""
        enhanced_plan = story_plan.copy()
        enhanced_plan["_instructions"] = {
            "use_tts": self.use_tts,
            "voice": self.tts_voice,
            "layout_rules": "Ensure all visuals fit within x∈[-6,6], y∈[-3.5,3.5]"
        }
        
        return json.dumps(enhanced_plan, ensure_ascii=False, indent=2)

    def _sanitize_code(self, code: str) -> str:
        """Clean up generated code."""
        # Remove any markdown remnants
        code = re.sub(r"^```python\s*", "", code)
        code = re.sub(r"```\s*$", "", code)
        
        # Ensure proper imports
        if "from manim import" not in code:
            header = "from manim import *\nimport numpy as np\n"
            if self.use_tts:
                header += "from audio_mixin import AudioMixin\n"
            code = header + "\n" + code
        
        # Fix common issues
        code = re.sub(r"\)\s*,\s*buff\s*=", ", buff=", code)  # Fix buff placement
        
        return code.strip()

    def _validate_code(self, code: str) -> None:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Generated code is not valid Python: {e}") from e

        scene_classes = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            base_names = [self._ast_name(base) for base in node.bases]
            if "Scene" in base_names:
                has_construct = any(
                    isinstance(item, ast.FunctionDef) and item.name == "construct"
                    for item in node.body
                )
                if has_construct:
                    scene_classes.append(node.name)

        if not scene_classes:
            raise ValueError("Generated code has no Scene class with construct()")

    def _ast_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def generate(self, story_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Manim code with real geometric visuals using LLM."""
        
        # Prepare enhanced prompt
        plan_str = self._build_prompt_context(story_plan)
        
        # Add visual enhancement instructions
        enhanced_prompt = f"""Generate Manim code for the following storyboard.

CRITICAL REQUIREMENTS:
1. Use REAL Manim primitives (not just Text):
   - NumberPlane() for grids/coordinate systems
   - Arrow(start, end, buff=0) for vectors/directions
   - Circle(radius=1) for circular concepts
   - Dot(point) for points/locations
   - Line(start, end) for connections
   - Axes(x_range=[-5,5], y_range=[-5,5]) for graphs
   - VGroup() to group related objects
   - MathTex() for equations
   - Always add .set_color() to make visuals distinct

2. TTS Integration:
   - use_tts: {self.use_tts}
   - voice: {self.tts_voice}
   - If TTS enabled: inherit from AudioMixin and use self.play_with_audio(animation, "narration")
   - If TTS disabled: inherit from Scene and use self.play(animation)

3. Layout Safety:
   - All objects must fit within x∈[-6,6], y∈[-3.5,3.5]
   - Title at y=3 using .to_edge(UP, buff=0.5)
   - Main visuals at y∈[-1,2]
   - Key points at y∈[-3,-2] using .to_edge(DOWN, buff=0.5)
   - Always use .scale() or .scale_to_fit_width() to keep objects on screen

4. Create ALL {len(story_plan.get("scenes", []))} scenes from the storyboard.

Storyboard:
{plan_str}
"""

        try:
            chain = self.prompt | self.llm
            response = chain.invoke({"story_plan": plan_str}).content.strip()
            
            # Extract and clean code
            code = self._extract_code(response)
            code = self._sanitize_code(code)
            self._validate_code(code)
            
        except Exception as e:
            print(f"[Error] LLM generation failed: {e}")
            # Fallback to simple template
            code = self._fallback_generation(story_plan)

        concept = story_plan.get("concept", "concept_visualization")
        file_name = self._slugify(concept)

        scene_narrations = [
            {"title": s.get("title", "Scene"), "narration": (s.get("narration") or "").strip()}
            for s in story_plan.get("scenes", [])
        ]

        return {
            "file_name": file_name,
            "code": code,
            "scene_narrations": scene_narrations,
        }

    def _fallback_generation(self, story_plan: Dict[str, Any]) -> str:
        """Simple fallback if LLM fails."""
        scenes = story_plan.get("scenes", [])
        if not scenes:
            return "from manim import *\n\nclass EmptyScene(Scene):\n    def construct(self):\n        pass"
        
        code_parts = ["from manim import *", "import numpy as np"]
        if self.use_tts:
            code_parts.append("from audio_mixin import AudioMixin\n")
        else:
            code_parts.append("")
        
        for scene in scenes:
            title = scene.get("title", "Scene")
            scene_name = re.sub(r"[^A-Za-z0-9]", "", title.title()) + "Scene"
            if not scene_name or scene_name == "Scene":
                scene_name = "GeneratedScene"
            
            base_class = "AudioMixin, Scene" if self.use_tts else "Scene"
            narration = scene.get("narration", "")
            title_literal = json.dumps(title[:40])
            narration_literal = json.dumps(narration[:140])
            key_point = scene.get("key_points", [""])[0] if scene.get("key_points") else ""
            key_literal = json.dumps(str(key_point)[:70])
            play_title = (
                f"self.play_with_audio(Write(title), {narration_literal})"
                if self.use_tts else
                "self.play(Write(title))"
            )
            
            scene_code = f"""
class {scene_name}({base_class}):
    def construct(self):
        title = Text({title_literal}, font_size=32).to_edge(UP, buff=0.5)
        {play_title}

        plane = NumberPlane(x_range=[-5, 5, 1], y_range=[-3, 3, 1]).set_opacity(0.35)
        circle = Circle(radius=1.1).set_color(BLUE).shift(LEFT * 2)
        arrow = Arrow(circle.get_right(), RIGHT * 2, buff=0.1).set_color(YELLOW)
        dot = Dot(RIGHT * 2).set_color(RED)
        label = Text({key_literal}, font_size=24).to_edge(DOWN, buff=0.5)

        self.play(Create(plane))
        self.play(Create(circle), GrowArrow(arrow), FadeIn(dot))
        self.play(Write(label))
        self.wait(2)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)
"""
            code_parts.append(scene_code)
        
        return "\n".join(code_parts)
