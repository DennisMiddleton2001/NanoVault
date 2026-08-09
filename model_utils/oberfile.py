from pathlib import Path
import shutil

class OberFs:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @classmethod
    def file(cls, path: str | Path):
        """Explicitly target a file."""
        return cls(path)

    @classmethod
    def folder(cls, path: str | Path):
        """Explicitly target a folder."""
        return cls(path)

    def exists(self) -> bool:
        """Check if the path exists."""
        return self.path.exists()

    def delete(self, missing_ok: bool = True) -> bool:
        """Delete a file or an entire directory tree automatically."""
        if not self.path.exists():
            if missing_ok:
                return False
            raise FileNotFoundError(f"Path not found: {self.path}")
            
        if self.path.is_dir():
            shutil.rmtree(self.path)  # Handles folders [1]
        else:
            self.path.unlink()        # Handles files [1]
        return True

    def rename(self, new_name: str):
        """Rename the file or folder in place."""
        self.path = self.path.rename(self.path.with_name(new_name))

    def read(self) -> str:
        """Read file contents instantly."""
        return self.path.read_text()

    def write(self, content: str):
        """Write file contents instantly."""
        self.path.write_text(content)