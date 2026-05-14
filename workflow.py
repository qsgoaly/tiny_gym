import argparse
import json
import time

import openai

from database import verify_identity, get_account_balance
from profiler import inject_traceparent_headers, span
from tools import SYSTEM_PROMPT, TOOLS

SGLANG_BASE_URL = "http://localhost:30000/v1"
MODEL_NAME = "Qwen/Qwen3.5-9B"

TOOL_DISPATCH = {
    "verify_identity": verify_identity,
    "get_account_balance": get_account_balance,
}

# ---------------------------------------------------------------------------
# Conversation scenarios
# ---------------------------------------------------------------------------

SCENARIOS = {
    "cooperative": {
        "description": "Customer provides all info upfront on first ask.",
        "script": [
            "Hi, I'd like to check my bank account balance please.",
            (
                "Sure! My name is Alice Johnson, my date of birth is "
                "1985-03-15, and the last four digits of my SSN are 1234."
            ),
        ],
    },
    "reluctant": {
        "description": "Customer is uneasy about sharing SSN and pushes back.",
        "script": [
            "Hello, I need to check my account balance.",
            "My name is Bob Smith.",
            "Why do you need my date of birth and SSN? That feels like a lot of personal info to share over the phone.",
            "Alright fine, my birthday is July 22, 1990. But I really don't want to give my SSN.",
            "Okay, I understand. The last four digits are 5678.",
        ],
    },
    "piecemeal": {
        "description": "Customer drip-feeds info one piece at a time.",
        "script": [
            "Hey, what's my balance?",
            "It's Carol.",
            "Carol Williams.",
            "November 3, 1978.",
            "9012.",
        ],
    },
    "wrong_info": {
        "description": "Customer gives wrong SSN first, then corrects it.",
        "script": [
            "Hi there, I want to see my balance.",
            "David Brown, born January 30, 1995, last four of SSN is 9999.",
            "Hmm that's weird, sorry — let me try again. The last four should be 3456.",
        ],
    },
}


def _call_llm(client, messages):
    with span(
        "llm_request", "llm_request",
        model=MODEL_NAME, **{"sglang.url": SGLANG_BASE_URL},
    ) as s:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
            extra_headers=inject_traceparent_headers(),
        )
        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        prompt_tokens = completion_tokens = 0
        if usage is not None:
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            s.set_attribute("prompt_tokens", prompt_tokens)
            s.set_attribute("completion_tokens", completion_tokens)
            s.set_attribute("total_tokens", usage.total_tokens)
        s.set_attribute("finish_reason", choice.finish_reason)
        s.set_attribute("n_tool_calls", len(choice.message.tool_calls or []))
        return response, prompt_tokens, completion_tokens


def _handle_tool_calls(tool_calls):
    results = []
    for tc in tool_calls:
        fn_name = tc.function.name
        fn_args = json.loads(tc.function.arguments)
        print(f"\n  [Tool Call]  {fn_name}({json.dumps(fn_args)})")

        with span(f"tool_call:{fn_name}", "tool_call", **{"tool.name": fn_name}) as s:
            t0 = time.time()
            try:
                result = TOOL_DISPATCH[fn_name](**fn_args)
                s.set_attribute("tool.success", True)
            except Exception as e:
                s.set_attribute("tool.success", False)
                s.set_attribute("tool.error", repr(e))
                raise
            elapsed = time.time() - t0
            s.set_attribute("tool.result_size", len(result))
        print(f"  [Tool Result] ({elapsed:.1f}s) {result}")

        results.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })
    return results


def run_conversation(scenario_name="cooperative"):
    scenario = SCENARIOS[scenario_name]
    print(f"\n{'#'*60}")
    print(f"# Scenario: {scenario_name}")
    print(f"# {scenario['description']}")
    print(f"{'#'*60}")

    client = openai.OpenAI(base_url=SGLANG_BASE_URL, api_key="not-needed")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    with span(
        f"scenario:{scenario_name}", "scenario",
        scenario_name=scenario_name, model=MODEL_NAME,
    ) as scenario_span:
        scenario_totals = {"llm": 0, "tool": 0, "prompt_tok": 0, "completion_tok": 0}

        for turn_index, user_msg in enumerate(scenario["script"]):
            print(f"\n{'='*60}")
            print(f"[Customer]: {user_msg}")
            messages.append({"role": "user", "content": user_msg})

            with span(
                f"turn[{turn_index}]", "turn",
                turn_index=turn_index,
                user_message=user_msg[:80],
            ) as turn_span:
                turn_llm = turn_tool = turn_pt = turn_ct = 0
                while True:
                    response, pt, ct = _call_llm(client, messages)
                    turn_llm += 1
                    turn_pt += pt
                    turn_ct += ct
                    assistant_msg = response.choices[0].message
                    messages.append(assistant_msg)

                    if assistant_msg.tool_calls:
                        turn_tool += len(assistant_msg.tool_calls)
                        tool_results = _handle_tool_calls(assistant_msg.tool_calls)
                        messages.extend(tool_results)
                        continue

                    if assistant_msg.content:
                        print(f"\n[Agent]: {assistant_msg.content}")
                    break

                turn_span.set_attribute("n_llm_calls", turn_llm)
                turn_span.set_attribute("n_tool_calls", turn_tool)
                turn_span.set_attribute("prompt_tokens", turn_pt)
                turn_span.set_attribute("completion_tokens", turn_ct)
                scenario_totals["llm"] += turn_llm
                scenario_totals["tool"] += turn_tool
                scenario_totals["prompt_tok"] += turn_pt
                scenario_totals["completion_tok"] += turn_ct

        scenario_span.set_attribute("n_turns", len(scenario["script"]))
        scenario_span.set_attribute("n_llm_calls", scenario_totals["llm"])
        scenario_span.set_attribute("n_tool_calls", scenario_totals["tool"])
        scenario_span.set_attribute("prompt_tokens", scenario_totals["prompt_tok"])
        scenario_span.set_attribute("completion_tokens", scenario_totals["completion_tok"])
        scenario_span.set_attribute("n_messages", len(messages))

    print(f"\n{'='*60}")
    print(f"[Conversation complete — {len(messages)} messages total]\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a bank customer service scenario")
    parser.add_argument(
        "scenario",
        nargs="?",
        default="cooperative",
        choices=list(SCENARIOS.keys()),
        help="Which conversation scenario to run (default: cooperative)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios sequentially",
    )
    args = parser.parse_args()

    if args.all:
        for name in SCENARIOS:
            run_conversation(name)
    else:
        run_conversation(args.scenario)
