# Ask FinAI

A chat page where you ask Claude about the FinAI platform in plain English. It answers from
your real files (V009 status, research reports, shadow strategies, collection logs, events)
and lists its sources.

## One-time setup
1. Create an API key at https://console.anthropic.com (API usage is billed there, separately
   from a Claude subscription).
2. Store it encrypted for your Windows account:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\set_anthropic_key.ps1
   ```

## Start it
`scripts\start_v42.ps1` starts it automatically when a key is stored. To start it by hand:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_ask_finai.ps1
```

Open http://127.0.0.1:8502, or use **Ask FinAI** in the dashboard sidebar.
Default model: `claude-sonnet-5-5`. To change it, set `FINAI_CLAUDE_MODEL` before starting.

## What it can and cannot do
- Reads only `artifacts`, `research`, `logs`, `docs`, `config`, `research_kit` and root
  `README*.md` files. `.env`, credential, secret and key files and `.git` are blocked, and
  key-like strings are redacted.
- Can propose one job (a legacy V4.1 learning cycle); it runs only after you click Confirm.
- Cannot place orders, change gates, configuration or the V009 protocol/policy/panel.
- Treats V009 as performance-blind and will not estimate its returns.
- Research only; not financial advice.

## Code
`src/finai/assistant/` (knowledge tools, jobs, Claude client), `apps/ask_finai/app.py`
(Streamlit page), `tests/unit/test_ask_finai.py`.
