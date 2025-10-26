from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
import os


class PlannerAgent:
    """
    PlannerAgent
    -------------
    Takes a concept and produces a structured visual explanation plan
    using the modern LangChain v1.x interface.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        self.llm = ChatOpenAI(model=model, temperature=temperature)

        # Load prompt from file
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "planner_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read().strip()

        self.prompt = ChatPromptTemplate.from_template(
            self.prompt_template
        )

    def plan(self, concept: str):
        """Generate a structured story plan for the given concept."""
        chain = self.prompt | self.llm
        response = chain.invoke({"concept": concept}).content

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print("Warning: non-JSON response, returning raw text.")
            return {"concept": concept, "raw_response": response}
