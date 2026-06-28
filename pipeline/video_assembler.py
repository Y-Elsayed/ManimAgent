import json
import os
import shutil
import subprocess
from typing import Dict, List, Optional


class VideoAssembler:
    def __init__(self, mode: str = "ffmpeg"):
        self.mode = mode

    def assemble(self, title: str, clips: List[Dict], final_dir: str, file_name: str) -> Dict:
        os.makedirs(final_dir, exist_ok=True)
        manifest = {
            "title": title,
            "clips": clips,
            "theme": {"background": "#0B0F19", "accent": "#F7D154"},
            "mode": self.mode,
        }
        manifest_path = os.path.join(final_dir, f"{file_name}_assembly_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        if self.mode == "remotion":
            return {"manifest": manifest_path, "final_video": None, "status": "remotion_manifest_ready"}
        final_video = self._ffmpeg_concat([clip["video_path"] for clip in clips], final_dir, file_name)
        return {"manifest": manifest_path, "final_video": final_video, "status": "assembled" if final_video else "failed"}

    def _ffmpeg_concat(self, paths: List[str], final_dir: str, file_name: str) -> Optional[str]:
        paths = [path for path in paths if path and os.path.exists(path)]
        if not paths:
            return None
        output_path = os.path.join(final_dir, f"{file_name}_final.mp4")
        if len(paths) == 1:
            shutil.copy2(paths[0], output_path)
            return output_path
        concat_path = output_path + ".concat.txt"
        try:
            with open(concat_path, "w", encoding="utf-8") as f:
                for path in paths:
                    f.write(f"file '{os.path.abspath(path)}'\n")
            result = subprocess.run(
                ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_path, "-c", "copy", "-y", output_path],
                capture_output=True,
                text=True,
            )
            return output_path if result.returncode == 0 else None
        finally:
            if os.path.exists(concat_path):
                os.remove(concat_path)

