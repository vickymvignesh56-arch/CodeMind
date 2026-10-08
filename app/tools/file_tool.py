from pathlib  import Path

class FileTool:
    def  __init__(self, workspace: str)-> None:
        self.workspace = Path(workspace).resolve()

    def list_files(self)-> list[str]:
        files=[]
        for path in self.workspace.rglob("*"):
            if path.is_file():
                relative_path = path.relative_to(self.workspace)
                files.append(str(relative_path))
        return files
    def read_file(self,file_path:str)-> str:
        path=self._safe_path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        return path.read_text(encoding="utf-8")

    def create_file(self, file_path:str)->str:
        path = self._safe_path(file_path)
        if path.exists():
            raise FileExistsError(f"File already exists: {file_path}")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.touch()
        return f"File created: {file_path}"

    def write_file(self,file_path:str,content:str)-> str:
        path = self._safe_path(file_path)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content,encoding="utf-8")
        return f"File written: {file_path}"

    def delete_file(self,file_path:str)->str:
        path = self._safe_path(file_path)
        if not path.exists():
             raise FileNotFoundError(
                f"File not found: {file_path}"
            )
        if not path.is_file():
             raise ValueError(
                f"Not a file: {file_path}"
            )
        path.unlink()
        return f"File deleted: {file_path}"

    def _safe_path(self, file_path: str) -> Path:
        target = (self.workspace / file_path).resolve()
        if not target.is_relative_to(self.workspace):
            raise PermissionError("Access denied: path is outside the workspace.")
        return target
