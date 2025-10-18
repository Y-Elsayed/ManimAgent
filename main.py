from agents.planner_agent import PlannerAgent
from agents.generator_agent import GeneratorAgent
from nodes.python_interpreter_node import InterpreterNode
import os




def get_save_location():
    """prompt the user for a directory to save the animation, verify or create it."""
    while True:
        save_path = input("\nEnter a folder path to save the animation (default: ./output): ").strip()
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
            print("Please enter a valid directory path.")


def main():
    print("Manim Visualizer Agent")
    print("-------------------------")

    # initial input
    concept = input("Enter a concept you want me to visualize for you: ").strip()
    if not concept:
        print("No concept provided. Exiting.")
        return

    # Initialize agents
    planner = PlannerAgent()
    generator = GeneratorAgent()
    interpreter = InterpreterNode()

    # story planning
    print("\n [1/3] Planning the explanation...")
    story_plan = planner.plan(concept)
    print("\nGenerated Story Plan:")
    print(story_plan)

    # generating the Manim code
    print("\n[2/3] Generating Manim code...")
    manim_code = generator.generate(story_plan)
    print("\nGenerated Manim Script:")
    print(manim_code[:500] + "..." if len(manim_code) > 500 else manim_code)

    # ask if the user wants to execute it
    run_now = input("\nRun the animation now? (y/n): ").lower().startswith("y")
    if run_now:
        print("\n[3/3] Running Manim...")
        save_path = get_save_location()
        output_path = interpreter.run(manim_code, output_dir=save_path)
        print(f"\nAnimation rendered: {output_path}")
    else:
        print("\nAnimation code generated but not executed.")

    print("\nDone!")


if __name__ == "__main__":
    main()
