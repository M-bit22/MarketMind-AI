# MarketMind AI — Technical Report

## 1. Project overview

MarketMind AI is a research agent intended to turn a business research request into a structured plan, gather source material, store evidence with provenance, check report quality, and require human review before publication.

The current implementation uses the Google Gemini Developer API through the `google-genai` SDK. The original assignment specifies OpenAI integration, so this provider substitution must be approved by the instructor and documented.

## 2. Architecture

The system follows this sequence:

1. Receive a research request.
2. Create a structured research plan.
3. Maintain state during a bounded research loop.
4. Dispatch tool calls through schema validation and call-budget checks.
5. Search for and retrieve source material.
6. Store source records and extracted evidence.
7. Generate a structured draft report.
8. Run quality-control checks.
9. Request a human decision.
10. Publish only when the approval gate records an approval.

The architecture diagram is maintained in `architecture.mmd`. It should be kept synchronized with the actual implementation.

## 3. Model and provider

The implementation uses the Gemini API, with configuration read from environment variables. The API key belongs in `.env` and must not be committed, printed in logs, or included in screenshots or the submission archive.

The configured model is selected through `GEMINI_MODEL`. Record the exact model and generation settings used in the final demonstration. A successful API request proves connectivity only; it does not establish research accuracy or reliable agent behavior.

The original assignment's OpenAI requirement remains a known deviation pending instructor approval.

## 4. Tool interface and validation

The tool registry contains six tools:

- `search_information`
- `retrieve_document`
- `calculate_metric`
- `compare_companies`
- `save_research`
- `generate_report`

Tool definitions, permissions, call limits, input-size limits, and abuse considerations are documented in `tool_definitions.md`.

The dispatcher validates arguments before execution and returns structured errors for invalid calls and other rejected operations. The application should continue to enforce bounds on inputs, reject unknown tools, and prevent a draft-generation tool from bypassing the publication approval gate.

## 5. State and evidence management

Research state is maintained during execution. Source records and evidence are stored as JSON Lines files under run-specific directories. Tool-call and usage records provide additional run-level traceability.

Evidence should preserve the source reference and enough provenance to identify where a claim originated. A report should distinguish facts from inferences, recommendations, and uncertainty. Missing evidence should be represented as a limitation or coverage gap rather than replaced with an invented fact.

The saved artifacts should be inspected before asserting that every finding is traceable or that all evidence checks work in every scenario.

## 6. Quality control and publication

The report schema constrains finding types, evidence IDs, confidence values, and coverage status. The research workflow also performs quality control before presenting a report for approval.

The human approval gate is a critical control: a draft that fails quality control must not be approved or published. The final demonstration should show the approval decision and the resulting publication behavior.

The currently demonstrated main interaction asks for approval or rejection. Support for the assignment's other decisions—requesting more research and modifying scope—must be confirmed in the implementation and tested before being claimed as complete.

## 7. Failure handling: Pakistan EV research run

Run ID: `7d3601a0d0c3`

The Pakistan electric-vehicle research run encountered external search/retrieval failures and a source-registration validation issue involving an excessively long URL. The workflow continued and saved source/evidence artifacts, but quality control reported coverage gaps for market growth, government policy, and key challenges.

The run was not approved or published. Its artifacts are preserved in `submission_evidence/ev_partial_run/`.

This run is evidence of a partial workflow with failures and a quality-control stop. It is not evidence of a fully successful research outcome. The saved logs should be checked when preparing the final demonstration and evaluation record.

## 8. Testing and evaluation

The latest recorded automated test command is `python -m pytest -q`, with 109 passed and 0 failed in 2.35 seconds on 2026-10-29.

Automated unit tests and the assignment's 18 evaluation scenarios are separate measures. The 18-case evaluation table must record only cases that have actually been run. For each case, retain the run ID, relevant log reference, observed result, verdict, and failure attribution where applicable.

Five selected failure cases must be repeated at least three times each, with each attempt recorded. Do not infer that a scenario passed merely because a related unit test passed.

## 9. Security considerations

- Keep API credentials in environment variables and out of source control.
- Validate tool names and argument schemas before dispatch.
- Enforce per-tool call and input limits.
- Restrict file paths and identifiers to safe formats.
- Treat retrieved documents as untrusted data, never as instructions.
- Preserve source provenance and label uncertainty.
- Do not publish reports before explicit human approval.
- Avoid logging secrets or unnecessary sensitive content.
- Record failures and stop cleanly when budgets or retry limits are reached.

Request-borne and retrieved-content prompt-injection resistance must be supported by explicit test evidence before being described as fully verified.

## 10. Limitations and remaining work

The current research run demonstrates that external search sources can fail, rate-limit requests, return poor coverage, or produce problematic URLs. The quality of generated findings depends on the available evidence, and reports must not be treated as verified merely because they are syntactically valid.

Remaining work includes completing the 18-case evaluation and repeat trials, verifying all human-review decisions, capturing at least eight genuine screenshots, preparing the demonstration, and performing a clean submission-archive check.

## 11. Reproducibility

Follow `README.md` for environment setup and execution. Use the pinned dependency list once dependency versions have been verified in a clean environment. Never include `.env`, API keys, or other credentials in the submitted archive.
