# LangGraph — Complete Reference

## What is LangGraph?
LangGraph is a framework for building stateful, multi-agent AI applications as directed graphs. Built on LangChain, it extends it with cycles, persistence, and human-in-the-loop patterns that LangChain's linear chains cannot support.

## Core Concepts

### StateGraph
The fundamental building block. You define a TypedDict as shared state, add nodes (Python functions), and connect them with edges.

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str

def classify(state: State) -> dict:
    return {"intent": "sql"}

builder = StateGraph(State)
builder.add_node("classify", classify)
builder.set_entry_point("classify")
builder.add_edge("classify", END)
graph = builder.compile()
```

### Nodes
Any async or sync Python function with signature `(state: State) -> dict`. The returned dict is merged into the state using reducers (e.g., `add_messages` appends to the list instead of replacing).

### Edges
- **Direct edge**: `builder.add_edge("a", "b")` — always goes from a to b
- **Conditional edge**: `builder.add_conditional_edges("planner", route_fn, {"sql": "sql_agent", "python": "python_agent"})` — route_fn returns one of the keys

### Reducers
State fields use reducers to handle concurrent writes. The `add_messages` reducer appends instead of overwriting, enabling message history accumulation.

## Multi-Agent Architecture

### Supervisor Pattern
A planner/supervisor node classifies intent and routes to specialist nodes. Each specialist writes to its own state field and the final response.

```
START → planner → [conditional] → sql_agent → END
                               → python_agent → END
                               → research_agent → END
```

### Tool-Calling Nodes
Each node can bind LangChain tools and run an internal agentic loop:
```python
llm_with_tools = llm.bind_tools([tool1, tool2])
response = await llm_with_tools.ainvoke(messages)
if response.tool_calls:
    # execute tools, add ToolMessage, loop
```

## Persistence and Checkpointing
LangGraph supports persistent state via checkpointers (SQLite, PostgreSQL). This enables:
- Session memory across conversations
- Human-in-the-loop (pause graph execution, wait for human input)
- Time-travel debugging (replay from any checkpoint)

```python
from langgraph.checkpoint.sqlite import SqliteSaver
memory = SqliteSaver.from_conn_string(":memory:")
graph = builder.compile(checkpointer=memory)
result = graph.invoke(state, config={"configurable": {"thread_id": "session-1"}})
```

## When to Use LangGraph vs LangChain
Use LangGraph when you need:
- Cycles (agent loops that repeat until a condition is met)
- Multiple specialized agents coordinating
- State that persists across turns
- Human approval steps
- Complex routing logic

Use plain LangChain chains when:
- Single linear pipeline with no cycles
- Simple prompt → LLM → output
- No agent coordination needed

## Key LangGraph Patterns

### ReAct Loop
```
LLM → tool call → tool result → LLM → (repeat until no tool calls) → final response
```

### Parallel Execution
Multiple agents can run in parallel using `Send` API:
```python
from langgraph.constants import Send
def router(state): 
    return [Send("agent", {"task": t}) for t in state["tasks"]]
```

### Streaming
```python
async for event in graph.astream_events(state, version="v2"):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="")
```
