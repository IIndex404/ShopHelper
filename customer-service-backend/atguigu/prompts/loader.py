from pathlib import Path


def load_prompt(prompt_file_name: str) -> str:
    path = Path(__file__).resolve().parent / "jinja2" / f"{prompt_file_name}.jinja2"
    return path.read_text(encoding="utf-8")
