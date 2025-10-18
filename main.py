import os
import json
import shutil
import subprocess
from dotenv import load_dotenv
from agents.planner_agent import PlannerAgent
from agents.critic_agent import CriticAgent
from agents.generator_agent import GeneratorAgent
from nodes.interpreter_node import InterpreterNode


# ------------------------
# ENVIRONMENT CHECK
# ------------------------
def check_command(cmd):
    """Return True if command exists."""
    return shutil.which(cmd) is not None


def has_amssymb():
    """Return True if amssymb.sty exists in LaTeX tree."""
    try:
        result = subprocess.run(
            ["kpsewhich", "amssymb.sty"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def check_environment():
    """Verify system dependencies. Ask user to fix missing ones before continuing."""
    print(f"Checking environment on {os.uname().sysname}...")

    deps = {
        "manim": "pip install manim",
        "ffmpeg": "brew install ffmpeg" if os.uname().sysname == "Darwin" else "sudo apt install ffmpeg -y",
        "latex": (
            "brew install --cask basictex && "
            "sudo tlmgr update --self && "
            "sudo tlmgr install standalone preview xcolor amsmath amssymb geometry hyperref"
        ),
    }

    missing = []
    for dep, install_hint in deps.items():
        found = check_command(dep)
        if dep == "latex":
            found = found or check_command("pdflatex")
        if found:
            print(f"[OK] {dep} found.")
        else:
            print(f"[Missing] {dep} not found.")
            missing.append((dep, install_hint))

    # Check amssymb explicitly (even if latex present)
    if not missing and not has_amssymb():
        print("[Warn] LaTeX found but math symbol packages (amssymb) are missing.")
        print("Attempting automatic fix...")
        try:
            subprocess.run(
                ["sudo", "tlmgr", "install", "amsfonts", "amsmath", "amssymb"],
                check=False
            )
        except Exception:
            pass
        if not has_amssymb():
            print("Still missing amssymb, but it may already exist under amsfonts — continuing safely.")
        else:
            print("[OK] amssymb verified.")
    elif has_amssymb():
        print("[OK] LaTeX math packages verified (amssymb found).")

    if missing:
        print("\nSome dependencies are missing:")
        for dep, cmd in missing:
            print(f" - {dep}: {cmd}")

        print("\nYou can install them manually using the above commands.")
        print("Your progress will NOT be lost — checkpoints are saved inside your project folder.")
        print("After installing, restart the program. It will resume from the last saved checkpoint.")
        exit(1)

    print("All dependencies found. Continuing...\n")


# ------------------------
# API KEY HANDLING
# ------------------------
def ensure_api_key():
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if key and key.strip():
        return key

    print("\n--- OpenAI API Key Required ---")
    print("You can create one here: https://platform.openai.com/api-keys")
    print("\nTwo ways to set it up:")
    print("1. Create a '.env' file in this folder containing:")
    print("     OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("2. Or, enter your key below.")

    user_key = input("\nEnter your OpenAI API key: ").strip()
    if not user_key:
        print("No key provided. Exiting.")
        exit(1)

    with open(".env", "w", encoding="utf-8") as f:
        f.write(f"OPENAI_API_KEY={user_key}\n")

    os.environ["OPENAI_API_KEY"] = user_key
    print("API key saved to .env.")
    return user_key


# ------------------------
# FAST MODE HANDLING
# ------------------------
def ask_fast_mode():
    print("\nFast Mode determines how interactive this session is.")
    print(" - In Fast Mode: the system skips confirmations and runs automatically.")
    print(" - In Normal Mode: you’ll review each step manually.")
    return input("Enable Fast Mode? [y/N]: ").lower().startswith("y")


# ------------------------
# FILE HANDLING
# ------------------------
def save_checkpoint(data, filename, folder="./checkpoints"):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, (dict, list)):
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            f.write(str(data))
    print(f"[Checkpoint saved → {path}]")
    return path


def load_checkpoint(filename, folder="./checkpoints"):
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                f.seek(0)
                return f.read()
    return None


def get_unique_output_dir(base_dir: str, name: str) -> str:
    target_dir = os.path.join(base_dir, name)
    counter = 1
    while os.path.exists(target_dir):
        target_dir = os.path.join(base_dir, f"{name} ({counter})")
        counter += 1
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def get_save_location(concept_name=None, default="./output", fast=False):
    if fast:
        os.makedirs(default, exist_ok=True)
        base_name = concept_name.replace(" ", "_").lower() if concept_name else "animation"
        return get_unique_output_dir(default, base_name)

    while True:
        base_path = input(f"\nSave folder (default: {default}): ").strip()
        if not base_path:
            base_path = default
        if not os.path.exists(base_path):
            create = input(f"Directory '{base_path}' not found. Create it? (y/n): ").lower().startswith("y")
            if not create:
                print("Please enter a valid directory.")
                continue
            os.makedirs(base_path, exist_ok=True)
        base_name = concept_name.replace(" ", "_").lower() if concept_name else "animation"
        unique_dir = get_unique_output_dir(base_path, base_name)
        print(f"[Output Directory → {unique_dir}]")
        return unique_dir


# ------------------------
# MAIN PIPELINE
# ------------------------
def main():
    check_environment()
    ensure_api_key()

    print("Manim Visualizer Agent")
    print("----------------------")

    fast_mode = ask_fast_mode()
    concept = input("Enter a concept to visualize: ").strip()
    if not concept:
        print("No concept provided. Exiting.")
        return

    planner = PlannerAgent()
    critic = CriticAgent()
    generator = GeneratorAgent()
    interpreter = InterpreterNode()

    # Step 1: Planning
    print("\n[1/4] Planning explanation...")
    story_plan = load_checkpoint("story_plan.json")
    if story_plan and not fast_mode:
        use_existing = input("A previous story plan was found. Resume from it? (y/n): ").lower().startswith("y")
        if not use_existing:
            story_plan = None
    if not story_plan:
        story_plan = planner.plan(concept)
        save_checkpoint(story_plan, "story_plan.json")
    if not fast_mode:
        print("\nStory Plan:")
        print(story_plan)

    # Step 2: Refinement
    refine = True if fast_mode else input("\nReview and refine with Critic Agent? (y/n): ").lower().startswith("y")
    refined_plan = load_checkpoint("refined_story.json") if refine else story_plan
    if refine and not refined_plan:
        print("\n[2/4] Refining storyboard...")
        refined_plan = critic.critique(story_plan)
        save_checkpoint(refined_plan, "refined_story.json")
    story_to_use = refined_plan or story_plan
    if not fast_mode:
        print("\nRefined Storyboard:")
        print(story_to_use)

    # Step 3: Generation
    print("\n[3/4] Generating Manim script...")
    generation_result = load_checkpoint("generation_result.json")
    if not generation_result:
        generation_result = generator.generate(story_to_use)
        save_checkpoint(generation_result, "generation_result.json")
    print("\nGenerated script and narration prepared.")

    # Step 4: Rendering
    run_now = True if fast_mode else input("\nRender the animation now? (y/n): ").lower().startswith("y")
    if run_now:
        save_path = get_save_location(concept_name=concept, fast=fast_mode)
        try:
            output_path = interpreter.run(
                code=generation_result["code"],
                file_name=generation_result["file_name"],
                scene_narrations=generation_result.get("scene_narrations", []),
                output_dir=save_path
            )
            print(f"\nRendered output saved at: {output_path}")
        except Exception as e:
            print(f"\n[Error during rendering] {e}")
    else:
        print("\nScript generated but not rendered.")

    print("\nDone.")


if __name__ == "__main__":
    main()
