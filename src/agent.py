import json
import os
from time import perf_counter
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from src.prompts import SYSTEM_PROMPT
from src.tools import (
    breakdown_by_dimension,
    compare_dimension_periods,
    compare_periods,
    get_funnel_metrics,
    get_overview_metrics,
)

load_dotenv()


DATE_FILTER_PROPERTIES = {
    "start_date": {
        "type": "string",
        "description": "Inclusive start date in YYYY-MM-DD format.",
    },
    "end_date": {
        "type": "string",
        "description": "Inclusive end date in YYYY-MM-DD format.",
    },
    "category": {
        "type": "string",
        "description": (
            "Optional product category filter. Known values are Beauty, "
            "Electronics, Home, Apparel, and Food. Pass the user's value "
            "through unchanged so the Python tool can validate it."
        ),
    },
    "channel": {
        "type": "string",
        "description": (
            "Optional traffic channel filter. Known values are "
            "Livestream, Short Video, and Search. Pass the user's value "
            "through unchanged so the Python tool can validate it."
        ),
    },
    "user_segment": {
        "type": "string",
        "description": (
            "Optional user segment filter. Known values are New, "
            "Returning, and High Value. Pass the user's value through "
            "unchanged so the Python tool can validate it."
        ),
    },
}


COMPARISON_PROPERTIES = {
    "current_start_date": {
        "type": "string",
        "description": "Inclusive start date of the current period.",
    },
    "current_end_date": {
        "type": "string",
        "description": "Inclusive end date of the current period.",
    },
    "previous_start_date": {
        "type": "string",
        "description": "Inclusive start date of the previous period.",
    },
    "previous_end_date": {
        "type": "string",
        "description": "Inclusive end date of the previous period.",
    },
    "category": DATE_FILTER_PROPERTIES["category"],
}


DIMENSION_COMPARISON_PROPERTIES = {
    **COMPARISON_PROPERTIES,
    "channel": DATE_FILTER_PROPERTIES["channel"],
    "user_segment": DATE_FILTER_PROPERTIES["user_segment"],
    "dimension": {
        "type": "string",
        "enum": [
            "category",
            "channel",
            "user_segment",
        ],
        "description": (
            "Dimension whose values should be compared "
            "between the two periods."
        ),
    },
}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_overview_metrics",
            "description": (
                "Return aggregated business metrics for one date range "
                "and optional category, channel, or user-segment filters. "
                "For a single-period overview request, call this exactly "
                "once and pass every user-provided filter value unchanged, "
                "including values that may be invalid."
            ),
            "parameters": {
                "type": "object",
                "properties": DATE_FILTER_PROPERTIES,
                "required": [
                    "start_date",
                    "end_date",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": (
                "Compare the same business scope between a current "
                "period and a previous period. Return current values, "
                "previous values, absolute changes, and relative changes."
            ),
            "parameters": {
                "type": "object",
                "properties": COMPARISON_PROPERTIES,
                "required": [
                    "current_start_date",
                    "current_end_date",
                    "previous_start_date",
                    "previous_end_date",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_dimension_periods",
            "description": (
                "Compare every value of one business dimension "
                "between a current period and a previous period. "
                "Use this instead of repeated filtered calls. Do not use "
                "this tool merely to validate a filter or list valid values."
            ),
            "parameters": {
                "type": "object",
                "properties": DIMENSION_COMPARISON_PROPERTIES,
                "required": [
                    "current_start_date",
                    "current_end_date",
                    "previous_start_date",
                    "previous_end_date",
                    "dimension",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "breakdown_by_dimension",
            "description": (
                "Break down business metrics by category, channel, "
                "or user segment for one selected period."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **DATE_FILTER_PROPERTIES,
                    "dimension": {
                        "type": "string",
                        "enum": [
                            "category",
                            "channel",
                            "user_segment",
                        ],
                        "description": "Dimension used for the breakdown.",
                    },
                },
                "required": [
                    "start_date",
                    "end_date",
                    "dimension",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_funnel_metrics",
            "description": (
                "Return impressions, clicks, paid orders, buyers, "
                "CTR, and CVR for a selected business scope."
            ),
            "parameters": {
                "type": "object",
                "properties": DATE_FILTER_PROPERTIES,
                "required": [
                    "start_date",
                    "end_date",
                ],
                "additionalProperties": False,
            },
        },
    },
]


TOOL_FUNCTIONS = {
    "get_overview_metrics": get_overview_metrics,
    "compare_periods": compare_periods,
    "compare_dimension_periods": compare_dimension_periods,
    "breakdown_by_dimension": breakdown_by_dimension,
    "get_funnel_metrics": get_funnel_metrics,
}


def create_client() -> OpenAI:
    """Create a DeepSeek API client."""

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
    )

    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY is missing from the .env file."
        )

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> str:
    """Execute a local Python tool and return a JSON string."""

    tool_function = TOOL_FUNCTIONS.get(tool_name)

    if tool_function is None:
        return json.dumps(
            {
                "status": "error",
                "error_type": "UnknownTool",
                "message": f"Unknown tool: {tool_name}",
            }
        )

    try:
        result = tool_function(**arguments)
    except Exception as error:
        return json.dumps(
            {
                "status": "error",
                "error_type": type(error).__name__,
                "message": str(error),
            }
        )

    return json.dumps(result)


def run_agent(
    question: str,
    return_trace: bool = False,
    verbose: bool = True,
) -> str | dict[str, Any]:
    """Run the DeepSeek tool-calling loop."""

    started_at = perf_counter()
    tool_trace: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    force_final_answer = False

    client = create_client()
    model = os.getenv(
        "DEEPSEEK_MODEL",
        "deepseek-v4-flash",
    )

    messages: list[Any] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    maximum_tool_rounds = 8

    for _ in range(maximum_tool_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice=(
                "none" if force_final_answer else "auto"
            ),
            stream=False,
            max_tokens=2000,
            extra_body={
                "thinking": {
                    "type": "disabled",
                }
            },
        )

        if response.usage is not None:
            prompt_tokens += response.usage.prompt_tokens or 0
            completion_tokens += response.usage.completion_tokens or 0
            total_tokens += response.usage.total_tokens or 0

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

        if choice.finish_reason == "length":
            raise RuntimeError(
                "The model response reached the token limit."
            )

        if not message.tool_calls:
            if not message.content:
                raise RuntimeError(
                    "The model returned an empty final response."
                )

            if not return_trace:
                return message.content

            return {
                "question": question,
                "answer": message.content,
                "tool_calls": tool_trace,
                "tool_call_count": len(tool_trace),
                "elapsed_seconds": round(
                    perf_counter() - started_at,
                    3,
                ),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments

            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as error:
                arguments = {}
                tool_result = json.dumps(
                    {
                        "status": "error",
                        "error_type": type(error).__name__,
                        "message": "Tool arguments were not valid JSON.",
                    }
                )
            else:
                if verbose:
                    print(f"Tool call: {tool_name}")
                    print(
                        "Arguments: "
                        + json.dumps(arguments, indent=2)
                    )

                tool_result = execute_tool(
                    tool_name,
                    arguments,
                )

            parsed_result = json.loads(tool_result)
            tool_status = (
                parsed_result.get("status", "unknown")
                if isinstance(parsed_result, dict)
                else "unknown"
            )

            if tool_status in {"error", "no_data"}:
                force_final_answer = True

            tool_trace.append(
                {
                    "name": tool_name,
                    "arguments": arguments,
                    "status": tool_status,
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                }
            )

    raise RuntimeError(
        "The agent exceeded the maximum number of tool rounds."
    )