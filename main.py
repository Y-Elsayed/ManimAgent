import os
import json
import shutil
import subprocess
from dotenv import load_dotenv
from agents.planner_agent import PlannerAgent
from agents.critic_agent import CriticAgent
from agents.generator_agent import GeneratorAgent
from agents.aligner_agent import AlignerAgent
from nodes.interpreter_node import InterpreterNode


# ------------------------
# ENVIRONMENT CHECK
# ------------------------
def check_command(cmd):
    return shutil.which(cmd) is not None


def has_amssymb():
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

    if not missing and not has_amssymb():
        print("[Warn] LaTeX found but missing amssymb; trying auto-install...")
        try:
            subprocess.run(["sudo", "tlmgr", "install", "amsfonts", "amsmath", "amssymb"], check=False)
        except Exception:
            pass
    elif has_amssymb():
        print("[OK] LaTeX math packages verified (amssymb found).")

    if missing:
        print("\nSome dependencies are missing:")
        for dep, cmd in missing:
            print(f" - {dep}: {cmd}")
        print("\nInstall them using the above commands, then restart.")
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
    print("Create one at: https://platform.openai.com/api-keys")
    user_key = input("Enter your OpenAI API key: ").strip()
    if not user_key:
        print("No key provided. Exiting.")
        exit(1)

    with open(".env", "w", encoding="utf-8") as f:
        f.write(f"OPENAI_API_KEY={user_key}\n")

    os.environ["OPENAI_API_KEY"] = user_key
    return user_key


# ------------------------
# MODE HANDLING
# ------------------------
def ask_fast_mode():
    print("\nFast Mode skips confirmations and runs automatically.")
    return input("Enable Fast Mode? [y/N]: ").lower().startswith("y")


# ------------------------
# FILE UTILITIES
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


def delete_checkpoint(*files):
    for f in files:
        try:
            os.remove(os.path.join("./checkpoints", f))
            print(f"[Deleted stale checkpoint → {f}]")
        except FileNotFoundError:
            pass


def get_unique_output_dir(base_dir: str, name: str) -> str:
    target = os.path.join(base_dir, name)
    counter = 1
    while os.path.exists(target):
        target = os.path.join(base_dir, f"{name} ({counter})")
        counter += 1
    os.makedirs(target, exist_ok=True)
    return target


def get_save_location(concept_name=None, default="./output", fast=False):
    if fast:
        os.makedirs(default, exist_ok=True)
        base_name = concept_name.replace(" ", "_").lower() if concept_name else "animation"
        return get_unique_output_dir(default, base_name)

    base_path = input(f"\nSave folder (default: {default}): ").strip() or default
    os.makedirs(base_path, exist_ok=True)
    base_name = concept_name.replace(" ", "_").lower() if concept_name else "animation"
    return get_unique_output_dir(base_path, base_name)


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
    aligner = AlignerAgent()
    interpreter = InterpreterNode()

    # Smart refresh if concept changed
    old_plan = load_checkpoint("story_plan.json")
    if old_plan and old_plan.get("concept") != concept:
        print(f"Concept changed from '{old_plan.get('concept')}' → '{concept}'. Resetting checkpoints...")
        delete_checkpoint("refined_story.json", "generation_result.json", "aligned_result.json")

    # Step 1: Planning
    print("\n[1/5] Planning explanation...")
    story_plan = load_checkpoint("story_plan.json")
    if story_plan and not fast_mode:
        use_existing = input("Resume from previous plan? (y/n): ").lower().startswith("y")
        if not use_existing:
            story_plan = None
    if not story_plan:
        story_plan = planner.plan(concept)
        save_checkpoint(story_plan, "story_plan.json")

    # Step 2: Refinement
    refine = True if fast_mode else input("\nRefine with Critic Agent? (y/n): ").lower().startswith("y")
    refined_plan = load_checkpoint("refined_story.json") if refine else story_plan
    if refine and not refined_plan:
        print("\n[2/5] Refining storyboard...")
        refined_plan = critic.critique(story_plan)
        save_checkpoint(refined_plan, "refined_story.json")
    story_to_use = refined_plan or story_plan

    # Step 3: Generation
    print("\n[3/5] Generating Manim script...")
    generation_result = load_checkpoint("generation_result.json")
    regen = not fast_mode and input("Regenerate script from refined story? (y/n): ").lower().startswith("y")
    if regen:
        delete_checkpoint("generation_result.json", "aligned_result.json")
        generation_result = None
    if not generation_result:
        generation_result = generator.generate(story_to_use)
        save_checkpoint(generation_result, "generation_result.json")
    print("Generated script and narration prepared.")

    # Step 4: Alignment
    print("\n[4/5] Aligning narration and visuals...")
    aligned_result = load_checkpoint("aligned_result.json")
    realign = not fast_mode and input("Re-align narration and visuals? (y/n): ").lower().startswith("y")
    if realign:
        delete_checkpoint("aligned_result.json")
        aligned_result = None
    if not aligned_result:
        aligned_result = aligner.align(generation_result)
        save_checkpoint(aligned_result, "aligned_result.json")
    print("Narration and animation timing optimized.")

    # Step 5: Rendering
    run_now = True if fast_mode else input("\nRender animation now? (y/n): ").lower().startswith("y")
    if run_now:
        save_path = get_save_location(concept_name=concept, fast=fast_mode)
        try:
            output_path = interpreter.run(
                code=aligned_result["code"],
                file_name=aligned_result["file_name"],
                scene_narrations=aligned_result.get("scene_narrations", []),
                output_dir=save_path
            )
            print(f"\nRendered output saved at: {output_path}")
        except Exception as e:
            print(f"\n[Error during rendering] {e}")
    else:
        print("Script generated but not rendered.")

    print("\nDone.")


if __name__ == "__main__":
    main()
