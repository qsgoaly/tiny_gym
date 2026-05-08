# Bank Customer Service Call Simulation

Simulates a phone call between a bank customer and an LLM-powered customer service agent. The agent verifies the caller's identity (name, date of birth, last 4 digits of SSN) before looking up account balances.

## Architecture

```
┌──────────────┐     OpenAI-compat API     ┌──────────────────┐
│  workflow.py  │ ◄──────────────────────► │  sglang server   │
│  (orchestrator)│    /v1/chat/completions  │  Qwen3.5-9B      │
└──────┬───────┘                           └──────────────────┘
       │ tool calls
       ▼
┌──────────────┐
│  database.py  │  In-memory bank DB
│  (~1.5 GB)    │  + heavy index scan
└──────────────┘
```

**Three components:**

| Component | File | Description |
|---|---|---|
| LLM Server | `start_server.sh` | sglang serving Qwen3.5-9B with tool-calling support |
| Database | `database.py` | 15 users, 19 accounts, 1.46 GB numpy index, 2s+ per query |
| Workflow | `workflow.py` | Multi-turn conversation loop with tool dispatch |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```
or use sglang docker
```
docker pull lmsysorg/sglang:latest
```
### 2. Run (auto-starts server)

```bash
python run.py                  # default "cooperative" scenario
python run.py reluctant        # reluctant customer scenario
python run.py piecemeal        # customer drip-feeds info
python run.py wrong_info       # customer gives wrong SSN, then corrects
python run.py --all            # run all scenarios
```

`run.py` will start the sglang server automatically if it's not already running and wait for it to be ready (model download may take a few minutes on first run).

### Alternative: start server separately

```bash
bash start_server.sh           # terminal 1
python workflow.py cooperative  # terminal 2
python workflow.py --all        # or run all scenarios
```

## Scenarios

| Name | Turns | Description |
|---|---|---|
| `cooperative` | 2 | Customer provides all info on first ask |
| `reluctant` | 5 | Customer pushes back on sharing SSN, agent must persuade |
| `piecemeal` | 5 | Customer gives info one piece at a time |
| `wrong_info` | 3 | Customer gives wrong SSN, verification fails, then corrects |

## Performance Characteristics

- **Memory**: `database.py` allocates a 14000x14000 float64 numpy array (~1.46 GB) at import time to simulate a heavy in-memory database index.
- **Latency**: Each tool call runs a full matrix-vector cosine similarity search across the index, then pads to a 2-second minimum. This simulates realistic database query latency.
- **Model**: Qwen3.5-9B (~18 GB in bf16). Served by sglang on port 30000 with the `qwen3_coder` tool-call parser.

## File Reference

```
├── requirements.txt   # sglang, openai, numpy
├── start_server.sh    # Launch sglang inference server
├── database.py        # Simulated DB: user/account data + heavy numpy index
├── tools.py           # OpenAI tool schemas + system prompt
├── workflow.py        # Conversation orchestrator with 4 scenarios
└── run.py             # Entrypoint: server lifecycle + scenario runner
```

## Sample Output

```
############################################################
# Scenario: reluctant
# Customer is uneasy about sharing SSN and pushes back.
############################################################

============================================================
[Customer]: Hello, I need to check my account balance.

[Agent]: I'd be happy to help you check your account balance. For security
purposes, I'll need to verify your identity first. Could you please provide
me with your full name, date of birth, and the last 4 digits of your SSN?

============================================================
[Customer]: My name is Bob Smith.

[Agent]: Thank you, Bob. I also need your date of birth and the last 4
digits of your Social Security Number to complete the verification.

============================================================
[Customer]: Why do you need my date of birth and SSN? That feels like a
lot of personal info to share over the phone.

[Agent]: I completely understand your concern. We take your privacy very
seriously. This information is required by federal regulations to verify
your identity and protect your account from unauthorized access. Your
data is encrypted and never shared with third parties. ...

  ...

  [Tool Call]  verify_identity({"name":"Bob Smith", ...})
  [Tool Result] (2.0s) {"verified": true, "user_id": "U002"}

  [Tool Call]  get_account_balance({"user_id":"U002"})
  [Tool Result] (2.0s) {"accounts": [{"account_number":"ACC-10003", ...}]}

[Agent]: Your checking account (ACC-10003) has a balance of $3,421.00.
```
