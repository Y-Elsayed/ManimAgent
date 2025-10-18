import subprocess
import json
import os
import re
from openai import OpenAI


class InterpreterNode:
    """
    Executes generated Manim code scene by scene, 
    generates one TTS audio clip per scene, 
    waits in Manim for that duration, and merges audio+video.
    """

    def __init__(self):
        self.client = OpenAI()

    def _get_audio_duration(self, path: str) -> float:
        """Return audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0", path
        ]
        out = subprocess.check_output(cmd, text=True).strip()
        return float(out)

    def run(self, code: str, file_name: str, scene_narrations: list, output_dir: str = "./output"):
        base_dir = os.path.join(output_dir, file_name)
        os.makedirs(base_dir, exist_ok=True)

        # --- Generate per-scene audio & record durations
        audio_info = {}
        for scene in scene_narrations:
            title = re.sub(r"[^a-zA-Z0-9]+", "_", scene["title"])
            audio_path = os.path.join(base_dir, f"{title}.mp3")

            print(f"Generating TTS for scene: {scene['title']} ...")
            speech = self.client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=scene["narration"]
            )
            with open(audio_path, "wb") as f:
                f.write(speech.audio)

            duration = self._get_audio_duration(audio_path)
            audio_info[scene["title"]] = {"path": audio_path, "duration": duration}

        # --- Inject waits into the code
        print("Adjusting Manim code for timing...")
        adjusted_code = code
        for title, meta in audio_info.items():
            placeholder = f"#WAIT_{title.upper().replace(' ', '_')}"
            wait_line = f"self.wait({meta['duration']:.2f})  # auto-synced to narration\n"
            adjusted_code = adjusted_code.replace(placeholder, wait_line)

        script_path = os.path.join(base_dir, f"{file_name}.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(adjusted_code)

        # --- render the video
        print("Rendering animation...")
        subprocess.run(["manim", "-pql", script_path, "ConceptScene"], check=True)
        video_path = os.path.join(base_dir, f"{file_name}.mp4")

        # --- merge per-scene audio files sequentially
        print("Merging all scene audios...")
        concat_list = os.path.join(base_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for meta in audio_info.values():
                f.write(f"file '{meta['path']}'\n")

        merged_audio = os.path.join(base_dir, f"{file_name}_narration.mp3")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", concat_list, "-c", "copy", merged_audio], check=True)

        final_output = os.path.join(base_dir, f"{file_name}_final.mp4")
        print("Combining audio with video...")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-i", merged_audio,
            "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)

        return final_output
