# MarketMind AI — Tool Definitions and Abuse Analysis

## 1. Purpose

The tool registry defines six tools. Each tool has a permission level, per-run call budget, maximum serialized input size, and an argument schema enforced by the dispatcher.

Permissions:
- `read`: retrieve information from registered sources.
- `compute`: calculate or compare using supplied inputs and evidence.
- `write`: perform or prepare research-artifact operations.

The dispatcher rejects unknown tools, invalid argument objects, oversized inputs, exhausted budgets, and calls requiring approval when approval has not been supplied.

## 2. Tool specifications

### 2.1 `search_information`

- **Permission:** `read`
- **Maximum calls per run:** 8
- **Maximum serialized input:** 2,000 characters
- **Human approval:** Not required
- **Arguments:**
  - `query`: string, 3–1,000 characters; extra properties forbidden.
- **Handler:** `src/tools/search.py`, connected by `src/tools/factory.py`.

**Abuse analysis**
- Risk: broad, irrelevant, or adversarial search queries consume the research budget.
- Risk: search snippets may contain inaccurate claims or prompt-injection text.
- Controls: argument validation, per-run budget, source registration, and provenance collection.
- Further verification: confirm URL and content handling in the search implementation; retrieved content must be treated as untrusted data, not instructions.

### 2.2 `retrieve_document`

- **Permission:** `read`
- **Maximum calls per run:** 8
- **Maximum serialized input:** 2,000 characters
- **Human approval:** Not required
- **Arguments:**
  - `source_ref`: string, 1–300 characters; extra properties forbidden.
- **Handler:** `src/tools/retrieve.py`, connected by `src/tools/factory.py`.

**Abuse analysis**
- Risk: an attacker attempts to make the system fetch an arbitrary URL or an internal network resource.
- Current control: the factory looks up the reference in the source store and only permits registered search results.
- Further verification: inspect URL scheme, redirect, DNS/IP, response-size, timeout, and content-type controls in the retrieval implementation. A registered URL alone does not guarantee SSRF protection.

### 2.3 `calculate_metric`

- **Permission:** `compute`
- **Maximum calls per run:** 10
- **Maximum serialized input:** 2,000 characters
- **Human approval:** Not required
- **Arguments:**
  - `metric_name`: one of `percentage`, `growth_rate`, `ratio`.
  - `numerator`: finite number.
  - `denominator`: finite, nonzero number.
  - Extra properties are forbidden.
- **Handler:** `src/tools/calculator.py`.

**Abuse analysis**
- Risk: invalid or misleading numeric inputs produce misleading calculations.
- Controls: strict argument validation, an allow-list of metric names, rejection of non-finite numbers, and division-by-zero protection.
- Limitation: safe arithmetic does not prove that the supplied inputs are factually correct. Calculations should retain their input values and provenance.

### 2.4 `compare_companies`

- **Permission:** `compute`
- **Maximum calls per run:** 5
- **Maximum serialized input:** 4,000 characters
- **Human approval:** Not required
- **Arguments:**
  - `company_names`: list of 2–10 strings.
  - `evidence_ids`: list of 1–50 strings.
  - Extra properties are forbidden.
- **Handler:** `src/tools/compare.py`, connected by `src/tools/factory.py`.

**Abuse analysis**
- Risk: the comparison may imply that an attribute is known when the evidence does not establish it.
- Controls: bounded lists and evidence-store access.
- Further verification: ensure every comparison cell can be traced to supporting evidence, and missing attributes are labelled as not established rather than guessed.

### 2.5 `save_research`

- **Permission:** `write`
- **Maximum calls per run:** 3
- **Maximum serialized input:** 10,000 characters
- **Registry approval flag:** Required
- **Arguments:**
  - `artifact_type`: string, 1–100 characters.
  - `artifact_id`: string, 1–100 characters.
  - Extra properties are forbidden.
- **Current factory status:** Placeholder. The factory handler raises `NotImplementedError`.

**Abuse analysis**
- Risk: unvalidated or unauthorized data is persisted as a trusted research artifact.
- Required controls before enabling: allow-list artifact types, validate the artifact against its schema, verify referenced evidence, restrict writes to the current run directory, and avoid overwriting unrelated files.
- Approval note: distinguish saving intermediate research data from publishing a final report. Do not weaken the final publication approval gate to enable this tool.

### 2.6 `generate_report`

- **Permission:** `write`
- **Maximum calls per run:** 2
- **Maximum serialized input:** 15,000 characters
- **Registry approval flag:** Required
- **Arguments:**
  - `report_id`: string, 1–100 characters.
  - `evidence_ids`: list of 1–100 strings.
  - Extra properties are forbidden.
- **Current factory status:** Placeholder. The factory handler raises `NotImplementedError`.

**Abuse analysis**
- Risk: a report is generated with unsupported claims, invalid evidence references, or incomplete coverage.
- Required controls before enabling: validate report structure, check evidence IDs, enforce coverage checks, and preserve uncertainty and limitations.
- Approval note: report generation for human review is a different operation from publication. The existing main workflow generates a draft before the human approval decision. Align this tool's permission flag with that workflow after adding regression tests; final publication must still require explicit approval.

## 3. Dispatcher-wide controls

The current dispatcher implements:
- Unknown-tool rejection.
- JSON-object argument requirement.
- Maximum serialized-input length.
- Per-tool call budgets.
- Human-approval checks for tools marked as requiring approval.
- Pydantic argument validation with extra properties forbidden.
- Structured errors for rejected calls and execution failures.
- JSON Lines tool-call logging.

The call counter is maintained in the dispatcher instance. Confirm whether run state is persisted and resumed safely before claiming that budgets survive process restarts.

## 4. Important limitations and verification work

This document describes the inspected registry, dispatcher, and factory. It does not claim that every registered handler is complete.

Before submission:
1. Implement and test `save_research`.
2. Implement and test `generate_report`, or document and justify the separate report workflow if the assignment permits that design.
3. Verify URL and redirect protections in retrieval.
4. Verify timeouts, response-size limits, and error recovery.
5. Test malformed arguments, out-of-bounds values, unknown tools, and exhausted budgets.
6. Test content-borne and request-borne prompt injection.
7. Record actual test run IDs, logs, verdicts, repeated failure-case runs, and component attribution in the evaluation deliverables.

Do not mark a control as verified until its behavior has been tested.
