import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class CriticAgent:
    """
    CriticAgent
    ------------
    Evaluates and refines storyboards created by the PlannerAgent
    to ensure the explanations are clear, deep enough, and well-structured.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.5):
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "critic_prompt.txt"
        )
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_text = f.read()

        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_template(self.prompt_text)

    def critique(self, story_plan: dict) -> dict:
        """Review and refine the storyboard JSON from the PlannerAgent."""
        plan_json = json.dumps(story_plan, indent=2)
        chain = self.prompt | self.llm
        response = chain.invoke({"story_plan": plan_json}).content

        try:
            refined_plan = json.loads(response)
        except json.JSONDecodeError:
            print("Warning: Response not valid JSON; returning original plan with feedback text.")
            refined_plan = story_plan
            refined_plan["critic_feedback"] = response

        return refined_plan
