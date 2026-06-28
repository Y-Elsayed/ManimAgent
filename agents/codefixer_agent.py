import os
import re


class CodeFixerAgent:
    """
    Fixes syntax or runtime errors in generated Manim code.
    Receives the code + error trace and returns a corrected full script.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2):
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate

        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "codefixer_prompt.txt"
        )
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_text = f.read().strip()

        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_template(self.prompt_text)

    def fix_code(self, code: str, error: str) -> str:
        """Return a fixed version of the code given an error trace."""
        chain = self.prompt | self.llm
        try:
            response = chain.invoke({"code": code, "error": error}).content.strip()
        except Exception as e:
            print(f"[CodeFixerAgent] LLM call failed: {e}")
            return code

        fence = re.search(r"```(?:python)?\s*([\s\S]*?)```", response)
        if fence:
            response = fence.group(1)
        
        return response.strip()
