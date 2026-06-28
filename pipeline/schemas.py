import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class SchemaValidationError(ValueError):
    pass


@dataclass
class SceneObject:
    type: str
    id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "id": self.id, **self.data}


@dataclass
class SceneAnimation:
    type: str
    target: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "target": self.target, **self.data}


@dataclass
class SceneEquation:
    latex: str
    position: str = "bottom"

    def to_dict(self) -> Dict[str, Any]:
        return {"latex": self.latex, "position": self.position}


@dataclass
class SceneSpec:
    id: str
    title: str
    scene_type: str
    narration: str
    duration_seconds: int = 10
    objects: List[SceneObject] = field(default_factory=list)
    animations: List[SceneAnimation] = field(default_factory=list)
    equations: List[SceneEquation] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "scene_type": self.scene_type,
            "narration": self.narration,
            "duration_seconds": self.duration_seconds,
            "objects": [obj.to_dict() for obj in self.objects],
            "animations": [anim.to_dict() for anim in self.animations],
            "equations": [eq.to_dict() for eq in self.equations],
            "key_points": self.key_points,
        }


@dataclass
class SceneDSL:
    concept: str
    audience: str = "beginner"
    style: str = "3blue1brown_like"
    scenes: List[SceneSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "audience": self.audience,
            "style": self.style,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass
class QualityIssue:
    severity: str
    message: str
    repair_instruction: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "message": self.message,
            "repair_instruction": self.repair_instruction,
        }


@dataclass
class QualityReport:
    scene_id: str
    quality_score: float
    passed: bool
    issues: List[QualityIssue] = field(default_factory=list)
    frame_samples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "quality_score": self.quality_score,
            "passed": self.passed,
            "issues": [issue.to_dict() for issue in self.issues],
            "frame_samples": self.frame_samples,
            "repair_instructions": [
                issue.repair_instruction for issue in self.issues if issue.repair_instruction
            ],
        }


def validate_scene_dsl(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("Scene DSL must be an object")
    if not isinstance(data.get("concept"), str) or not data["concept"].strip():
        raise SchemaValidationError("Scene DSL requires a concept")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SchemaValidationError("Scene DSL requires at least one scene")
    for index, scene in enumerate(scenes, start=1):
        _validate_scene(scene, index)


def _validate_scene(scene: Dict[str, Any], index: int) -> None:
    required = ("id", "title", "scene_type", "narration", "objects", "animations", "equations")
    if not isinstance(scene, dict):
        raise SchemaValidationError(f"Scene {index} must be an object")
    for field_name in required:
        if field_name not in scene:
            raise SchemaValidationError(f"Scene {index} missing {field_name}")
    for field_name in ("id", "title", "scene_type", "narration"):
        if not isinstance(scene[field_name], str):
            raise SchemaValidationError(f"Scene {index} field {field_name} must be a string")
    for field_name in ("objects", "animations", "equations"):
        if not isinstance(scene[field_name], list):
            raise SchemaValidationError(f"Scene {index} field {field_name} must be a list")

