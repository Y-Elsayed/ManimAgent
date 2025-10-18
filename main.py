from agents.planner_agent import PlannerAgent
from agents.critic_agent import CriticAgent
from agents.generator_agent import GeneratorAgent
from nodes.interpreter_node import InterpreterNode
import os


def get_save_location():
    while True:
        save_path = input("\nSave folder (default: ./output): ").strip()
        if not save_path:
            save_path = "./output"

        if os.path.isdir(save_path):
            return os.path.abspath(save_path)

        if os.path.exists(save_path) and not os.path.isdir(save_path):
            print(f"'{save_path}' exists but is not a directory.")
            continue

        create = input(f"Directory '{save_path}' not found. Create it? (y/n): ").lower().startswith("y")
        if create:
            try:
                os.makedirs(save_path, exist_ok=True)
                return os.path.abspath(save_path)
            except Exception as e:
                print(f"Error creating directory: {e}")
        else:
            print("Enter a valid directory path.")


def main():
    print("Manim Visualizer Agent")
    print("----------------------")

    concept = input("Enter a concept to visualize: ").strip()
    if not concept:
        print("No concept provided. Exiting.")
        return

    planner = PlannerAgent()
    critic = CriticAgent()
    generator = GeneratorAgent()
    interpreter = InterpreterNode()

    print("\n[1/4] Planning explanation...")
    story_plan = planner.plan(concept)
    print("\nStory Plan:")
    print(story_plan)

    refine = input("\nReview and refine with Critic Agent? (y/n): ").lower().startswith("y")
    if refine:
        print("\n[2/4] Refining storyboard...")
        story_plan = critic.critique(story_plan)
        print("\nRefined Storyboard:")
        print(story_plan)

    print("\n[3/4] Generating Manim script...")
    result = generator.generate(story_plan)
    print("\nGenerated script and narration prepared.")

    run_now = input("\nRender the animation now? (y/n): ").lower().startswith("y")
    if run_now:
        save_path = get_save_location()
        output_path = interpreter.run(
            code=result["code"],
            file_name=result["file_name"],
            scene_narrations=result.get("scene_narrations", []),
            output_dir=save_path
        )
        print(f"\nRendered output saved at: {output_path}")
    else:
        print("\nScript generated but not rendered.")

    print("\nDone.")


if __name__ == "__main__":
    main()
