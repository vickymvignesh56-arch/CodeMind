from pydantic import InstanceOf
import resampy
from app.llm.ollama_client import OllamaClient
import json
class Planner:
    def __init__(self)-> None:
        self.llm=OllamaClient()
    async def create_plan(self, message: str) -> dict:
        prompt = f"""
You are the planning engine of CodeMind, an AI-powered
local development environment.

Your job is to analyze the user's request and create a
structured execution plan.

Available tools:

1. list_files
   - List files inside the workspace.

2. read_file
   - Read the contents of a file.

3. create_file
   - Create a new file.

4. write_file
   - Write content into a file.

5. delete_file
   - Delete a file.

6. chat
   - Answer the user without using a tool.

Rules:

- Choose only the tools listed above.
- Never invent a tool.
- If the request requires multiple actions, return multiple steps.
- Keep each step clear and executable.
- File operations must use relative paths.
- Never access files outside the workspace.
- Destructive operations such as delete_file must be marked as risky.
- Return ONLY valid JSON.
- Do not add markdown.
- Do not add explanations outside the JSON.

JSON format:

{{
    "intent": "short description of the user's intent",
    "steps": [
        {{
            "tool": "tool_name",
            "arguments": {{}},
            "risk": "safe"
        }}
    ]
}}
User request:
{message}
"""
        response = await self.llm.chat(prompt)
        return self._parse_response(response)

    def _parse_response(self,response: str) -> dict:
        response = response.strip()
        if response.startswith("```"):
            response = response.replace("```json", "")
            response = response.replace("```", "")
            response = response.strip()
        try:
             plan = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Planner returned invalid JSON."
            ) from exc
        self._validate_plan(plan)
        return plan

    def _validate_plan(self, plan: dict) -> None:
        if not isinstance(plan, dict):
            raise ValueError("Planner output must be an object.")

        if "intent" not in plan:
            raise ValueError("Planner output missing 'intent'.")

        if "steps" not in plan:
            raise ValueError("Planner output missing 'steps'.")
        if not isinstance(plan['steps'],list):
            raise ValueError("'steps' must be a list.")
        allowed_tools = {
            "list_files",
            "read_file",
            "create_file",
            "write_file",
            "delete_file",
            "chat",
        }
        allowed_risks = {
            "safe",
            "risky",
        }
        for step in plan["steps"]:
            if not isinstance(step, dict):
                raise ValueError("Each step must be an object.")
            tool = step.get("tool")
            if tool not in allowed_tools:
                raise ValueError(
                    f"Unknown tool requested: {tool}"
                )
            if "arguments" not in step:
                raise ValueError(
                    f"Missing arguments for tool: {tool}"
                )

            risk = step.get("risk")
            if risk not in allowed_risks:
                raise ValueError(
                    f"Invalid risk level: {risk}"
                )