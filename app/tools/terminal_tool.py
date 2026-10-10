import asyncio
from pathlib import Path
from typing import Any
class TerminalTool:
    MAX_TIMEOUT = 180
    MAX_OUTPUT_LENGTH = 20_000

    ALLOWED_COMMANDS = {
    "python", "python3", "pytest", "ruff", "mypy",
    "node", "npm", "npx", "tsc", "tsx", "ts-node",
    "java", "javac", "mvn", "gradle",
    "gcc", "g++",
    "dotnet",
    "go",
    "cargo", "rustc",
    "git",
    }

    def __init__(self, workspace: str) -> None:
        self.workspace = Path(workspace).resolve()

        if not self.workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {self.workspace}"
            )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace is not a directory: {self.workspace}"
            )

    def _validate_command(self, command: list[str]) -> None:
        if not isinstance(command, list) or not command:
            raise ValueError(
                "Command must be a non-empty list of strings."
            )

        if not all(isinstance(arg, str) for arg in command):
            raise ValueError(
                "Every command argument must be a string."
            )

        if not command[0].strip():
            raise ValueError("Executable cannot be empty.")

        if any("\x00" in arg for arg in command):
            raise ValueError(
                "Command arguments cannot contain null bytes."
            )

        executable = Path(command[0]).name.lower()

        if executable.endswith(".exe"):
            executable = executable[:-4]

        if executable not in self.ALLOWED_COMMANDS:
            raise PermissionError(
                f"Command is not allowed: {executable}"
            )

    def _resolve_cwd(self, cwd: str = ".") -> Path:

        if not isinstance(cwd, str) or not cwd.strip():
            raise ValueError(
                "A valid working directory is required."
            )

        requested = Path(cwd)

        if requested.is_absolute():
            resolved = requested.resolve()
        else:
            resolved = (self.workspace / requested).resolve()

        try:
            resolved.relative_to(self.workspace)
        except ValueError as exc:
            raise PermissionError(
                "Commands cannot run outside the workspace."
            ) from exc

        if not resolved.exists():
            raise FileNotFoundError(
                f"Working directory not found: {cwd}"
            )

        if not resolved.is_dir():
            raise NotADirectoryError(
                f"Working path is not a directory: {cwd}"
            )

        return resolved

    @staticmethod
    def _decode_output(data: bytes) -> str:
        return data.decode("utf-8", errors="replace")

    def _build_result(
        self,
        command: list[str],
        cwd: Path,
        return_code: int | None,
        stdout: str,
        stderr: str,
        status: str,
    ) -> dict[str, Any]:
        truncated = (
            len(stdout) > self.MAX_OUTPUT_LENGTH
            or len(stderr) > self.MAX_OUTPUT_LENGTH
        )

        return {
            "status": status,
            "command": command,
            "cwd": str(cwd),
            "return_code": return_code,
            "stdout": stdout[:self.MAX_OUTPUT_LENGTH],
            "stderr": stderr[:self.MAX_OUTPUT_LENGTH],
            "output_truncated": truncated,
        }

    async def run_command(
        self,
        command: list[str],
        cwd: str = ".",
        timeout: int = 30,
    ) -> dict[str, Any]:
        self._validate_command(command)
        if (
            type(timeout) is not int
            or not 1 <= timeout <= self.MAX_TIMEOUT
        ):
            raise ValueError(
                f"timeout must be between 1 and "
                f"{self.MAX_TIMEOUT} seconds."
            )

        working_directory = self._resolve_cwd(cwd)

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(working_directory),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            stdout = self._decode_output(stdout_bytes)
            stderr = self._decode_output(stderr_bytes)

            status = (
                "success"
                if process.returncode == 0
                else "failed"
            )

            return self._build_result(
                command=command,
                cwd=working_directory,
                return_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                status=status,
            )

        except asyncio.TimeoutError:
            process.kill()

            stdout_bytes, stderr_bytes = await process.communicate()

            result = self._build_result(
                command=command,
                cwd=working_directory,
                return_code=process.returncode,
                stdout=self._decode_output(stdout_bytes),
                stderr=self._decode_output(stderr_bytes),
                status="timeout",
            )

            result["timeout_seconds"] = timeout
            return result
