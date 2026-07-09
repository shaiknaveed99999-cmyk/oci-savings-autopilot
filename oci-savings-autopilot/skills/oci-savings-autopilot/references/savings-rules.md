# Savings Rules

Use conservative estimates and keep customer safety visible.

## Scoring

Priority score:

```text
score = monthly_savings_weight + confidence_weight + low_risk_weight + low_effort_weight
```

Sort by:

1. Highest estimated savings
2. Highest confidence
3. Lowest risk
4. Lowest effort

## Rules

### Cloud Advisor Recommendation

If Cloud Advisor gives an estimated monthly savings value, use it as the primary estimate and mark confidence `High`.

### Unattached Block or Boot Volume

If inventory shows a block or boot volume with `attached=false`, mark it as a cleanup candidate.

- Risk: Medium
- Effort: Low
- Approval: storage owner approval and backup/retention check
- Rollback: restore from backup/snapshot if deletion is later approved

### Non-Prod Always-On Compute

If a resource is compute, environment is `dev`, `test`, `uat`, `sandbox`, or `nonprod`, and it appears to run continuously, recommend schedule-based stop/start or autoscaling.

- Estimate: up to 60% of monthly compute cost for weekday business-hours usage
- Risk: Medium
- Effort: Medium
- Approval: application owner confirms operating hours
- Rollback: remove schedule or restore previous instance pool size

### Oversized Compute

If average CPU is below 10% and monthly cost is present, recommend rightsizing review.

- Estimate: 25% of monthly compute cost unless a Cloud Advisor estimate is available
- Risk: Medium
- Effort: Medium
- Approval: performance owner review
- Rollback: revert to previous shape

### Object Storage Lifecycle Gap

If Object Storage has high monthly cost and no lifecycle policy evidence, recommend lifecycle rules.

- Estimate: 15% of monthly object storage cost until exact access patterns are known
- Risk: Low to Medium
- Effort: Medium
- Approval: data owner retention and restore requirements
- Rollback: disable lifecycle rule before transition/deletion window

### Missing Cost Tags

If a high-cost resource lacks owner, application, or environment tags, mark as governance opportunity.

- Estimate: no direct savings unless paired with cleanup
- Risk: Low
- Effort: Low
- Approval: tagging standard owner
- Business value: accountability and faster future savings

## Never Claim

- Guaranteed savings.
- Safe deletion without owner approval.
- Customer compliance approval.
- That a resource is unused based only on name.

