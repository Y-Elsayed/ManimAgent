from manim import *


class BrokenSmokeScene(Scene):
    def construct(self):
        title = Text("Broken Smoke Test", font_size=36).to_edge(UP)
        self.play(Write(title))
        self.play(Create(NotAManimObject()))
