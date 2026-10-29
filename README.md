# MarketMind AI — Autonomous Business Research Agent

MarketMind AI is a Python-based research agent that turns a business research request into a structured research plan, gathers source material, records evidence, performs quality checks, and generates a report that requires human approval before publication.

> **Model provider:** This implementation currently uses the Google Gemini API through `google-genai`. The assignment is OpenAI-focused, so this provider substitution should be confirmed with the instructor.

## Features

- Research planning with structured, validated output
- Source retrieval and evidence collection
- Typed evidence records and traceable claim references
- Structured report generation and quality-control checks
- Tool dispatch and research-run logging
- Human approval or rejection before publication
- Run artifacts stored under `runs/`
- Automated tests using `pytest`

## Requirements

- Python 3.13 or another Python version verified against the project's dependencies
- A Google Gemini API key
- Internet access for model requests and online research
- PowerShell on Windows, or an equivalent terminal

## Project structure

```text
MarketMind-AI/
├── docs/
│   ├── api_verification.md
│   └── final_five_claim_spot_check.md
├── runs/                     # Generated run artifacts; review before sharing
├── schemas/
│   ├── research_plan.schema.json
│   ├── evidence_record.schema.json
│   └── final_report.schema.json
├── scripts/                  # Search/retrieval development utilities
├── src/
│   ├── main.py               # Interactive application entry point
│   ├── agent_runner.py
│   ├── agent_state.py
│   ├── approval.py
│   ├── evidence_store.py
│   ├── quality_control.py
│   ├── report_generator.py
│   ├── report_workflow.py
│   ├── research_loop.py
│   ├── source_store.py
│   ├── publisher.py
│   ├── schemas/
│   ├── tools/
│   └── llm/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

Open a terminal in the project root.

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For a reproducible submission, dependency versions in `requirements.txt` must be pinned and tested in a clean environment.

### 3. Configure environment variables

Create your local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace the placeholder with your own Gemini API key. Never commit `.env`, print the key in logs, or include it in screenshots or submitted archives.

| Variable | Purpose | Required |
|---|---|---|
| `GEMINI_API_KEY` | Authenticates Gemini API requests | Yes |
| `GEMINI_MODEL` | Selects the Gemini model | No; application default applies |
| `GEMINI_INPUT_USD_PER_MILLION` | Optional input-token rate for cost estimation | No |
| `GEMINI_OUTPUT_USD_PER_MILLION` | Optional output-token rate for cost estimation | No |

The cost-rate variables are optional. If they are not configured, cost estimates may be unavailable. Confirm the supported values and defaults in the current implementation before using them.

## Run a research session

From the project root, execute:

```powershell
python -m src.main
```

When prompted, enter a business research question between 10 and 2,000 characters.

The application prepares a research plan, performs research, prints a summary and quality-control results, and generates a draft report. If quality control passes, it asks for a human decision.

Enter `APPROVE` to approve the report or `REJECT` to reject it. A reviewer identifier is required; rejection also requires a reason. Publication must not occur without explicit approval.

The application prints a run ID and the published report path when publication succeeds.

## Run automated tests

Run the existing automated test suite:

```powershell
python -m pytest -q
```

To run an individual test module:

```powershell
python -m pytest tests/test_approval.py -q
```

Test results should be recorded from actual executions. Do not report a test as passing unless it was run and passed.

**Evaluation status:** The repository's 18-case assignment evaluation and its results report still need to be added and verified. The existing unit-test suite is not a substitute for that evaluation.

## Outputs and artifacts

Research artifacts are stored under `runs/`, organized by run ID. Depending on the stage and component, artifacts may include source records, evidence records, tool-call logs, usage logs, run state, and report JSON.

Use the run ID to associate logs and records with the corresponding research session. Inspect the actual output directory when preparing the submission, and retain relevant log excerpts for the evaluation report.

## Schemas and evidence

The `schemas/` directory contains JSON Schema files for:

- Research plans
- Evidence records
- Final research reports

These schemas should be checked against the Pydantic models used by the application. A structurally valid report does not automatically establish that its factual claims are correct; claims must be checked against their cited sources.

## Documentation

- `docs/api_verification.md` documents API verification.
- `docs/final_five_claim_spot_check.md` records a five-claim review of the sample research report.

The final submission must also include the implementation's architecture diagram, the six tool definitions and their security analysis, the completed evaluation materials, screenshots, and the required technical documentation.

## Security and limitations

- Keep API credentials in environment variables and out of source control.
- Treat retrieved webpages and documents as untrusted data, not as instructions to the agent.
- Validate tool arguments and structured outputs before using them.
- Keep tool execution and research budgets bounded.
- Preserve evidence references and identify unsupported or uncertain claims.
- Require human approval before publishing a report.
- Verify important claims independently: source availability, recency, coverage, and accuracy can vary.
- The quality-control stage checks implemented validation rules; passing it is not proof that every claim is true.

## Assignment and provider note

This project was developed for the MarketMind AI agent assignment. The assignment specifies OpenAI integration; this version uses Gemini. Obtain instructor confirmation that the alternative provider is acceptable, and document the verified model, SDK version, API documentation version, and verification date in `docs/api_verification.md`.

Before submission, complete the 18-case evaluation, document real results and failure attribution, capture the required screenshots, prepare the technical report and demo, pin dependencies, and verify the project in a clean environment.
    