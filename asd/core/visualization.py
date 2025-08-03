from pathlib import Path

from .graph import create_git_assistant

graph = create_git_assistant()
png_bytes = graph.get_graph().draw_mermaid_png()

file_path = Path("images/git_assistant.png")
file_path.parent.mkdir(parents=True, exist_ok=True)

with open(file_path, "wb") as f:
    f.write(png_bytes)

print(f"Saved graph image to {file_path}!")
