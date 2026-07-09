# Customer Report Template

Use this structure for customer-facing summaries.

```md
# OCI Savings Autopilot Report

## Executive Summary

We found <count> savings opportunities with an estimated monthly savings of <amount>. The strongest opportunities are <short list>.

## Top Savings Actions

| Priority | Action | Estimated Monthly Savings | Confidence | Risk | Approval Needed |
|---|---|---:|---|---|---|
| 1 | <action> | <amount> | <High/Medium/Low> | <Low/Medium/High> | <owner approval> |

## Savings Ledger

| Resource | Service | Problem | Recommendation | Evidence | Monthly Savings |
|---|---|---|---|---|---:|

## Implementation Plan

1. Confirm owner and business hours.
2. Validate backup/rollback requirement.
3. Apply change in non-prod or pilot compartment.
4. Measure bill/performance for one billing cycle.
5. Roll out to similar resources.

## Rollback Plan

Describe how to reverse each change before implementation.

## Assumptions and Gaps

- Savings are estimates.
- Missing data: <list>.
- No resources were changed by this analysis.
```

