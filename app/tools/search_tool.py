
import os
from pathlib import Path
from typing import Any


class SearchTool:
    """Search files and text inside a workspace."""

    IGNORED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".idea",
        ".vscode",
    }

    MAX_FILE_SIZE = 1_000_000
    MAX_RESULTS = 200

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

    def _resolve_path(self, path: str = ".") -> Path:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("A valid path is required.")

        target = Path(path)

        if target.is_absolute():
            resolved = target.resolve()
        else:
            resolved = (self.workspace / target).resolve()

        try:
            resolved.relative_to(self.workspace)
        except ValueError as exc:
            raise PermissionError(
                "Access outside the workspace is not allowed."
            ) from exc

        return resolved

    def _is_ignored(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.workspace)
        except ValueError:
            return True

        return any(
            part in self.IGNORED_DIRS
            for part in relative.parts
        )

    def search_files(
        self,
        query: str = "",
        extension: str = "",
        folder_path: str = ".",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search files by filename and extension."""

        if not query.strip() and not extension.strip():
            raise ValueError(
                "Provide a filename query or file extension."
            )

        if not 1 <= limit <= self.MAX_RESULTS:
            raise ValueError(
                f"limit must be between 1 and {self.MAX_RESULTS}."
            )

        root = self._resolve_path(folder_path)

        if not root.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder_path}"
            )

        if not root.is_dir():
            raise NotADirectoryError(
                f"Not a folder: {folder_path}"
            )

        extension = extension.strip().lower()

        if extension and not extension.startswith("."):
            extension = "." + extension

        results = []

        for current, dirs, files in os.walk(root):
            current_path = Path(current)

            dirs[:] = [
                name
                for name in dirs
                if name not in self.IGNORED_DIRS
                and not (current_path / name).is_symlink()
            ]

            for filename in files:
                path = current_path / filename

                if path.is_symlink() or self._is_ignored(path):
                    continue

                if query and query.casefold() not in filename.casefold():
                    continue

                if extension and path.suffix.lower() != extension:
                    continue

                results.append({
                    "name": filename,
                    "path": path.relative_to(
                        self.workspace
                    ).as_posix(),
                    "extension": path.suffix.lower(),
                    "type": "file",
                })

                if len(results) >= limit:
                    return {
                        "status": "success",
                        "search_type": "filename",
                        "count": len(results),
                        "truncated": True,
                        "results": results,
                    }

        return {
            "status": "success",
            "search_type": "filename",
            "count": len(results),
            "truncated": False,
            "results": results,
        }

    def search_content(
        self,
        query: str,
        folder_path: str = ".",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search for text inside readable files."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search text cannot be empty.")

        if not 1 <= limit <= self.MAX_RESULTS:
            raise ValueError(
                f"limit must be between 1 and {self.MAX_RESULTS}."
            )

        root = self._resolve_path(folder_path)

        if not root.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder_path}"
            )

        if not root.is_dir():
            raise NotADirectoryError(
                f"Not a folder: {folder_path}"
            )

        results = []
        query_lower = query.casefold()
        skipped_large_files = 0

        for current, dirs, files in os.walk(root):
            current_path = Path(current)

            dirs[:] = [
                name
                for name in dirs
                if name not in self.IGNORED_DIRS
                and not (current_path / name).is_symlink()
            ]

            for filename in files:
                path = current_path / filename

                if path.is_symlink() or self._is_ignored(path):
                    continue

                try:
                    if path.stat().st_size > self.MAX_FILE_SIZE:
                        skipped_large_files += 1
                        continue

                    content = path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                except OSError:
                    continue

                for line_number, line in enumerate(
                    content.splitlines(),
                    start=1,
                ):
                    if query_lower in line.casefold():
                        results.append({
                            "path": path.relative_to(
                                self.workspace
                            ).as_posix(),
                            "line": line_number,
                            "text": line.strip()[:500],
                        })

                        if len(results) >= limit:
                            return {
                                "status": "success",
                                "search_type": "content",
                                "count": len(results),
                                "truncated": True,
                                "skipped_large_files": skipped_large_files,
                                "results": results,
                            }

        return {
            "status": "success",
            "search_type": "content",
            "count": len(results),
            "truncated": False,
            "skipped_large_files": skipped_large_files,
            "results": results,
        }
