# Input Contract

OCI Savings Autopilot works best with exported data. It does not require live OCI access.

## Cost Report CSV

Supported formats:

- OCI proprietary cost report CSV
- FOCUS cost report CSV, including `.csv.gz`
- Simple custom CSV with resource, service, cost, and time columns

Useful columns, case-insensitive:

- `resource_id`, `resource_ocid`, `resourceid`, `resource`
- FOCUS `ResourceId`
- `resource_name`, `name`
- FOCUS `ResourceName`
- `service`, `service_name`
- FOCUS `ServiceName`, `ServiceCategory`
- `product_description`, `sku`, `description`
- `compartment`, `compartment_name`
- FOCUS `SubAccountName`
- `region`
- FOCUS `RegionName`, `RegionId`, `AvailabilityZone`
- FOCUS `ChargeCategory`
- `cost`, `net_cost`, `billed_cost`, `amount`
- FOCUS `BilledCost`, `EffectiveCost`, `ListCost`, `ContractedCost`
- `usage_start`, `usage_date`, `date`, `time`
- FOCUS `Tags`
- tag columns such as `tag_owner`, `tag_environment`, `tag_application`

## Cloud Advisor Export

Supported formats:

- JSON list of recommendations
- CSV export

Useful fields:

- `category`
- `recommendation`
- `description`
- `resource_id`
- `resource_name`
- `estimated_monthly_savings`
- `estimatedCostSaving`, `estimatedMonthlySavings`
- `status`
- `action`

## Inventory JSON

Supported shape:

```json
{
  "resources": [
    {
      "id": "ocid1.instance...",
      "name": "dev-app-01",
      "type": "compute_instance",
      "service": "Compute",
      "lifecycle_state": "RUNNING",
      "compartment": "dev",
      "region": "us-ashburn-1",
      "monthly_cost": 120,
      "cpu_avg_percent": 3,
      "attached": true,
      "tags": {
        "environment": "dev",
        "owner": "apps-team",
        "application": "billing"
      }
    }
  ]
}
```

Top-level arrays are also supported.

## Minimum Useful Input

At least one of the following:

- Cost report CSV
- Cloud Advisor export
- Inventory JSON with monthly cost fields

If only inventory is available and no cost is present, produce a risk/effort cleanup backlog but mark savings as `Needs cost report`.

## Output Ledger

`savings_ledger.csv` includes a `remediation_template` column. These values are review-only templates and must be treated as non-executed guidance until a human owner approves the exact action.
