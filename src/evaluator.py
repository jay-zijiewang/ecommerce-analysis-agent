import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from src.agent import run_agent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = PROJECT_ROOT / "tests" / "evaluation_cases.json"
RESULTS_PATH = PROJECT_ROOT / "reports" / "evaluation_results.json"


def load_cases() -> list[dict[str, Any]]:
    """Load evaluation cases from JSON."""

    with CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def score_case(
    case: dict[str, Any],
    run_result: dict[str, Any],
) -> dict[str, Any]:
    """Score one completed agent run."""

    expected_counts = Counter(
        case.get("expected_tool_counts", {})
    )
    actual_counts = Counter(
        call["name"]
        for call in run_result["tool_calls"]
    )

    total_required_calls = sum(expected_counts.values())
    matched_required_calls = sum(
        min(actual_counts[name], expected_count)
        for name, expected_count in expected_counts.items()
    )

    if total_required_calls == 0:
        required_tool_recall = 1.0
    else:
        required_tool_recall = (
            matched_required_calls / total_required_calls
        )

    forbidden_tools = case.get("forbidden_tools", [])
    forbidden_tool_hits = [
        tool_name
        for tool_name in forbidden_tools
        if actual_counts[tool_name] > 0
    ]

    required_terms = case.get("required_terms", [])
    answer_lower = run_result["answer"].lower()
    found_terms = [
        term
        for term in required_terms
        if term.lower() in answer_lower
    ]

    if not required_terms:
        required_term_recall = 1.0
    else:
        required_term_recall = (
            len(found_terms) / len(required_terms)
        )

    tool_selection_pass = (
        actual_counts == expected_counts
        and not forbidden_tool_hits
    )
    task_completed = bool(run_result["answer"].strip())

    case_pass = (
        task_completed
        and tool_selection_pass
        and required_term_recall == 1.0
    )

    return {
        "id": case["id"],
        "question": case["question"],
        "tags": case.get("tags", []),
        "case_pass": case_pass,
        "task_completed": task_completed,
        "tool_selection_pass": tool_selection_pass,
        "required_tool_recall": round(
            required_tool_recall,
            4,
        ),
        "required_term_recall": round(
            required_term_recall,
            4,
        ),
        "expected_tool_counts": dict(expected_counts),
        "actual_tool_counts": dict(actual_counts),
        "forbidden_tool_hits": forbidden_tool_hits,
        "required_terms": required_terms,
        "found_terms": found_terms,
        "tool_calls": run_result["tool_calls"],
        "elapsed_seconds": run_result["elapsed_seconds"],
        "prompt_tokens": run_result["prompt_tokens"],
        "completion_tokens": run_result[
            "completion_tokens"
        ],
        "total_tokens": run_result["total_tokens"],
        "answer": run_result["answer"],
        "error": None,
    }


def evaluate_case(
    case: dict[str, Any],
) -> dict[str, Any]:
    """Run and score one evaluation case."""

    print(f"Running case: {case['id']}")

    try:
        run_result = run_agent(
            case["question"],
            return_trace=True,
            verbose=False,
        )
    except Exception as error:
        return {
            "id": case["id"],
            "question": case["question"],
            "tags": case.get("tags", []),
            "case_pass": False,
            "task_completed": False,
            "tool_selection_pass": False,
            "required_tool_recall": 0.0,
            "required_term_recall": 0.0,
            "expected_tool_counts": case.get(
                "expected_tool_counts",
                {},
            ),
            "actual_tool_counts": {},
            "forbidden_tool_hits": [],
            "required_terms": case.get(
                "required_terms",
                [],
            ),
            "found_terms": [],
            "tool_calls": [],
            "elapsed_seconds": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "answer": "",
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            },
        }

    if not isinstance(run_result, dict):
        raise TypeError(
            "Evaluation mode did not return a result dictionary."
        )

    return score_case(case, run_result)


def build_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build aggregate evaluation metrics."""

    case_count = len(results)
    passed_count = sum(
        result["case_pass"]
        for result in results
    )
    completed_count = sum(
        result["task_completed"]
        for result in results
    )
    tool_pass_count = sum(
        result["tool_selection_pass"]
        for result in results
    )

    return {
        "case_count": case_count,
        "passed_count": passed_count,
        "case_pass_rate": round(
            passed_count / case_count,
            4,
        ),
        "task_completion_rate": round(
            completed_count / case_count,
            4,
        ),
        "tool_selection_accuracy": round(
            tool_pass_count / case_count,
            4,
        ),
        "average_required_tool_recall": round(
            mean(
                result["required_tool_recall"]
                for result in results
            ),
            4,
        ),
        "average_required_term_recall": round(
            mean(
                result["required_term_recall"]
                for result in results
            ),
            4,
        ),
        "average_latency_seconds": round(
            mean(
                result["elapsed_seconds"]
                for result in results
            ),
            3,
        ),
        "total_tokens": sum(
            result["total_tokens"]
            for result in results
        ),
    }


def save_results(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    """Save evaluation results as JSON."""

    RESULTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "summary": summary,
        "cases": results,
    }

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=True,
        )


def main() -> None:
    """Run the evaluation suite."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        dest="case_id",
        default=None,
    )
    arguments = parser.parse_args()

    cases = load_cases()

    if arguments.case_id is not None:
        cases = [
            case
            for case in cases
            if case["id"] == arguments.case_id
        ]

        if not cases:
            raise ValueError(
                f"Unknown evaluation case: "
                f"{arguments.case_id}"
            )

    results = [
        evaluate_case(case)
        for case in cases
    ]
    summary = build_summary(results)
    save_results(summary, results)

    print()
    print(json.dumps(summary, indent=2))
    print(f"Saved results: {RESULTS_PATH}")


if __name__ == "__main__":
    main()