from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..ui.display import display_execution_plan, display_git_status
from .executor import execute_plan
from .git_tools import get_git_status
from .intents import parse_intent
from .models import State
from .planner import generate_execution_plan


def create_git_assistant():
    graph = StateGraph(State)

    # analyze git context (to understand the current state of the repo)
    def analyze_git_context(state: State) -> State:
        git_status = get_git_status()
        return state.copy(update={"git_status": git_status})

    # parse the user's intent (to understand what they want to do)
    def parse_git_intent(state: State) -> State:
        intent = parse_intent(state.input)
        return state.copy(update={"intent": intent})

    # create an execution plan (to understand the steps needed to achieve the user's intent)
    def create_execution_plan(state: State) -> State:
        plan = generate_execution_plan(state)
        return state.copy(update={"plan": plan})

    # show plan overview before step-by-step execution
    def show_plan_overview(state: State) -> State:
        from ..ui.display import console

        console.print()
        display_git_status(state.git_status)
        display_execution_plan(state.plan)
        return state

    graph.add_node("analyze", analyze_git_context)
    graph.add_node("intent", parse_git_intent)
    graph.add_node("plan", create_execution_plan)
    graph.add_node("show", show_plan_overview)
    graph.add_node("execute", execute_plan)  # step-by-step approval

    # added show node to show the plan overview before step-by-step execution
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "intent")
    graph.add_edge("intent", "plan")
    graph.add_edge("plan", "show")
    graph.add_edge("show", "execute")  # go directly to execute
    graph.add_edge("execute", END)  # always end after execute

    return graph.compile(checkpointer=MemorySaver())
