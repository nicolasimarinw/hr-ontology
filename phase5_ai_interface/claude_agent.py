"""Claude AI agent with tool use for HR ontology queries."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import anthropic

from config.settings import ANTHROPIC_API_KEY
from phase5_ai_interface.prompts.system_prompt import SYSTEM_PROMPT
from phase5_ai_interface.prompts.example_queries import EXAMPLE_QUERIES
from phase5_ai_interface.tools.cypher_tools import query_graph
from phase5_ai_interface.tools.duckdb_tools import query_data_lake
from phase5_ai_interface.tools.ontology_tools import describe_ontology
from phase5_ai_interface.tools.visualization_tools import visualize_subgraph, run_graph_algorithm

# Model to use for the chat interface
MODEL = "claude-sonnet-4-6"

# Tool definitions for the Claude API
TOOLS = [
    {
        "name": "query_graph",
        "description": (
            "Execute a Cypher query against the Neo4j HR knowledge graph. "
            "Use this for relationship-based questions: org hierarchy traversal, "
            "skill networks, cascade impact, pattern matching across entities. "
            "Returns JSON with rows and count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cypher": {
                    "type": "string",
                    "description": "A valid Cypher query. Use parameterized queries with $param syntax when possible."
                },
            },
            "required": ["cypher"],
        },
    },
    {
        "name": "query_data_lake",
        "description": (
            "Execute a SQL query against the DuckDB data lake (Parquet files). "
            "Use this for aggregate analytics: compensation stats, turnover rates, "
            "demographic distributions, cross-tabulations, time-series analysis. "
            "Available tables: employees, departments, positions, locations, "
            "employment_history, requisitions, candidates, applications, interviews, "
            "offers, performance_cycles, goals, performance_reviews, "
            "competency_assessments, salary_bands, base_salary, bonuses, equity_grants."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A valid DuckDB SQL query. Table aliases are pre-registered (e.g., SELECT * FROM employees)."
                },
            },
            "required": ["sql"],
        },
    },
    {
        "name": "describe_ontology",
        "description": (
            "Describe the HR ontology schema: node types, relationship types, "
            "and their properties. Use this to understand available data before "
            "writing queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": (
                        "What to describe: 'all' for full overview, 'nodes' for all node types, "
                        "'edges' for all relationships, or a specific name like 'Employee' or 'REPORTS_TO'."
                    ),
                },
            },
            "required": ["entity_type"],
        },
    },
    {
        "name": "visualize_subgraph",
        "description": (
            "Execute a Cypher query and render the results as an interactive HTML graph. "
            "Use this to create visual representations of query results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cypher": {
                    "type": "string",
                    "description": "Cypher query to visualize.",
                },
                "title": {
                    "type": "string",
                    "description": "Short title for the visualization file.",
                },
            },
            "required": ["cypher", "title"],
        },
    },
    {
        "name": "run_graph_algorithm",
        "description": (
            "Run a graph algorithm: centrality (influential managers), "
            "community (cross-department clusters), cascade (departure impact), "
            "org_distance (shortest path between employees), flight_risk (top risks), "
            "or render visualizations (render_org_chart, render_department_network, "
            "render_compensation_map, render_recruiting_funnel, render_skills_network)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "algorithm": {
                    "type": "string",
                    "description": "Algorithm name: centrality, community, cascade, org_distance, flight_risk, or render_*.",
                },
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID (for cascade analysis). Format: EMP-XXXXX.",
                },
                "emp1_id": {
                    "type": "string",
                    "description": "First employee ID (for org_distance).",
                },
                "emp2_id": {
                    "type": "string",
                    "description": "Second employee ID (for org_distance).",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top results to return (default: 15).",
                },
            },
            "required": ["algorithm"],
        },
    },
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "query_graph": lambda inp: query_graph(inp["cypher"]),
    "query_data_lake": lambda inp: query_data_lake(inp["sql"]),
    "describe_ontology": lambda inp: describe_ontology(inp["entity_type"]),
    "visualize_subgraph": lambda inp: visualize_subgraph(inp["cypher"], inp.get("title", "subgraph")),
    "run_graph_algorithm": lambda inp: run_graph_algorithm(
        inp["algorithm"],
        employee_id=inp.get("employee_id"),
        emp1_id=inp.get("emp1_id"),
        emp2_id=inp.get("emp2_id"),
        top_n=inp.get("top_n", 15),
    ),
}


def _build_system_prompt() -> str:
    """Build the full system prompt with few-shot examples."""
    examples_text = "\n\n## Example Queries\n"
    for ex in EXAMPLE_QUERIES[:6]:
        examples_text += f"\n**Q: {ex['question']}**\n"
        examples_text += f"Approach: {ex['approach']}\n"
        if "query" in ex:
            examples_text += f"```\n{ex['query'].strip()}\n```\n"
        if "note" in ex:
            examples_text += f"Note: {ex['note']}\n"
    return SYSTEM_PROMPT + examples_text


class HRAgent:
    """Claude-powered HR analytics agent with tool use."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or ANTHROPIC_API_KEY
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Set it in .env or pass api_key parameter."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model or MODEL
        self.system_prompt = _build_system_prompt()
        self.messages: list[dict] = []

    def reset(self):
        """Clear conversation history."""
        self.messages = []

    def chat(self, user_message: str, on_tool_call=None) -> str:
        """Send a message and get a response, handling tool calls automatically.

        Args:
            user_message: The user's question or request.
            on_tool_call: Optional callback(tool_name, tool_input, tool_result)
                         called each time a tool is used.

        Returns:
            The assistant's final text response.
        """
        self.messages.append({"role": "user", "content": user_message})

        max_iterations = 10
        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=TOOLS,
                messages=self.messages,
            )

            # If no tool use, we're done
            if response.stop_reason == "end_turn":
                # Extract text from response
                text_parts = []
                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)

                assistant_text = "\n".join(text_parts)
                self.messages.append({"role": "assistant", "content": response.content})
                return assistant_text

            # Handle tool use
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # No tool calls and not end_turn - extract text anyway
                text_parts = [b.text for b in response.content if b.type == "text"]
                assistant_text = "\n".join(text_parts)
                self.messages.append({"role": "assistant", "content": response.content})
                return assistant_text

            # Append assistant message with tool_use blocks
            self.messages.append({"role": "assistant", "content": response.content})

            # Execute tools and collect results
            tool_results = []
            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input

                # Execute the tool
                func = TOOL_FUNCTIONS.get(tool_name)
                if func:
                    try:
                        result = func(tool_input)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                # Notify callback
                if on_tool_call:
                    on_tool_call(tool_name, tool_input, result)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result,
                })

            # Send tool results back
            self.messages.append({"role": "user", "content": tool_results})

        return "I reached the maximum number of tool calls. Please try a more specific question."


if __name__ == "__main__":
    agent = HRAgent()
    print("HR Ontology AI Assistant (type 'quit' to exit)\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        def on_tool(name, inp, result):
            print(f"  [Tool: {name}]")

        response = agent.chat(user_input, on_tool_call=on_tool)
        print(f"\nAssistant: {response}\n")
