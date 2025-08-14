import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

EDUCATIONAL_NOTE_PROMPT = """You are a git expert. Based on this command result, provide a concise educational note (1-2 sentences) explaining what happened and a key git concept it demonstrates.

Command: {command}
Success: {success}
Output: {output}
Error: {error}
Original note from plan: {original_note}

Keep it simple and educational."""


def get_llm():
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "o4-mini"), api_key=os.getenv("OPENAI_API_KEY")
    )


# using an llm to generate an educational note with structured outputs
def generate_educational_note(
    command: str, success: bool, output: str, error: str, original_note: str
) -> str:
    llm = get_llm()
    context = {
        "command": command,
        "success": success,
        "output": output,
        "error": error,
        "original_note": original_note,
    }

    messages = [
        SystemMessage(content=EDUCATIONAL_NOTE_PROMPT.format(**context)),
        HumanMessage(content="Generate a concise educational note."),
    ]

    response = llm.invoke(messages)
    return response.content.strip()
