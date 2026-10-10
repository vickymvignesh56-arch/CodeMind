from pathlib import Path
from typing import Any


class FolderTool:
    """Handle folder operations inside a workspace."""

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

    def _resolve_path(self, folder_path: str) -> Path:
        """Resolve a path and reject paths outside the workspace."""

        if not isinstance(folder_path, str) or not folder_path.strip():
            raise ValueError("A valid folder path is required.")

        path = Path(folder_path)

        if path.is_absolute():
            resolved_path = path.resolve()
        else:
            resolved_path = (self.workspace / path).resolve()

        try:
            resolved_path.relative_to(self.workspace)
        except ValueError as exc:
            raise PermissionError(
                "Access outside the workspace is not allowed."
            ) from exc

        return resolved_path

    def create_folder(self, folder_path: str) -> dict[str, Any]:
        """Create a folder."""

        path = self._resolve_path(folder_path)

        if path.exists():
            if path.is_dir():
                return {
                    "status": "already_exists",
                    "path": str(path.relative_to(self.workspace)),
                }

            raise FileExistsError(
                f"A file already exists at: {folder_path}"
            )

        path.mkdir(parents=True, exist_ok=False)

        return {
            "status": "success",
            "action": "create_folder",
            "path": str(path.relative_to(self.workspace)),
        }

    def list_folder(self, folder_path: str = ".") -> dict[str, Any]:
        """List files and subfolders."""

        path = self._resolve_path(folder_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder_path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Not a folder: {folder_path}"
            )

        items = []

        for item in sorted(
            path.iterdir(),
            key=lambda entry: entry.name.lower(),
        ):
            items.append({
                "name": item.name,
                "type": "folder" if item.is_dir() else "file",
            })

        return {
            "status": "success",
            "path": str(path.relative_to(self.workspace)) or ".",
            "count": len(items),
            "items": items,
        }

    def delete_folder(self, folder_path: str) -> dict[str, Any]:
        """Delete an empty folder only."""

        path = self._resolve_path(folder_path)

        if path == self.workspace:
            raise PermissionError(
                "Deleting the workspace root is not allowed."
            )

        if not path.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder_path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Not a folder: {folder_path}"
            )

        path.rmdir()

        return {
            "status": "success",
            "action": "delete_folder",
            "path": str(path.relative_to(self.workspace)),
        }