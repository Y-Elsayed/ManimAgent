import glob
import json
import os
import shutil
import subprocess
from typing import Dict, List

from pipeline.schemas import QualityIssue, QualityReport


class VisualCritic:
    def __init__(self, min_score: float = 0.75):
        self.min_score = min_score

    def evaluate_render_result(self, render_result: Dict, dsl: Dict, debug_dir: str) -> Dict:
        reports = []
        rendered = set(render_result.get("rendered", [])) if render_result else set()
        for scene in dsl.get("scenes", []):
            reports.append(self._evaluate_scene(scene, rendered, debug_dir).to_dict())
        summary = {
            "quality_target": self.min_score,
            "passed": all(report["passed"] for report in reports),
            "reports": reports,
        }
        os.makedirs(debug_dir, exist_ok=True)
        with open(os.path.join(debug_dir, "quality_report.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return summary

    def extract_frame_samples(self, video_paths: List[str], scene_ids: List[str], debug_dir: str) -> List[str]:
        sample_dir = os.path.join(debug_dir, "frame_samples")
        os.makedirs(sample_dir, exist_ok=True)
        if not shutil.which("ffmpeg"):
            return []
        samples = []
        for index, video_path in enumerate(video_paths):
            if not video_path or not os.path.exists(video_path):
                continue
            scene_id = scene_ids[index] if index < len(scene_ids) else f"scene_{index + 1:02d}"
            for label, timestamp in (("start", "00:00:01"), ("middle", "00:00:04"), ("late", "00:00:08")):
                out_path = os.path.join(sample_dir, f"{scene_id}_{label}.png")
                result = subprocess.run(
                    ["ffmpeg", "-y", "-ss", timestamp, "-i", video_path, "-frames:v", "1", out_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if result.returncode == 0 and os.path.exists(out_path):
                    samples.append(out_path)
        return samples

    def _evaluate_scene(self, scene: Dict, rendered: set, debug_dir: str) -> QualityReport:
        issues: List[QualityIssue] = []
        scene_id = scene["id"]
        if not self._scene_rendered(scene, rendered):
            issues.append(QualityIssue("error", "Scene did not render", "Fix render error before visual quality repair"))
        if not scene.get("objects"):
            issues.append(QualityIssue("warning", "Scene has no visual objects", "Add at least one meaningful visual object"))
        if len(scene.get("narration", "")) > 260:
            issues.append(QualityIssue("warning", "Narration is too long for one scene", "Split narration across multiple animation beats"))
        if scene.get("scene_type") == "concept_intro" and len(scene.get("objects", [])) < 3:
            issues.append(QualityIssue("warning", "Intro scene may be visually sparse", "Add relationship arrows or comparison objects"))
        score = max(0.0, 1.0 - 0.18 * len(issues))
        return QualityReport(
            scene_id=scene_id,
            quality_score=score,
            passed=score >= self.min_score and not any(issue.severity == "error" for issue in issues),
            issues=issues,
            frame_samples=self._frame_samples(debug_dir, scene_id),
        )

    def _scene_rendered(self, scene: Dict, rendered: set) -> bool:
        expected_suffix = "Scene"
        title_name = "".join(part for part in scene["title"].title() if part.isalnum()) + expected_suffix
        return title_name in rendered or scene["id"] in rendered

    def _frame_samples(self, debug_dir: str, scene_id: str) -> List[str]:
        sample_dir = os.path.join(debug_dir, "frame_samples")
        return glob.glob(os.path.join(sample_dir, f"{scene_id}_*.png"))
