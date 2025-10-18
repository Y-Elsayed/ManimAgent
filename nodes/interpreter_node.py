import os
import re
import subprocess
from openai import OpenAI


class InterpreterNode:
    def __init__(self):
        self.client = OpenAI()

    # -------------------------------------------------
    # Detect scene names from generated Manim script
    # -------------------------------------------------
    def _detect_scene_names(self, code: str):
        pattern = r"class\s+([A-Za-z0-9_]+Scene)\s*\("
        return re.findall(pattern, code)

    # -------------------------------------------------
    # Locate rendered scene file (robust fallback)
    # -------------------------------------------------
    def _expected_video_path(self, output_dir: str, base_name: str, scene_name: str):
        primary = os.path.join(output_dir, "media", "videos", base_name, "480p15", f"{scene_name}.mp4")
        if os.path.exists(primary):
            return primary

        fallback = os.path.join("media", "videos", base_name, "480p15", f"{scene_name}.mp4")
        if os.path.exists(fallback):
            return fallback

        raise FileNotFoundError(
            f"Expected video not found in either:\n - {primary}\n - {fallback}"
        )

    # -------------------------------------------------
    # Get file duration (seconds)
    # -------------------------------------------------
    def _get_duration(self, file_path: str):
        """Return duration of a media file in seconds using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    # -------------------------------------------------
    # Run pipeline
    # -------------------------------------------------
    def run(self, code, file_name, scene_narrations, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        # Save generated Manim script
        script_path = os.path.join(output_dir, f"{file_name}.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Detect scene classes
        scene_names = self._detect_scene_names(code)
        if not scene_names:
            print("No Manim scenes found in the generated code.")
            return None

        final_scene_videos = []
        base_name = os.path.splitext(file_name)[0]

        # -------------------------------------------------
        # Sequential scene processing
        # -------------------------------------------------
        for i, scene_name in enumerate(scene_names):
            title = scene_narrations[i].get("title", f"Scene {i+1}") if i < len(scene_narrations) else f"Scene {i+1}"
            narration = scene_narrations[i].get("narration", "") if i < len(scene_narrations) else ""

            print(f"\n--- Processing Scene {i+1}/{len(scene_names)}: {title} ({scene_name}) ---")

            try:
                subprocess.run(["manim", "-ql", script_path, scene_name], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to render {scene_name}: {e}")
                continue

            try:
                base_video = self._expected_video_path(output_dir, base_name, scene_name)
            except FileNotFoundError as e:
                print(f"{e}")
                continue

            # Generate narration
            audio_path = os.path.join(output_dir, f"scene_{i+1}.mp3")
            if narration.strip():
                try:
                    print(f"Generating narration for '{title}' ...")
                    with self.client.audio.speech.with_streaming_response.create(
                        model="gpt-4o-mini-tts",
                        voice="alloy",
                        input=narration
                    ) as response:
                        response.stream_to_file(audio_path)
                except Exception as e:
                    print(f"Failed to generate TTS for scene {i+1}: {e}")
                    audio_path = None
            else:
                audio_path = None

            # --------------- Merge scene + audio ----------------
            scene_final = os.path.join(output_dir, f"scene_{i+1}_final.mp4")

            try:
                if audio_path and os.path.exists(audio_path):
                    video_dur = self._get_duration(base_video)
                    audio_dur = self._get_duration(audio_path)
                    total_dur = max(video_dur, audio_dur)

                    subprocess.run([
                        "ffmpeg", "-y",
                        "-i", base_video, "-i", audio_path,
                        "-filter_complex",
                        f"[0:v]tpad=stop_mode=clone:stop_duration={total_dur - video_dur}[v];[1:a]apad[a]",
                        "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-c:a", "aac",
                        "-shortest", scene_final
                    ], check=True)
                else:
                    subprocess.run([
                        "ffmpeg", "-y", "-i", base_video, "-c", "copy", scene_final
                    ], check=True)

                final_scene_videos.append(scene_final)
                print(f"Scene {i+1} complete: {scene_final}")

            except subprocess.CalledProcessError as e:
                print(f"Failed to merge scene {i+1}: {e}")

        # -------------------------------------------------
        # Merge all scenes into a single video
        # -------------------------------------------------
        if not final_scene_videos:
            print("No scenes successfully processed — aborting merge.")
            return None

        full_dir = os.path.join(output_dir, "full")
        os.makedirs(full_dir, exist_ok=True)

        concat_file = os.path.join(output_dir, "scenes_list.txt")
        with open(concat_file, "w") as f:
            for path in final_scene_videos:
                f.write(f"file '{os.path.abspath(path)}'\n")

        final_video = os.path.join(full_dir, f"{file_name}.mp4")
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", final_video
            ], check=True)
            print(f"\n🎬 All scenes merged successfully → {final_video}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to merge final video: {e}")
            return None

        # -------------------------------------------------
        # Merge all scene classes into one script
        # -------------------------------------------------
        merged_script_path = os.path.join(full_dir, f"{file_name}.py")
        print(f"\nMerging all scene classes into one file → {merged_script_path}")

        scenes = re.findall(r"(class\s+[A-Za-z0-9_]+Scene\s*\(.*?\):.*?)(?=class|\Z)", code, re.DOTALL)
        merged_code = "from manim import *\n\n" + "\n\n".join(scenes)

        with open(merged_script_path, "w", encoding="utf-8") as f:
            f.write(merged_code)

        print(f"Scene script merged successfully → {merged_script_path}")

        # -------------------------------------------------
        # Play only the final video (not all scenes)
        # -------------------------------------------------
        try:
            subprocess.run(["open", final_video])  # macOS: use 'xdg-open' on Linux
        except Exception:
            pass

        print("\nSession complete.")
        return final_video
