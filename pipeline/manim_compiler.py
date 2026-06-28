import ast
import json
import re
from typing import Any, Dict, List

from pipeline.schemas import SceneDSL, validate_scene_dsl


class ManimCompiler:
    def __init__(self, use_tts: bool = True, tts_voice: str = "onyx", voiceover_mode: str = "audio_mixin"):
        self.use_tts = use_tts
        self.tts_voice = tts_voice or "onyx"
        self.voiceover_mode = voiceover_mode

    def compile(self, dsl: SceneDSL) -> Dict[str, Any]:
        validate_scene_dsl(dsl.to_dict())
        code_parts = ["from manim import *", "import numpy as np"]
        if self.use_tts and self.voiceover_mode == "manim_voiceover":
            code_parts.append("from manim_voiceover import VoiceoverScene")
            code_parts.append("from manim_voiceover.services.openai import OpenAIService")
        elif self.use_tts:
            code_parts.append("from audio_mixin import AudioMixin")
        code_parts.append("")
        for scene in dsl.scenes:
            code_parts.append(self._compile_scene(scene.to_dict()))
        code = "\n\n".join(code_parts).strip() + "\n"
        ast.parse(code)
        return {
            "file_name": self._slugify(dsl.concept),
            "code": code,
            "scene_narrations": [{"id": s.id, "title": s.title, "narration": s.narration} for s in dsl.scenes],
            "metadata": {"generator": "scene_dsl_compiler", "voiceover_mode": self.voiceover_mode},
        }

    def _compile_scene(self, scene: Dict[str, Any]) -> str:
        class_name = self._class_name(scene["id"], scene["title"])
        if self.use_tts and self.voiceover_mode == "manim_voiceover":
            base_class = "VoiceoverScene"
        else:
            base_class = "AudioMixin, Scene" if self.use_tts else "Scene"
        body = self._template(scene)
        if self.use_tts and self.voiceover_mode == "manim_voiceover":
            body = f"self.set_speech_service(OpenAIService(voice={json.dumps(self.tts_voice)}))\n" + body
        return f"class {class_name}({base_class}):\n    def construct(self):\n{self._indent(body, 8)}"

    def _template(self, scene: Dict[str, Any]) -> str:
        title = json.dumps(scene["title"][:50])
        narration = json.dumps(scene["narration"][:220])
        key_point = json.dumps((scene.get("key_points") or [""])[0][:90])
        equation = self._equation(scene)
        scene_type = scene["scene_type"]
        play_title = self._play("Write(title)", narration)
        if scene_type == "linear_transform_2d":
            return self._linear_transform(title, play_title, key_point, equation)
        if scene_type == "vector_addition":
            return self._vector_addition(title, play_title, key_point, equation)
        if scene_type == "graph_function":
            return self._graph_function(title, play_title, key_point, equation)
        if scene_type == "force_diagram":
            return self._force_diagram(title, play_title, key_point, equation)
        if scene_type == "equation_derivation":
            return self._equation_derivation(title, play_title, key_point, equation)
        return self._concept_intro(title, play_title, key_point, equation)

    def _concept_intro(self, title, play_title, key_point, equation):
        return f"""
title = Text({title}, font_size=34).to_edge(UP, buff=0.45)
{play_title}
idea = Circle(radius=1.15).set_color(BLUE).shift(LEFT * 1.7)
label = Text("Idea", font_size=28).move_to(idea.get_center())
arrow = Arrow(idea.get_right(), RIGHT * 1.7, buff=0.1).set_color(YELLOW)
result = Circle(radius=1.15).set_color(GREEN).shift(RIGHT * 2.8)
result_label = Text("Insight", font_size=26).move_to(result.get_center())
point = Text({key_point}, font_size=24).scale_to_fit_width(10).to_edge(DOWN, buff=0.5)
self.play(Create(idea), FadeIn(label))
self.play(GrowArrow(arrow), Create(result), FadeIn(result_label))
self.play(Write(point))
self.wait(1)
self.play(FadeOut(*self.mobjects))
self.wait(0.4)
"""

    def _linear_transform(self, title, play_title, key_point, equation):
        return f"""
title = Text({title}, font_size=34).to_edge(UP, buff=0.45)
{play_title}
plane = NumberPlane(x_range=[-5, 5, 1], y_range=[-3, 3, 1]).set_opacity(0.35)
v = Arrow(ORIGIN, [3, 0, 0], buff=0).set_color(YELLOW)
w = Arrow(ORIGIN, [4.2, 0, 0], buff=0).set_color(ORANGE)
moving = Arrow(ORIGIN, [2, 1.2, 0], buff=0).set_color(BLUE)
eq = MathTex(r{json.dumps(equation)}, font_size=34).to_edge(DOWN, buff=0.55)
label = Text({key_point}, font_size=22).scale_to_fit_width(9.5).next_to(eq, UP, buff=0.35)
self.play(Create(plane))
self.play(GrowArrow(moving), GrowArrow(v))
self.play(Transform(v, w), moving.animate.put_start_and_end_on(ORIGIN, [1.2, 2.4, 0]))
self.play(Write(eq), FadeIn(label))
self.wait(1)
self.play(FadeOut(*self.mobjects))
self.wait(0.4)
"""

    def _vector_addition(self, title, play_title, key_point, equation):
        return f"""
title = Text({title}, font_size=34).to_edge(UP, buff=0.45)
{play_title}
plane = NumberPlane(x_range=[-5, 5, 1], y_range=[-3, 3, 1]).set_opacity(0.35)
v1 = Arrow(ORIGIN, [2, 1, 0], buff=0).set_color(BLUE)
v2 = Arrow([2, 1, 0], [4, 2.4, 0], buff=0).set_color(GREEN)
total = Arrow(ORIGIN, [4, 2.4, 0], buff=0).set_color(YELLOW)
label = Text({key_point}, font_size=24).scale_to_fit_width(10).to_edge(DOWN, buff=0.55)
self.play(Create(plane))
self.play(GrowArrow(v1))
self.play(GrowArrow(v2))
self.play(GrowArrow(total), Write(label))
self.wait(1)
self.play(FadeOut(*self.mobjects))
self.wait(0.4)
"""

    def _graph_function(self, title, play_title, key_point, equation):
        return f"""
title = Text({title}, font_size=34).to_edge(UP, buff=0.45)
{play_title}
axes = Axes(x_range=[-4, 4, 1], y_range=[-1, 5, 1], x_length=8, y_length=4).shift(DOWN * 0.25)
curve = axes.plot(lambda x: 0.25 * (x - 1) ** 2 + 0.5, color=BLUE)
point = Dot(axes.c2p(1, 0.5)).set_color(YELLOW)
tangent = Line(axes.c2p(-0.2, 0.8), axes.c2p(2.2, 0.8)).set_color(ORANGE)
label = Text({key_point}, font_size=24).scale_to_fit_width(10).to_edge(DOWN, buff=0.55)
self.play(Create(axes))
self.play(Create(curve))
self.play(FadeIn(point), Create(tangent))
self.play(Write(label))
self.wait(1)
self.play(FadeOut(*self.mobjects))
self.wait(0.4)
"""

    def _force_diagram(self, title, play_title, key_point, equation):
        return f"""
title = Text({title}, font_size=34).to_edge(UP, buff=0.45)
{play_title}
ground = Line(LEFT * 4, RIGHT * 4).shift(DOWN * 1.2).set_color(GRAY)
block = Square(side_length=1.2).set_fill(BLUE, opacity=0.35).shift(DOWN * 0.55)
force = Arrow(block.get_right(), block.get_right() + RIGHT * 2.1, buff=0).set_color(YELLOW)
normal = Arrow(block.get_top(), block.get_top() + UP * 1.6, buff=0).set_color(GREEN)
gravity = Arrow(block.get_bottom(), block.get_bottom() + DOWN * 1.6, buff=0).set_color(RED)
label = Text({key_point}, font_size=24).scale_to_fit_width(10).to_edge(DOWN, buff=0.55)
self.play(Create(ground), FadeIn(block))
self.play(GrowArrow(force), GrowArrow(normal), GrowArrow(gravity))
self.play(Write(label))
self.wait(1)
self.play(FadeOut(*self.mobjects))
self.wait(0.4)
"""

    def _equation_derivation(self, title, play_title, key_point, equation):
        return f"""
title = Text({title}, font_size=34).to_edge(UP, buff=0.45)
{play_title}
eq1 = MathTex(r{json.dumps(equation)}, font_size=42).shift(UP * 0.7)
box = SurroundingRectangle(eq1, color=YELLOW, buff=0.25)
point = Text({key_point}, font_size=24).scale_to_fit_width(10).to_edge(DOWN, buff=0.55)
self.play(Write(eq1))
self.play(Create(box))
self.play(Write(point))
self.wait(1)
self.play(FadeOut(*self.mobjects))
self.wait(0.4)
"""

    def _play(self, animation: str, narration: str) -> str:
        if not self.use_tts:
            return f"self.play({animation})"
        if self.voiceover_mode == "manim_voiceover":
            return f"with self.voiceover(text={narration}):\n    self.play({animation})"
        return f"self.play_with_audio({animation}, {narration}, voice={json.dumps(self.tts_voice)})"

    def _equation(self, scene: Dict[str, Any]) -> str:
        equations = scene.get("equations") or []
        if equations:
            return equations[0].get("latex") or r"x=x"
        return r"x=x"

    def _class_name(self, scene_id: str, title: str) -> str:
        raw = re.sub(r"[^A-Za-z0-9]+", "", title.title()) or scene_id.title().replace("_", "")
        if raw[0].isdigit():
            raw = "Scene" + raw
        return raw + "Scene"

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
        return slug[:40] or "visualization"

    def _indent(self, text: str, spaces: int) -> str:
        prefix = " " * spaces
        return "\n".join(prefix + line if line.strip() else line for line in text.strip().splitlines())
