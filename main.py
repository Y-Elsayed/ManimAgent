import os
import re
import json
import shutil
from dotenv import load_dotenv

# Core agents
from agents.planner_agent import PlannerAgent
from agents.generator_agent import GeneratorAgent
from nodes.syntax_guard_node import SyntaxGuardNode
from nodes.interpreter_node import InterpreterNode


# ----------------------------
# Environment & Utilities
# ----------------------------

def check_command(cmd):
    """Check if a command is available on the system."""
    return shutil.which(cmd) is not None


def check_environment():
    """Verify required dependencies are installed."""
    print("Checking environment...")
    deps = {
        "manim": "pip install manim",
        "ffmpeg": "brew install ffmpeg" if os.name == "posix" else "sudo apt install ffmpeg -y",
        "latex": "sudo apt install texlive-latex-base -y"
    }

    for dep, hint in deps.items():
        found = check_command(dep) or (dep == "latex" and check_command("pdflatex"))
        if found:
            print(f"[OK] {dep} found.")
        else:
            print(f"[Missing] {dep} not found. Install using: {hint}")
    print("Environment check done.\n")


def ensure_api_key():
    """Load or request an OpenAI API key."""
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if key and key.strip():
        return key

    print("OpenAI API key not found.")
    key = input("Enter your OpenAI API key: ").strip()
    with open(".env", "w", encoding="utf-8") as f:
        f.write(f"OPENAI_API_KEY={key}\n")
    os.environ["OPENAI_API_KEY"] = key
    return key


# ----------------------------
# Project Directory Management
# ----------------------------

def safe_project_name(concept: str) -> str:
    """Generate a unique, filesystem-safe project path under 'projects/'."""
    base_name = re.sub(r"[^a-zA-Z0-9_]+", "_", concept.strip().lower()).strip("_")
    if not base_name:
        base_name = "project"

    projects_root = os.path.join(os.getcwd(), "projects")
    os.makedirs(projects_root, exist_ok=True)

    project_path = os.path.join(projects_root, base_name)
    counter = 1
    while os.path.exists(project_path):
        project_path = os.path.join(projects_root, f"{base_name}_{counter}")
        counter += 1

    return project_path


def ensure_dirs(project_path: str):
    """Create necessary subfolders for the given project path."""
    out_dir = os.path.join(project_path, "output")
    dbg_dir = os.path.join(project_path, "debug")
    media_dir = os.path.join(project_path, "media")
    final_dir = os.path.join(project_path, "final")

    for d in [out_dir, dbg_dir, media_dir, final_dir]:
        os.makedirs(d, exist_ok=True)

    return out_dir, dbg_dir, media_dir, final_dir


def save_debug(dbg_dir: str, name: str, data):
    """Save intermediate JSON/text debug files."""
    path = os.path.join(dbg_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, (dict, list)):
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            f.write(str(data))
    return path


def get_user_preferences():
    """Get user preferences for generation."""
    print("\n--- Configuration ---")
    
    # TTS option
    use_tts = input("Enable text-to-speech narration? (y/n, default=y): ").strip().lower()
    use_tts = use_tts != 'n'
    
    if use_tts:
        print("\nAvailable voices (gpt-4o-mini-tts):")
        print("  1. onyx (deep male) - recommended")
        print("  2. echo (clear male)")
        print("  3. fable (expressive male)")
        print("  4. ash (mature male)")
        print("  5. alloy (neutral)")
        print("  6. ballad (calm female)")
        print("  7. coral (warm female)")
        print("  8. shimmer (gentle female)")
        print("  9. nova (energetic female)")
        
        voice_choice = input("Choose voice (1-9, default=1): ").strip()
        voice_map = {
            "1": "onyx", "2": "echo", "3": "fable", "4": "ash",
            "5": "alloy", "6": "ballad", "7": "coral", 
            "8": "shimmer", "9": "nova"
        }
        tts_voice = voice_map.get(voice_choice, "onyx")
        print(f"Using voice: {tts_voice}")
    else:
        tts_voice = None
        print("TTS disabled - videos will be silent")
    
    print()
    return {
        "use_tts": use_tts,
        "tts_voice": tts_voice
    }


# ----------------------------
# Main Orchestration
# ----------------------------

def main():
    check_environment()
    ensure_api_key()

    print("\n--- Manim Visualizer Agent ---\n")
    concept = input("Enter a concept to visualize: ").strip()
    if not concept:
        print("No concept provided. Exiting.")
        return

    # Get user preferences
    prefs = get_user_preferences()

    # Generate unique project directory
    project_path = safe_project_name(concept)
    project_name = os.path.basename(project_path)

    output_dir, debug_dir, media_dir, final_dir = ensure_dirs(project_path)

    # Initialize agents
    planner = PlannerAgent()
    generator = GeneratorAgent(use_tts=prefs["use_tts"], tts_voice=prefs["tts_voice"])
    syntax_guard = SyntaxGuardNode(
        enable_audio_mixin=prefs["use_tts"],
        replace_play_calls=False  # Generator handles this
    )
    interpreter = InterpreterNode()

    # ----------------------------
    # Step 1 – Planning explanation
    # ----------------------------
    print("\n[1/4] Planning explanation...")
    story_plan = planner.plan(concept)
    save_debug(debug_dir, "story_plan.json", story_plan)

    # ----------------------------
    # Step 2 – Generating Manim script
    # ----------------------------
    print("\n[2/4] Generating Manim script...")
    generation_result = generator.generate(story_plan)
    save_debug(debug_dir, "generation_result.json", generation_result)

    # ----------------------------
    # Step 3 – Syntax validation & code sanitization
    # ----------------------------
    print("\n[3/4] Running syntax validation and code sanitation...")
    sanitized = syntax_guard.sanitize(generation_result["code"])
    sanitized_code = sanitized["code"]
    diagnostics = sanitized["diagnostics"]
    save_debug(debug_dir, "syntax_diagnostics.json", diagnostics)
    save_debug(debug_dir, "final_code.py", sanitized_code)

    print("\n[Diagnostics]")
    for k, v in diagnostics.items():
        print(f"  - {k}: {v}")

    # ----------------------------
    # Step 4 – Rendering final animation
    # ----------------------------
    print("\n[4/4] Rendering animation...")
    try:
        result = interpreter.run(
            code=sanitized_code,
            file_name=generation_result.get("file_name", project_name),
            output_dir=output_dir,
            media_dir=media_dir,
            final_dir=final_dir,
        )
        
        if result:
            print(f"\n[Success] Rendered scenes: {result['scenes']}")
            
            # Show file locations
            if result.get("organized"):
                org = result["organized"]
                print(f"\n📁 Project Directory: {project_path}")
                print(f"   ├─ Debug files: {debug_dir}")
                print(f"   ├─ Python script: {result['script_path']}")
                print(f"   ├─ Individual scenes: {output_dir}/")
                if org.get("merged_video"):
                    print(f"   └─ 🎬 Final video: {org['merged_video']}")
        else:
            print("\n[Error] Rendering failed or no scenes found.")
            
    except Exception as e:
        print(f"\n[Render error] {e}")
        import traceback
        traceback.print_exc()

    print(f"\nProject saved under: {project_path}")
    print("\nAll steps completed successfully.")


if __name__ == "__main__":
    main()