---
name: oci-savings-autopilot
description: Analyze exported OCI cost reports, Cloud Advisor findings, tags, and offline inventory to produce a read-only savings ledger, implementation backlog, and executive summary.
---

# OCI Savings Autopilot

Use this skill when the user wants OCI cost optimization, FinOps analysis, savings estimates, waste reduction, rightsizing, cleanup planning, or a customer-ready OCI savings report.

## Safety Rules

- Stay read-only by default.
- Do not run OCI CLI, Terraform apply, delete resources, resize resources, stop/start instances, update lifecycle policies, change budgets, or modify tags unless the user explicitly asks and confirms the exact action.
- Do not ask for passwords, API keys, private keys, wallet files, or customer secrets.
- Prefer offline inputs: OCI cost report CSV, FOCUS CSV, Cloud Advisor export, inventory JSON, Terraform plan/state, or user-provided spreadsheets.
- If live OCI discovery is needed, ask first and explain that exported files are safer for the first pass.
- Treat cost savings as estimates. Show assumptions and evidence.
- Treat remediation templates as review aids only. Do not run generated CLI/IaC snippets without separate explicit approval.

## Required References

Read these files before producing a savings report:

- `references/input-contract.md`
- `references/savings-rules.md`
- `references/customer-report-template.md`

## Workflow

1. Collect available offline inputs.
   - Cost report CSV is the best starting point.
   - Cloud Advisor export gives stronger savings estimates.
   - Inventory adds cleanup and tagging opportunities.
2. Run the local analyzer when files are available:

```powershell
python .\plugins\oci-savings-autopilot\scripts\oci_savings_autopilot.py `
  --cost-report <path-to-cost-report.csv> `
  --inventory <path-to-inventory.json> `
  --cloud-advisor <path-to-cloud-advisor.json-or.csv> `
  --output-dir <output-folder>
```

3. Review `savings_report.md` and `savings_ledger.csv`.
4. Explain the findings in simple business language:
   - What is wasting money
   - Why it matters
   - Estimated monthly savings
   - Risk level
   - Approval needed
   - Rollback path
5. If inputs are incomplete, produce a partial report and ask for the missing file that would improve confidence.

## Opportunity Types

Prioritize opportunities in this order:

1. Confirmed Cloud Advisor savings.
2. Unattached storage and stale boot/block volumes.
3. Non-prod compute running continuously.
4. Oversized compute or databases with low utilization evidence.
5. Object Storage buckets missing lifecycle policy.
6. High-cost resources with missing owner/application/environment tags.
7. Forecasted budget overruns.

## Output Contract

Every response should include:

- Top 3 savings opportunities.
- Estimated monthly savings when available.
- What evidence supports each recommendation.
- What the customer must approve before implementation.
- Whether any remediation template is present, and that it is not executed by this plugin.
- A short caveat if data is partial.

Use simple language. Avoid making the customer read raw OCI terminology before telling them the business impact.
