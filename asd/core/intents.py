import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .costs import UsageCallback, get_active_model_provider
from .models import Intent

SYSTEM_PROMPT = """you are a git safety and education assistant. your job is to understand what the user wants to do with git, 
while being mindful of safety and learning opportunities.

analyze the user's request and extract:

1. **primary git action** - the main thing they want to accomplish
2. **secondary actions** - any follow-up git operations needed
3. **safety concerns** - any fears or safety questions they express
4. **learning goals** - what they want to understand about git
5. **specific targets** - files, branches, commits they mention
6. **force indicators** - if they explicitly want to force something

**common user language patterns:**
- "undo" → usually means reset or revert
- "go back" → checkout previous commit or reset
- "fix my last commit" → amend or reset
- "clean up" → reset, clean, or branch deletion
- "sync with main" → pull, merge, or rebase
- "save my work" → commit, stash, or add
- "share my changes" → push or create pull request
- "i messed up" → indicates need for recovery help
- "without losing work" → safety concern about data loss
- "what would happen if" → learning/safety question

**examples:**
user: "undo my last commit but keep my changes"
→ primary_action: reset, safety_concern: "don't lose changes", learning_goal: "understand difference between reset types"

user: "i accidentally committed to main instead of a feature branch"  
→ primary_action: reset, secondary_actions: [branch, checkout, commit], safety_concern: "fix wrong branch commit"

user: "safely merge main into my feature branch"
→ primary_action: merge, safety_concern: "avoid conflicts", learning_goal: "safe merging practices"

focus on git operations only. if the user asks about non-git tasks, set primary_action to "status" and add a note about focusing on git."""


# capturing user's intent using an LLM and system prompt with structured outputs
def get_llm():
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "o4-mini"), api_key=os.getenv("OPENAI_API_KEY")
    )


def parse_intent(user_input: str) -> Intent:
    llm = get_llm()
    mapper = llm.with_structured_output(Intent)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"user request: {user_input}"),
    ]

    provider, model = get_active_model_provider()
    return mapper.invoke(
        messages,
        config={"callbacks": [UsageCallback(provider, model)]},
    )
