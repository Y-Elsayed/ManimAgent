import os
import subprocess
from openai import OpenAI


class AudioMixin:
    """
    Provides synchronized playback of narration and visuals.
    Each call to play_with_audio() generates speech, attaches the audio,
    and plays the animation for exactly that duration.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = OpenAI()
        self.audio_cache = {}
        self.output_dir = os.path.join(os.getcwd(), "audio_cache")
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_audio_duration(self, file_path: str) -> float:
        """Return duration (seconds) of an audio file using ffprobe."""
        if not os.path.exists(file_path):
            return 0.0
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", file_path
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            return float(result.stdout.strip())
        except Exception:
            return 0.0

def _tts(self, text: str, file_path: str, voice: str = "onyx"):
    """
    Generate speech via OpenAI TTS API with correct WAV encoding.
    """
    try:
        with self.client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
            format="wav"
        ) as response:
            response.stream_to_file(file_path)
    except Exception as e:
        print(f"[TTS Error] {e}")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "1", "-acodec", "pcm_s16le", file_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    def play_with_audio(self, animation, narration: str, voice: str = "onyx"):
        """
        Generate TTS audio for `narration` and play animation for its duration.
        """
        if not narration.strip():
            self.play(animation)
            return

        # use .wav format for compatibility
        file_name = str(abs(hash(narration))) + ".wav"
        file_path = os.path.join(self.output_dir, file_name)

        if file_name not in self.audio_cache:
            print(f"[TTS] Generating audio: {narration[:60]}...")
            self._tts(narration, file_path, voice)
            duration = self._get_audio_duration(file_path)
            self.audio_cache[file_name] = duration
        else:
            duration = self.audio_cache[file_name]

        # Attach audio to scene and play
        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            self.add_sound(abs_path)
        else:
            print(f"[Warning] Missing audio file: {abs_path}")

        self.play(animation, run_time=max(duration, 2.0))  # Ensure minimum length
        self.wait(0.3)
