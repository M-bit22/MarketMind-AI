# MarketMind AI — Demo Notes

## Demo objective
Demonstrate the research workflow from a user request through planning, tool execution, evidence collection, quality control, and the human approval gate.

## Suggested duration: 8–10 minutes

### 1. Project overview (1 minute)
- Introduce MarketMind AI as an autonomous business research agent.
- Explain the planner, tool registry and dispatcher, evidence/source stores, quality-control checks, report generation, and human approval gate.
- Point to `docs/architecture.mmd` and `docs/technical_report.md`.

### 2. Configuration and security (1 minute)
- Show `.env.example`, `requirements.txt`, and the README setup instructions.
- Explain that the actual `.env` file contains the API key and must not be shown, shared, or included in the submission ZIP.
- Explain that retrieved web content is treated as untrusted data, not instructions.

### 3. Run a complete research request (3 minutes)
- Run `python -m src.main`.
- Enter a research request with a clear scope and a request to distinguish facts from inferences and report evidence gaps.
- Show the generated research plan and the questions the agent intends to investigate.
- Show tool-call logs and the saved source/evidence records.
- Explain that search results are source candidates; they are not automatically verified evidence.

### 4. Demonstrate a recovered failure and uncertainty (2 minutes)
- Show an actual recorded tool failure, such as a retrieval HTTP 429 or a search provider returning no results.
- Show that the workflow continues where possible and records the limitation rather than treating the failed retrieval as successful evidence.
- Show the uncertainty or coverage-gap findings from the actual run.
- Do not edit out failures or describe a partial run as fully successful.

### 5. Quality control and approval gate (1–2 minutes)
- Show the QC findings for the Pakistan EV research run.
- Explain why the report cannot be approved when required questions remain unanswered or coverage gaps persist.
- Do not approve or publish the QC-failed report.
- If demonstrating approval, rejection, or another reviewer decision, use an actual run and record its real outcome. Do not claim a decision path works unless you have verified it.

### 6. Code walkthrough (about 90 seconds)
- `src/main.py`: workflow orchestration and approval gate.
- `src/tools/registry.py` and `src/tools/dispatcher.py`: tool registration, permissions, argument validation, and call budgets.
- Evidence/source storage and final report schemas.
- Tests covering validation, tool failures, evidence traceability, QC, and approval behavior.

## Evidence to capture during the demo
- Research request and generated plan.
- Tool-call logs showing successful calls and at least one real failure.
- Saved source and evidence records with provenance.
- QC output showing an uncertainty or coverage gap.
- Human approval gate showing the actual decision.
- Test output and the project documentation.

## Important accuracy rules
- Use real run IDs, logs, reports, and test output.
- Do not expose API keys or other secrets.
- Do not call a QC-failed report approved or published.
- Distinguish unit-test results from the separate 18-case evaluation suite.
- Clearly disclose incomplete functionality, including any reviewer decisions not implemented or verified.
