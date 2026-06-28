from manim import *
from audio_mixin import AudioMixin


class AudioSmokeScene(AudioMixin, Scene):
    def construct(self):
        title = Text("Audio Smoke Test", font_size=36).to_edge(UP)
        circle = Circle(radius=1.0).set_color(GREEN)
        self.play_with_audio(Write(title), "This is a short narration test.")
        self.play(Create(circle))
        self.wait(0.5)
