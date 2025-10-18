import re
import json
import os

class AlignerAgent:
    def align(self, generation_result):
        code = generation_result["code"]
        scene_narrations = generation_result["scene_narrations"]
        file_name = generation_result["file_name"]

        # Try to load actual audio durations if they exist
        audio_durations = {}
        possible_paths = [
            os.path.join("output", file_name.replace(".py", ""), "audio_durations.json"),
            os.path.join("checkpoints", "audio_durations.json"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    audio_durations = json.load(f)
                break

        # Replace each #WAIT_ placeholder with the exact duration
        for scene in scene_narrations:
            title = scene["title"]
            wait_key = re.sub(r"\W+", "_", title.upper())
            wait_comment = f"#WAIT_{wait_key}"

            duration = audio_durations.get(title)
            if duration is None:
                # fallback: estimate
                narration = scene.get("narration", "")
                duration = max(3.0, len(narration.split()) * 0.4)

            # Replace placeholder comment with actual wait
            code = code.replace(wait_comment, f"self.wait({duration:.2f})")

        return {
            "code": code,
            "file_name": file_name,
            "scene_narrations": scene_narrations,
        }
