# OCI Savings Autopilot

OCI Savings Autopilot is a read-only Codex plugin for OCI FinOps discovery. It turns exported cost reports, Cloud Advisor findings, tags, and offline inventory into a customer-ready savings ledger.

## What It Produces

- Executive savings summary
- Prioritized opportunities with estimated monthly savings
- Risk, effort, approval, evidence, and rollback notes
- Implementation backlog CSV
- Review-only remediation templates for engineering approval
- Follow-up questions when data is missing

## Core Workflow

Use the `oci-savings-autopilot` skill and provide one or more offline inputs:

- OCI cost report CSV or FOCUS CSV, including `.csv.gz`
- Cloud Advisor recommendation export as JSON or CSV
- Offline inventory JSON from OCI CLI, Terraform state, or another approved discovery process

The plugin must not change OCI resources. It can draft implementation steps, Terraform suggestions, or CLI command templates, but execution requires explicit user approval outside this read-only workflow. Ledger remediation templates are prefixed with `REVIEW_ONLY_APPROVAL_REQUIRED`.

## Local Analyzer

```powershell
python .\scripts\oci_savings_autopilot.py `
  --cost-report .\samples\sample_cost_report.csv `
  --inventory .\samples\sample_inventory.json `
  --cloud-advisor .\samples\sample_cloud_advisor.json `
  --output-dir .\output
```

Outputs:

- `savings_report.md`
- `savings_ledger.csv`

## Release Notes

See `RELEASE_NOTES.md` for version history, validation evidence, known limitations, and dispatch checklist.
