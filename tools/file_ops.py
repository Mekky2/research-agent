from langchain_core.tools import tool
import os

@tool
def save_report(content: str, filename: str = "final_report.txt") -> str:
    """Saves the final verified research report to the local disk."""
    print(f"[Tool: FileOps] Saving report to {filename}")

    try:
        with open(filename, "w", encoding = "utf-8") as f:
            f.write(content)
        return f"Successfully saved report to {os.path.abspath(filename)}"
    except Exception as e:
        return f"Failed to save file: {str(e)}"