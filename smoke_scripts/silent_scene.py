from manim import *


class SilentSmokeScene(Scene):
    def construct(self):
        title = Text("Smoke Test", font_size=36).to_edge(UP)
        circle = Circle(radius=1.0).set_color(BLUE)
        dot = Dot().set_color(YELLOW)
        self.play(Write(title))
        self.play(Create(circle), FadeIn(dot))
        self.wait(0.5)
