# ManimAgent

ManimAgent is a CLI pipeline that turns a scientific or mathematical topic into a narrated Manim video.

Current flow:

1. Plan a storyboard with an LLM.
2. Generate Manim Python code for every storyboard scene.
3. Sanitize and validate generated code.
4. Render each scene with Manim.
5. Repair failed renders with an LLM fixer when possible.
6. Copy individual scene videos and merge a final video.

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
  output/
  media/
  final/
```

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
