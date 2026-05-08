import argparse
import json
import time

import openai

from database import verify_identity, get_account_balance
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
    return client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.1,
    )


def _handle_tool_calls(tool_calls):
    results = []
    for tc in tool_calls:
        fn_name = tc.function.name
        fn_args = json.loads(tc.function.arguments)
        print(f"\n  [Tool Call]  {fn_name}({json.dumps(fn_args)})")

        t0 = time.time()
        result = TOOL_DISPATCH[fn_name](**fn_args)
        elapsed = time.time() - t0
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

    for user_msg in scenario["script"]:
        print(f"\n{'='*60}")
        print(f"[Customer]: {user_msg}")
        messages.append({"role": "user", "content": user_msg})

        while True:
            response = _call_llm(client, messages)
            assistant_msg = response.choices[0].message

            messages.append(assistant_msg)

            if assistant_msg.tool_calls:
                tool_results = _handle_tool_calls(assistant_msg.tool_calls)
                messages.extend(tool_results)
                continue

            if assistant_msg.content:
                print(f"\n[Agent]: {assistant_msg.content}")
            break

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
