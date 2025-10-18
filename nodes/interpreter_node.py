import os
import re
import subprocess
import shutil
import json
import time
from openai import OpenAI


class InterpreterNode:
    def __init__(self):
        self.client = OpenAI()

    def _detect_scene_names(self, code: str):
        pattern = r"class\s+([A-Za-z0-9_]+Scene)\s*\("
        return re.findall(pattern, code)

    def _expected_video_path(self, base_name: str, scene_name: str):
        base = os.path.join(os.getcwd(), "media", "videos", base_name)
        video_path = os.path.join(base, "480p15", f"{scene_name}.mp4")
        if not os.path.exists(video_path):
            print(f"[Warn] Expected video not found at {video_path}. Trying fallback...")
            for root, _, files in os.walk(os.path.join(os.getcwd(), "media", "videos")):
                for file in files:
                    if file == f"{scene_name}.mp4":
                        print(f"[Found] Using fallback: {os.path.join(root, file)}")
                        return os.path.join(root, file)
            raise FileNotFoundError(f"Expected video not found anywhere for: {scene_name}")
        return video_path

    def _format_time(self, seconds: float):
        h, m = divmod(seconds, 3600)
        m, s = divmod(m, 60)
        return f"{int(h):02}:{int(m):02}:{int(s):02},000"

    def _get_duration(self, path):
        if not os.path.exists(path):
            return 0.0
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _generate_subtitles_and_text(self, narrations, audio_durations, output_dir):
        srt_path = os.path.join(output_dir, "subtitles.srt")
        narration_txt = os.path.join(output_dir, "narration.txt")
        total_time = 0.0

        with open(srt_path, "w", encoding="utf-8") as srt, open(narration_txt, "w", encoding="utf-8") as txt:
            for i, scene in enumerate(narrations, start=1):
                narration = scene.get("narration", "").strip()
                duration = audio_durations[i - 1] if i - 1 < len(audio_durations) else len(narration) * 0.08
                start = self._format_time(total_time)
                end = self._format_time(total_time + duration)
                total_time += duration + 0.5
                srt.write(f"{i}\n{start} --> {end}\n{narration}\n\n")
                txt.write(f"{scene.get('title', f'Scene {i}')}\n{narration}\n\n")

        return srt_path, narration_txt

    # -------------------------------------------------
    # Safe audio generation with fallback + retry
    # -------------------------------------------------
    def _generate_tts(self, narration, audio_path, retries=2):
        models = ["gpt-4o-mini-tts", "gpt-4o-mini"]  # primary → fallback
        voices = ["alloy", "verse", "sage"]

        for model in models:
            for attempt in range(retries):
                try:
                    response = self.client.audio.speech.create(
                        model=model,
                        voice=voices[attempt % len(voices)],
                        input=narration
                    )
                    response.stream_to_file(audio_path)
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 500:
                        print(f"   ✓ TTS succeeded with model={model}, voice={voices[attempt % len(voices)]}")
                        return True
                except Exception as e:
                    print(f"   ⚠ TTS attempt {attempt+1} with {model} failed: {e}")
                    time.sleep(1.5)
        return False  # All failed

    # -------------------------------------------------
    # Main pipeline
    # -------------------------------------------------
    def run(self, code, file_name, scene_narrations, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        audio_dir = os.path.join(output_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        # Save Manim script
        script_path = os.path.join(output_dir, file_name if file_name.endswith(".py") else f"{file_name}.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        scene_names = self._detect_scene_names(code)
        if not scene_names:
            print("No Manim scenes found in the generated code.")
            return None

        base_name = os.path.splitext(file_name)[0]
        final_scene_videos = []
        audio_durations = []
        durations_dict = {}

        for i, scene_name in enumerate(scene_names):
            title = scene_narrations[i].get("title", f"Scene {i+1}") if i < len(scene_narrations) else f"Scene {i+1}"
            narration = scene_narrations[i].get("narration", "") if i < len(scene_narrations) else ""
            print(f"[Scene {i+1}/{len(scene_names)}] {title} ({scene_name})")

            # 1. Render Manim
            try:
                subprocess.run(["manim", "-ql", "--disable_caching", script_path, scene_name], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to render {scene_name}: {e}")
                continue

            # Locate rendered video
            try:
                base_video = self._expected_video_path(base_name, scene_name)
            except FileNotFoundError as e:
                print(e)
                continue

            # 2. Generate audio safely
            audio_path = os.path.join(audio_dir, f"scene_{i+1}.mp3")
            audio_duration = 0.0
            if narration.strip():
                print(f"Generating narration for '{title}'...")
                success = self._generate_tts(narration, audio_path)
                if success:
                    audio_duration = round(self._get_duration(audio_path) + 0.3, 2)
                    print(f"   ✓ Audio duration: {audio_duration}s")
                else:
                    print(f"   ⚠ All TTS attempts failed for scene {i+1}. Proceeding silently.")
                    audio_path = None
            else:
                print("   ⚠ No narration text provided.")

            audio_durations.append(audio_duration)
            durations_dict[title] = audio_duration

            # 3. Merge video + audio
            scene_final = os.path.join(output_dir, f"scene_{i+1}_final.mp4")
            video_duration = self._get_duration(base_video)
            final_duration = max(audio_duration, video_duration)

            try:
                if audio_path and os.path.exists(audio_path):
                    subprocess.run([
                        "ffmpeg", "-y",
                        "-i", base_video,
                        "-i", audio_path,
                        "-c:v", "copy", "-c:a", "aac",
                        "-t", str(final_duration),
                        "-shortest", scene_final
                    ], check=True)
                else:
                    subprocess.run(["ffmpeg", "-y", "-i", base_video, "-c", "copy", scene_final], check=True)
                final_scene_videos.append(scene_final)
                print(f"Scene {i+1} done → {scene_final}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to merge scene {i+1}: {e}")

        # Merge all scenes
        if not final_scene_videos:
            print("No successful scenes.")
            return None

        concat_file = os.path.join(output_dir, "scenes_list.txt")
        with open(concat_file, "w") as f:
            for path in final_scene_videos:
                f.write(f"file '{os.path.abspath(path)}'\n")

        full_dir = os.path.join(output_dir, "full")
        os.makedirs(full_dir, exist_ok=True)
        final_video = os.path.join(full_dir, f"{base_name}_final.mp4")

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file, "-c", "copy", final_video
        ], check=False)

        print(f"\nFinal merged video: {os.path.abspath(final_video)}")

        # Subtitles & narration
        srt_path, narration_txt = self._generate_subtitles_and_text(scene_narrations, audio_durations, full_dir)
        print(f"Subtitles saved to: {os.path.abspath(srt_path)}")
        print(f"Narration text saved to: {os.path.abspath(narration_txt)}")

        # Durations JSON
        durations_path = os.path.join(full_dir, "audio_durations.json")
        with open(durations_path, "w", encoding="utf-8") as f:
            json.dump(durations_dict, f, indent=2)
        print(f"Audio durations saved → {os.path.abspath(durations_path)}")

        print("Cleanup complete.\nSession complete.")
        return final_video
