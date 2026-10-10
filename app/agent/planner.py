
import json
from typing import Any

from app.llm.ollama_client import OllamaClient


class Planner:
    """Create and validate execution plans for CodeMind."""

    MAX_STEPS = 20
    MAX_RESULTS = 200
    MAX_TIMEOUT = 120

    def __init__(self) -> None:
        self.llm = OllamaClient()

    async def create_plan(self, message: str) -> dict[str, Any]:
        """Ask the local LLM to create a plan for the user request."""

        if not isinstance(message, str) or not message.strip():
            raise ValueError("User message cannot be empty.")

        prompt = f"""
You are the planning engine of CodeMind,
an AI-powered local development environment.

Analyze the user's request and return an executable plan.

AVAILABLE TOOLS AND EXACT ARGUMENTS:

1. list_files
Purpose: List files in the workspace.
Arguments: {{}}
Risk: safe

2. read_file
Purpose: Read a file.
Arguments: {{"file_path": "relative/path/to/file"}}
Risk: safe

3. create_file
Purpose: Create a new, empty file.
Arguments: {{"file_path": "relative/path/to/file"}}
Risk: risky

4. write_file
Purpose: Write content into a file.
Arguments: {{
    "file_path": "relative/path/to/file",
    "content": "content to write"
}}
Risk: risky

5. delete_file
Purpose: Delete a file.
Arguments: {{"file_path": "relative/path/to/file"}}
Risk: risky

6. create_folder
Purpose: Create a folder or directory.
Arguments: {{"folder_path": "relative/path/to/folder"}}
Risk: risky

7. list_folder
Purpose: List items inside a folder.
Arguments: {{"folder_path": "relative/path/to/folder"}}
Use "." for the workspace root.
Risk: safe

8. delete_folder
Purpose: Delete an empty folder.
Arguments: {{"folder_path": "relative/path/to/folder"}}
Risk: risky

9. search_files
Purpose: Search filenames and file extensions.
Arguments: {{
    "query": "filename keyword",
    "extension": ".py",
    "folder_path": ".",
    "limit": 50
}}
query and extension can be empty individually,
but at least one must be provided.
folder_path and limit are optional.
Risk: safe

10. search_content
Purpose: Search for text inside files.
Arguments: {{
    "query": "text to search",
    "folder_path": ".",
    "limit": 50
}}
query is required.
folder_path and limit are optional.
Risk: safe

11. chat
Purpose: Answer a question without workspace operations.
Arguments: {{"message": "user's question"}}
Risk: safe

12. run_command
Purpose: Run a development command inside the workspace.
Arguments: {{
    "command": ["python", "--version"],
    "cwd": ".",
    "timeout": 30
}}
Risk: risky

Supported command examples:
- Python: ["python", "main.py"]
- Python tests: ["python", "-m", "pytest"]
- JavaScript: ["node", "index.js"]
- JavaScript package scripts: ["npm", "run", "dev"]
- TypeScript: ["npx", "tsx", "index.ts"]
- Java source file: ["java", "Main.java"]
- Java compiler: ["javac", "Main.java"]
- Maven: ["mvn", "test"]
- Gradle: ["gradle", "test"]
- C: ["gcc", "main.c", "-o", "main.exe"]
- C++: ["g++", "main.cpp", "-o", "main.exe"]
- C#: ["dotnet", "run"]
- Go: ["go", "run", "main.go"]
- Rust: ["cargo", "run"]
- Git: ["git", "status"]

IMPORTANT RULES:

- Choose only tools listed above.
- Use exact tool names and argument names.
- Creating a folder must use create_folder.
- Creating a file must use create_file.
- File and folder paths must refer to locations inside the workspace.
- Never invent file content or user requirements.
- Never use delete_folder for non-empty folders.
- If the user asks a general question, use chat.
- If multiple actions are required, return steps in order.
- Return only valid JSON, without Markdown or extra explanations.
- Use search_files for filenames and extensions.
- Use search_content for text inside files.
- search_files requires query or extension, or both.
- search_content requires a non-empty query.
- Search tools are read-only and must be marked safe.
- run_command must always be marked risky.
- command must be a non-empty list of strings.
- cwd must be a directory inside the workspace.
- timeout must be an integer between 1 and {self.MAX_TIMEOUT}.
- Never execute a command without user approval.
- Do not assume a language runtime or compiler is installed.
- Do not invent commands or use shell command strings.
- The command must be an argument list, not one combined string.
- CodeMind, not the LLM, determines the final risk level.

OUTPUT FORMAT:

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

USER REQUEST:
{message}
"""

        response = await self.llm.chat(prompt)
        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parse the LLM response and validate its plan."""

        if not isinstance(response, str) or not response.strip():
            raise ValueError("Planner returned an empty response.")

        response = response.strip()

        # Remove Markdown code fences if the model adds them.
        if response.startswith("```"):
            lines = response.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            response = "\n".join(lines).strip()

        try:
            plan = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Planner returned invalid JSON."
            ) from exc

        self._validate_plan(plan)
        return plan

    def _validate_plan(self, plan: dict[str, Any]) -> None:
        """Validate tools, arguments, and canonical risk levels."""

        if not isinstance(plan, dict):
            raise ValueError("Planner output must be an object.")

        intent = plan.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError(
                "Planner output must contain a valid intent."
            )

        steps = plan.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(
                "Planner output must contain a non-empty steps list."
            )

        if len(steps) > self.MAX_STEPS:
            raise ValueError(
                f"A plan cannot contain more than {self.MAX_STEPS} steps."
            )

        # CodeMind defines the required arguments and risk for each tool.
        tool_rules: dict[str, dict[str, Any]] = {
            "list_files": {
                "required": set(),
                "risk": "safe",
            },
            "read_file": {
                "required": {"file_path"},
                "risk": "safe",
            },
            "create_file": {
                "required": {"file_path"},
                "risk": "risky",
            },
            "write_file": {
                "required": {"file_path", "content"},
                "risk": "risky",
            },
            "delete_file": {
                "required": {"file_path"},
                "risk": "risky",
            },
            "create_folder": {
                "required": {"folder_path"},
                "risk": "risky",
            },
            "list_folder": {
                "required": {"folder_path"},
                "risk": "safe",
            },
            "delete_folder": {
                "required": {"folder_path"},
                "risk": "risky",
            },
            "search_files": {
                "required": set(),
                "risk": "safe",
            },
            "search_content": {
                "required": {"query"},
                "risk": "safe",
            },
            "run_command": {
                "required": {"command"},
                "risk": "risky",
            },
            "chat": {
                "required": {"message"},
                "risk": "safe",
            },
        }

        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError(
                    f"Step {index} must be an object."
                )

            tool = step.get("tool")
            if not isinstance(tool, str) or tool not in tool_rules:
                raise ValueError(
                    f"Unknown tool in step {index}: {tool}"
                )

            arguments = step.get("arguments")
            if not isinstance(arguments, dict):
                raise ValueError(
                    f"Arguments in step {index} must be an object."
                )

            rules = tool_rules[tool]
            required = rules["required"]
            missing = required - arguments.keys()

            if missing:
                raise ValueError(
                    f"Tool '{tool}' is missing required arguments: "
                    f"{', '.join(sorted(missing))}"
                )

            # run_command needs list, string, and integer validation.
            if tool == "run_command":
                command = arguments["command"]

                if (
                    not isinstance(command, list)
                    or not command
                    or not all(
                        isinstance(arg, str) and arg.strip()
                        for arg in command
                    )
                ):
                    raise ValueError(
                        "'command' must be a non-empty list of strings."
                    )

                cwd = arguments.get("cwd", ".")
                if not isinstance(cwd, str) or not cwd.strip():
                    raise ValueError(
                        "'cwd' must be a non-empty string."
                    )

                timeout = arguments.get("timeout", 30)
                if (
                    type(timeout) is not int
                    or not 1 <= timeout <= self.MAX_TIMEOUT
                ):
                    raise ValueError(
                        f"'timeout' must be an integer between "
                        f"1 and {self.MAX_TIMEOUT}."
                    )

                arguments.setdefault("cwd", ".")
                arguments.setdefault("timeout", 30)

            else:
                # Validate required string arguments for other tools.
                for key in required:
                    value = arguments[key]

                    if (
                        not isinstance(value, str)
                        or not value.strip()
                    ):
                        raise ValueError(
                            f"'{key}' for tool '{tool}' must be "
                            "a non-empty string."
                        )

            # Validate search_files arguments.
            if tool == "search_files":
                query = arguments.get("query", "")
                extension = arguments.get("extension", "")

                if not isinstance(query, str):
                    raise ValueError(
                        "search_files query must be a string."
                    )

                if not isinstance(extension, str):
                    raise ValueError(
                        "search_files extension must be a string."
                    )

                if not query.strip() and not extension.strip():
                    raise ValueError(
                        "search_files requires query or extension."
                    )

            # Validate optional search arguments.
            if tool in {"search_files", "search_content"}:
                folder_path = arguments.get("folder_path", ".")
                limit = arguments.get("limit", 50)

                if (
                    not isinstance(folder_path, str)
                    or not folder_path.strip()
                ):
                    raise ValueError(
                        "folder_path must be a non-empty string."
                    )

                if (
                    type(limit) is not int
                    or not 1 <= limit <= self.MAX_RESULTS
                ):
                    raise ValueError(
                        f"limit must be an integer between "
                        f"1 and {self.MAX_RESULTS}."
                    )

                arguments.setdefault("folder_path", ".")
                arguments.setdefault("limit", 50)

                if tool == "search_files":
                    arguments.setdefault("query", "")
                    arguments.setdefault("extension", "")

            # Never trust the LLM to classify an action's risk.
            step["risk"] = rules["risk"]
