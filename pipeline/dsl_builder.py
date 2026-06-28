import re
from typing import Any, Dict, List

from pipeline.schemas import SceneAnimation, SceneDSL, SceneEquation, SceneObject, SceneSpec, validate_scene_dsl


class SceneDSLBuilder:
    def build(self, story_plan: Dict[str, Any], audience: str = "beginner", style: str = "3blue1brown_like") -> SceneDSL:
        concept = str(story_plan.get("concept") or "Concept").strip()
        scenes = []
        for index, scene in enumerate(story_plan.get("scenes", []), start=1):
            scenes.append(self._build_scene(concept, scene, index))
        if not scenes:
            scenes.append(self._build_scene(concept, {"title": concept, "narration": "", "visuals": [], "key_points": []}, 1))
        dsl = SceneDSL(concept=concept, audience=audience, style=style, scenes=scenes)
        validate_scene_dsl(dsl.to_dict())
        return dsl

    def _build_scene(self, concept: str, scene: Dict[str, Any], index: int) -> SceneSpec:
        title = str(scene.get("title") or f"Scene {index}").strip()
        narration = str(scene.get("narration") or "").strip()
        visuals = [str(item) for item in scene.get("visuals", [])]
        key_points = [str(item) for item in scene.get("key_points", [])]
        text = " ".join([concept, title, narration, *visuals, *key_points]).lower()
        scene_type = self._choose_scene_type(text, index)
        equations = self._extract_equations(key_points)
        if scene_type in {"equation_derivation", "linear_transform_2d"} and not equations:
            equations = [SceneEquation(latex=self._default_equation(concept, scene_type))]
        objects, animations = self._objects_for_type(scene_type)
        return SceneSpec(
            id=f"scene_{index:02d}",
            title=title,
            scene_type=scene_type,
            narration=narration,
            duration_seconds=self._estimate_duration(narration),
            objects=objects,
            animations=animations,
            equations=equations,
            key_points=key_points,
        )

    def _choose_scene_type(self, text: str, index: int) -> str:
        if any(word in text for word in ("eigen", "matrix", "linear transformation", "transform")):
            return "linear_transform_2d"
        if any(word in text for word in ("vector addition", "sum of vectors", "add vectors")):
            return "vector_addition"
        if any(word in text for word in ("graph", "function", "curve", "derivative", "gradient")):
            return "graph_function"
        if any(word in text for word in ("force", "newton", "acceleration", "friction")):
            return "force_diagram"
        if any(word in text for word in ("equation", "formula", "derive", "law")):
            return "equation_derivation"
        if index == 1:
            return "concept_intro"
        return "coordinate_plane"

    def _objects_for_type(self, scene_type: str):
        base = [SceneObject(type="title", id="title"), SceneObject(type="text", id="key_point")]
        if scene_type == "linear_transform_2d":
            objects = [SceneObject(type="number_plane", id="plane"), SceneObject(type="vector", id="eigen_vector"), *base]
            animations = [SceneAnimation(type="create", target="plane"), SceneAnimation(type="transform_vector", target="eigen_vector")]
        elif scene_type == "vector_addition":
            objects = [SceneObject(type="number_plane", id="plane"), SceneObject(type="vector", id="v1"), SceneObject(type="vector", id="v2"), SceneObject(type="vector", id="sum"), *base]
            animations = [SceneAnimation(type="create", target="plane"), SceneAnimation(type="grow_arrow", target="v1"), SceneAnimation(type="grow_arrow", target="v2"), SceneAnimation(type="grow_arrow", target="sum")]
        elif scene_type == "graph_function":
            objects = [SceneObject(type="axes", id="axes"), SceneObject(type="curve", id="curve"), SceneObject(type="dot", id="point"), *base]
            animations = [SceneAnimation(type="create", target="axes"), SceneAnimation(type="create", target="curve"), SceneAnimation(type="fade_in", target="point")]
        elif scene_type == "force_diagram":
            objects = [SceneObject(type="block", id="block"), SceneObject(type="force_arrow", id="force"), SceneObject(type="force_arrow", id="normal"), *base]
            animations = [SceneAnimation(type="fade_in", target="block"), SceneAnimation(type="grow_arrow", target="force"), SceneAnimation(type="grow_arrow", target="normal")]
        elif scene_type == "equation_derivation":
            objects = [SceneObject(type="equation", id="main_equation"), *base]
            animations = [SceneAnimation(type="write", target="main_equation")]
        else:
            objects = [SceneObject(type="circle", id="idea"), SceneObject(type="arrow", id="relationship"), *base]
            animations = [SceneAnimation(type="create", target="idea"), SceneAnimation(type="grow_arrow", target="relationship")]
        return objects, animations

    def _extract_equations(self, key_points: List[str]) -> List[SceneEquation]:
        equations = []
        for point in key_points:
            if any(token in point for token in ("=", "\\", "^", "_")):
                equations.append(SceneEquation(latex=self._clean_latex(point)))
        return equations[:2]

    def _clean_latex(self, value: str) -> str:
        value = value.strip()
        value = re.sub(r"^(equation|formula)\s*:\s*", "", value, flags=re.IGNORECASE)
        return value[:120] or r"x = x"

    def _default_equation(self, concept: str, scene_type: str) -> str:
        if scene_type == "linear_transform_2d":
            return r"A\vec{v}=\lambda\vec{v}"
        safe = re.sub(r"[^A-Za-z0-9 ]+", "", concept).strip() or "Idea"
        return rf"\text{{{safe[:30]}}}"

    def _estimate_duration(self, narration: str) -> int:
        words = len(narration.split())
        return max(7, min(18, round(words / 2.2) if words else 8))

