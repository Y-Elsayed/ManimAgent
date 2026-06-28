# ManimAgent

ManimAgent is a CLI pipeline that turns a scientific or mathematical topic into a narrated Manim video.

Current flow:

1. Plan a storyboard with an LLM.
2. Convert the storyboard into a structured scene DSL.
3. Compile deterministic Manim Python code from the DSL.
4. Sanitize and validate generated code.
5. Render each scene with Manim.
6. Repair failed renders with an LLM fixer when possible.
7. Evaluate rendered output with a quality report.
8. Write an assembly manifest and merge a final video.

## Requirements

- Python 3.10+; Python 3.11 is recommended.
- FFmpeg available on `PATH`.
- Manim and its system dependencies.
- LaTeX/MiKTeX if generated scenes use `Tex` or `MathTex`.
- An OpenAI API key.

On Windows, install FFmpeg and MiKTeX manually or through a package manager, then confirm:

```powershell
ffmpeg -version
pdflatex --version
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional macOS-only packages are listed in `requirements-macos.txt`.
Optional voiceover integration is listed in `requirements-voiceover.txt`.

Create `.env`:

```env
OPENAI_API_KEY=sk-proj-your-key
```

## Run

```powershell
python main.py
```

The app will ask for:

- concept to visualize
- whether to enable text-to-speech narration
- TTS voice

Generated projects are saved under:

```text
projects/<concept>/
  debug/
    story_plan.json
    scene_dsl.json
    generation_result.json
    quality_report.json
    assembly_result.json
  output/
  media/
  final/
```

## Voiceover Mode

By default, the compiler uses the local `AudioMixin` so the project works without extra packages.

To emit `manim-voiceover` scenes instead:

```powershell
pip install -r requirements-voiceover.txt
$env:MANIMAGENT_VOICEOVER_MODE="manim_voiceover"
python main.py
```

If `MANIMAGENT_VOICEOVER_MODE` is unset, the default is `audio_mixin`.

## Structured Pipeline

The default generation path is now:

```text
storyboard JSON -> scene DSL -> deterministic Manim compiler -> render -> quality report -> assembly manifest
```

The old direct LLM Manim generator remains as a fallback if DSL building or compilation fails.

## Debug A Script

Use `dev_runner.py` to render an existing Manim script without running the LLM pipeline:

```powershell
python dev_runner.py --file projects\example\output\example.py --out dev_output --attempts 1
```

Smoke scripts are available in `smoke_scripts/`:

```powershell
python dev_runner.py --file smoke_scripts\silent_scene.py --out dev_output --attempts 1
python dev_runner.py --file smoke_scripts\audio_scene.py --out dev_output --attempts 1
python dev_runner.py --file smoke_scripts\broken_scene.py --out dev_output --attempts 2
```

## Tests

```powershell
python -m unittest discover -s tests
```
