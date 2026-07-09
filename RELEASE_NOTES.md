# OCI Savings Autopilot Release Notes

## v0.1.0 - 2026-07-07

### Release Summary

OCI Savings Autopilot v0.1.0 is the first production-ready local release of the read-only OCI FinOps analysis plugin. It analyzes exported OCI cost reports, FOCUS cost data, Cloud Advisor recommendations, and offline inventory to produce a customer-ready savings report and prioritized savings ledger.

### Intended Users

- OCI cloud architects
- FinOps practitioners
- Presales and customer engineering teams
- Operations teams preparing OCI cost optimization backlogs

### Key Capabilities

- Read-only offline analysis with no OCI API calls and no resource changes.
- OCI cost report and FOCUS CSV ingestion, including `.csv.gz`.
- Cloud Advisor JSON/CSV recommendation ingestion.
- Offline inventory JSON analysis for storage cleanup, non-prod scheduling, rightsizing, lifecycle policy gaps, and missing cost tags.
- Conservative savings totals that avoid double-counting overlapping recommendations for the same resource.
- Customer-ready Markdown report and CSV savings ledger.
- Review-only remediation templates prefixed with `REVIEW_ONLY_APPROVAL_REQUIRED`.

### Data Sources Supported

- OCI proprietary cost report CSV.
- FOCUS cost report CSV or `.csv.gz`.
- Cloud Advisor recommendation exports in JSON or CSV.
- Offline inventory JSON from approved discovery processes.

### FOCUS Compatibility

This release explicitly supports common FOCUS dimensions and cost fields:

- `ResourceId`
- `ResourceName`
- `ServiceName`
- `ServiceCategory`
- `RegionName`
- `RegionId`
- `AvailabilityZone`
- `ChargeCategory`
- `BilledCost`
- `EffectiveCost`
- `ListCost`
- `ContractedCost`
- `Tags`

### Safety Model

The plugin is read-only by design:

- It does not call OCI APIs.
- It does not run OCI CLI commands.
- It does not run Terraform actions.
- It does not delete, resize, stop, start, tag, or mutate customer resources.
- Remediation snippets are advisory templates only and require separate human approval before use.

### Validation Evidence

Validated locally on 2026-07-07:

- Python compile check passed.
- Unit test suite passed with 6 tests.
- Built-in sample run generated `savings_report.md` and `savings_ledger.csv`.
- Public FOCUS sample cost-only run generated report outputs.
- Public FOCUS sample plus Cloud Advisor-style recommendation run generated one savings opportunity.
- Plugin manifest validation passed.

### Test Coverage

Current regression tests cover:

- Gzip FOCUS CSV ingestion.
- Zero-cost billing rows that must not fall through to list cost.
- Missing CPU telemetry safety.
- Invalid CPU telemetry safety.
- FOCUS dimension mapping.
- Review-only remediation template output.

### Known Limitations

- Billing-only cost reports can validate parsing and cost context, but they do not prove savings without inventory or Cloud Advisor evidence.
- Savings are estimates and must be reviewed by the customer or service owner.
- Remediation templates require owner approval and environment-specific target values.
- Live OCI discovery is intentionally out of scope for the default workflow.

### Dispatch Checklist

- Confirm `.codex-plugin/plugin.json` version is `0.1.0`.
- Run the unit test suite.
- Run the local sample analyzer.
- Run at least one FOCUS CSV or `.csv.gz` test.
- Confirm `savings_report.md` explains assumptions and gaps.
- Confirm `savings_ledger.csv` includes evidence, approval, rollback, and remediation template columns.
- Confirm no customer secrets or confidential exports are bundled.
- Confirm any marketplace entry points to the correct plugin path.

## Future Release Note Template

```markdown
## vX.Y.Z - YYYY-MM-DD

### Release Summary

Short business summary of what changed and why it matters.

### Added

- New capability or supported data source.

### Changed

- Existing behavior that changed.

### Fixed

- Bug fix or reliability improvement.

### Safety Notes

- Read-only guarantees, approval requirements, or data handling updates.

### Validation Evidence

- Tests run.
- Sample datasets used.
- Plugin validation result.

### Known Limitations

- Remaining gaps or assumptions.

### Upgrade Notes

- Any user action needed after upgrading.
```
