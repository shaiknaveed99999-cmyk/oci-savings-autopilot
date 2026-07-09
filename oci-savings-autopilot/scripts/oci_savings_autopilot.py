#!/usr/bin/env python3
"""Offline OCI savings analyzer.

This script intentionally performs no OCI API calls. It reads exported CSV/JSON
evidence and writes a Markdown report plus a CSV savings ledger.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


MONEY_FIELDS = (
    "cost",
    "cost/myCost",
    "cost/attributedCost",
    "net_cost",
    "billed_cost",
    "BilledCost",
    "EffectiveCost",
    "ListCost",
    "ContractedCost",
    "amount",
    "monthly_cost",
    "estimated_monthly_savings",
    "estimated_savings",
)

RESOURCE_ID_FIELDS = (
    "resource_id",
    "resource_ocid",
    "resourceid",
    "ResourceId",
    "product/resourceId",
    "ocid",
    "resource",
    "resource name",
)
INVENTORY_RESOURCE_ID_FIELDS = (*RESOURCE_ID_FIELDS, "id")
RESOURCE_NAME_FIELDS = ("resource_name", "ResourceName", "name", "display_name")
SERVICE_FIELDS = ("service", "service_name", "ServiceName", "product/service")
RESOURCE_TYPE_FIELDS = ("type", "resource_type", "ResourceType", "kind")
COMPARTMENT_FIELDS = ("compartment", "compartment_name", "SubAccountName", "product/compartmentName")
REGION_FIELDS = ("region", "region_name", "Region", "RegionName", "RegionId", "product/region")
AVAILABILITY_ZONE_FIELDS = ("availability_zone", "AvailabilityZone", "zone", "zone_name")
SERVICE_CATEGORY_FIELDS = ("service_category", "ServiceCategory", "product/serviceCategory")
CHARGE_CATEGORY_FIELDS = ("charge_category", "ChargeCategory")
CPU_FIELDS = ("cpu_avg_percent", "avg_cpu", "cpu_utilization", "cpu_percent")
ADVISOR_SAVINGS_FIELDS = (
    "estimated_monthly_savings",
    "estimated_savings",
    "estimatedCostSaving",
    "estimated_cost_saving",
    "estimatedMonthlySavings",
    "savings",
)

NON_PROD_VALUES = {"dev", "test", "uat", "qa", "sandbox", "nonprod", "non-prod"}


@dataclass
class Resource:
    id: str
    name: str = ""
    service: str = ""
    type: str = ""
    compartment: str = ""
    region: str = ""
    availability_zone: str = ""
    service_category: str = ""
    charge_category: str = ""
    monthly_cost: float = 0.0
    cpu_avg_percent: float | None = None
    attached: bool | None = None
    lifecycle_policy: bool | None = None
    always_on: bool | None = None
    lifecycle_state: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Opportunity:
    priority: int
    category: str
    resource_id: str
    resource_name: str
    service: str
    problem: str
    recommendation: str
    monthly_savings: float | None
    confidence: str
    risk: str
    effort: str
    approval_needed: str
    evidence: str
    rollback: str
    remediation_template: str = ""


def norm_key(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower()).strip("_")


def compact_key(value: str) -> str:
    return norm_key(value).replace("_", "")


def first_value(row: dict[str, Any], names: Iterable[str], default: Any = "") -> Any:
    normalized = {norm_key(k): v for k, v in row.items()}
    compacted = {compact_key(k): v for k, v in row.items()}
    for name in names:
        key = norm_key(name)
        if key in normalized and normalized[key] not in (None, ""):
            return normalized[key]
        key = compact_key(name)
        if key in compacted and compacted[key] not in (None, ""):
            return compacted[key]
    return default


def parse_money(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1", "attached", "enabled"}:
        return True
    if text in {"false", "no", "n", "0", "unattached", "disabled"}:
        return False
    return None


def read_csv(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def collect_costs(paths: list[Path]) -> dict[str, float]:
    costs: dict[str, float] = defaultdict(float)
    for path in paths:
        for row in read_csv(path):
            resource_id = str(first_value(row, RESOURCE_ID_FIELDS))
            resource_name = str(first_value(row, RESOURCE_NAME_FIELDS, resource_id))
            key = resource_id or resource_name
            amount = 0.0
            for field_name in MONEY_FIELDS:
                raw_amount = first_value(row, (field_name,), None)
                if raw_amount not in (None, ""):
                    amount = parse_money(raw_amount)
                    break
            if key:
                costs[key] += amount
    return dict(costs)


def extract_tags(row: dict[str, Any]) -> dict[str, str]:
    tags: dict[str, str] = {}
    raw_tags = first_value(row, ("tags", "Tags"), "")
    if isinstance(raw_tags, dict):
        tags.update({str(k).lower(): str(v) for k, v in raw_tags.items() if v not in (None, "")})
    elif isinstance(raw_tags, str) and raw_tags.strip().startswith(("{", "[")):
        try:
            parsed_tags = json.loads(raw_tags)
        except json.JSONDecodeError:
            parsed_tags = {}
        if isinstance(parsed_tags, dict):
            tags.update({str(k).lower(): str(v) for k, v in parsed_tags.items() if v not in (None, "")})
    for key, value in row.items():
        normalized = norm_key(key)
        if normalized.startswith("tag_") and value not in (None, ""):
            tags[normalized[4:]] = str(value)
        if normalized.startswith("tags_") and value not in (None, ""):
            tags[normalized[5:]] = str(value)
    for alias in ("environment", "env", "owner", "application", "app"):
        value = first_value(row, (alias,), "")
        if value:
            tags[alias] = str(value)
    if "env" in tags and "environment" not in tags:
        tags["environment"] = tags["env"]
    if "app" in tags and "application" not in tags:
        tags["application"] = tags["app"]
    return tags


def resource_from_row(row: dict[str, Any]) -> Resource:
    tags = extract_tags(row)
    resource_id = str(first_value(row, INVENTORY_RESOURCE_ID_FIELDS, ""))
    name = str(first_value(row, RESOURCE_NAME_FIELDS, resource_id))
    monthly_cost = 0.0
    for field_name in MONEY_FIELDS:
        raw_amount = first_value(row, (field_name,), None)
        if raw_amount not in (None, ""):
            monthly_cost = parse_money(raw_amount)
            break
    cpu_avg = parse_optional_float(first_value(row, CPU_FIELDS, ""))
    return Resource(
        id=resource_id or name,
        name=name,
        service=str(first_value(row, SERVICE_FIELDS, "")),
        type=str(first_value(row, RESOURCE_TYPE_FIELDS, "")),
        compartment=str(first_value(row, COMPARTMENT_FIELDS, "")),
        region=str(first_value(row, REGION_FIELDS, "")),
        availability_zone=str(first_value(row, AVAILABILITY_ZONE_FIELDS, "")),
        service_category=str(first_value(row, SERVICE_CATEGORY_FIELDS, "")),
        charge_category=str(first_value(row, CHARGE_CATEGORY_FIELDS, "")),
        monthly_cost=monthly_cost,
        cpu_avg_percent=cpu_avg,
        attached=parse_bool(first_value(row, ("attached", "is_attached"), "")),
        lifecycle_policy=parse_bool(first_value(row, ("lifecycle_policy", "has_lifecycle_policy"), "")),
        always_on=parse_bool(first_value(row, ("always_on", "runs_24x7", "running_24x7"), "")),
        lifecycle_state=str(first_value(row, ("lifecycle_state", "state"), "")),
        tags=tags,
    )


def collect_inventory(paths: list[Path]) -> dict[str, Resource]:
    resources: dict[str, Resource] = {}
    for path in paths:
        payload = read_json(path)
        rows = payload.get("resources", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                resource = resource_from_row(row)
                resources[resource.id] = resource
    return resources


def collect_cloud_advisor(paths: list[Path]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for path in paths:
        if is_csv_path(path):
            recommendations.extend(read_csv(path))
            continue
        payload = read_json(path)
        if isinstance(payload, list):
            recommendations.extend([item for item in payload if isinstance(item, dict)])
        elif isinstance(payload, dict):
            rows = payload.get("recommendations") or payload.get("items") or []
            recommendations.extend([item for item in rows if isinstance(item, dict)])
    return recommendations


def money(value: float | None) -> str:
    if value is None:
        return "Needs cost report"
    if math.isclose(value, 0.0):
        return "$0"
    return f"${value:,.2f}"


def review_only_template(command: str) -> str:
    return f"REVIEW_ONLY_APPROVAL_REQUIRED: {command}"


def remediation_for_cloud_advisor(row: dict[str, Any], resource_id: str, recommendation: str) -> str:
    service = str(first_value(row, ("service", "category", "ServiceName"), "")).lower()
    text = f"{service} {recommendation} {first_value(row, ('action', 'recommended_action'), '')}".lower()
    resource = resource_id or "<RESOURCE_OCID>"
    if "compute" in text or "instance" in text or resource.startswith("ocid") and ".instance." in resource:
        return review_only_template(
            f"oci compute instance update --instance-id {resource} --shape <APPROVED_TARGET_SHAPE>"
        )
    if "volume" in text or ".volume." in resource:
        return review_only_template(f"oci bv volume delete --volume-id {resource}")
    if "bucket" in text or "object" in text:
        bucket = first_value(row, ("bucket_name", "resource_name", "name"), "<BUCKET_NAME>")
        return review_only_template(
            f"oci os object-lifecycle-policy put --bucket-name {bucket} --items '<APPROVED_POLICY_JSON>'"
        )
    return review_only_template("Use the matching OCI Console, CLI, or IaC change after owner approval.")


def cloud_advisor_opportunities(recommendations: list[dict[str, Any]]) -> list[Opportunity]:
    output: list[Opportunity] = []
    for row in recommendations:
        status = str(first_value(row, ("status", "lifecycle_state"), "")).lower()
        if status and status not in {"pending", "open", "active", "new"}:
            continue
        resource_id = str(first_value(row, RESOURCE_ID_FIELDS, ""))
        resource_name = str(first_value(row, RESOURCE_NAME_FIELDS, resource_id))
        recommendation = str(first_value(row, ("recommendation", "title", "description"), "Review Cloud Advisor recommendation."))
        savings = parse_money(first_value(row, ADVISOR_SAVINGS_FIELDS, ""))
        output.append(
            Opportunity(
                priority=0,
                category="Cloud Advisor",
                resource_id=resource_id,
                resource_name=resource_name,
                service=str(first_value(row, (*SERVICE_FIELDS, "category"), "OCI")),
                problem=recommendation,
                recommendation=str(first_value(row, ("action", "recommended_action"), recommendation)),
                monthly_savings=savings if savings else None,
                confidence="High" if savings else "Medium",
                risk="Medium",
                effort="Low",
                approval_needed="Service owner approval before implementation.",
                evidence="Cloud Advisor recommendation export.",
                rollback="Use the pre-change resource configuration or Cloud Advisor history to reverse the change.",
                remediation_template=remediation_for_cloud_advisor(row, resource_id, recommendation),
            )
        )
    return output


def has_advisor_overlap(resource_id: str, opportunities: list[Opportunity], keywords: tuple[str, ...]) -> bool:
    for item in opportunities:
        if item.resource_id != resource_id:
            continue
        haystack = f"{item.problem} {item.recommendation} {item.category}".lower()
        if any(keyword in haystack for keyword in keywords):
            return True
    return False


def conservative_total(opportunities: list[Opportunity]) -> float:
    """Return a conservative savings estimate.

    Multiple recommendations can target the same resource. For executive totals,
    count only the highest direct saving per resource so the report does not
    imply that overlapping actions are fully additive.
    """
    by_resource: dict[str, float] = defaultdict(float)
    for item in opportunities:
        if not item.monthly_savings or item.monthly_savings <= 0:
            continue
        key = item.resource_id or item.resource_name or f"unknown-{item.priority}"
        by_resource[key] = max(by_resource[key], item.monthly_savings)
    return sum(by_resource.values())


def inventory_opportunities(resources: dict[str, Resource], advisor_opportunities: list[Opportunity]) -> list[Opportunity]:
    output: list[Opportunity] = []
    for resource in resources.values():
        type_text = f"{resource.type} {resource.service}".lower()
        env = resource.tags.get("environment", "").lower()
        missing_tags = [tag for tag in ("owner", "application", "environment") if not resource.tags.get(tag)]

        if ("volume" in type_text) and resource.attached is False and not has_advisor_overlap(
            resource.id, advisor_opportunities, ("volume", "storage", "unattached")
        ):
            output.append(
                Opportunity(
                    priority=0,
                    category="Storage Cleanup",
                    resource_id=resource.id,
                    resource_name=resource.name,
                    service=resource.service or "Block Volume",
                    problem="Volume appears unattached.",
                    recommendation="Confirm retention, snapshot if required, then delete the unattached volume.",
                    monthly_savings=resource.monthly_cost or None,
                    confidence="High",
                    risk="Medium",
                    effort="Low",
                    approval_needed="Storage owner confirms the volume is no longer required.",
                    evidence="Inventory shows attached=false.",
                    rollback="Restore from approved snapshot or backup if deletion is approved and later reversed.",
                    remediation_template=review_only_template(f"oci bv volume delete --volume-id {resource.id}"),
                )
            )

        if ("compute" in type_text or "instance" in type_text) and env in NON_PROD_VALUES and resource.always_on is True:
            estimate = (resource.monthly_cost * 0.60) if resource.monthly_cost else None
            output.append(
                Opportunity(
                    priority=0,
                    category="Non-Prod Scheduling",
                    resource_id=resource.id,
                    resource_name=resource.name,
                    service=resource.service or "Compute",
                    problem="Non-prod compute appears to run continuously.",
                    recommendation="Create business-hours stop/start or autoscaling schedule after owner approval.",
                    monthly_savings=estimate,
                    confidence="Medium",
                    risk="Medium",
                    effort="Medium",
                    approval_needed="Application owner confirms operating hours and exclusions.",
                    evidence=f"environment={env}, always_on=true.",
                    rollback="Remove the schedule or restore the prior instance pool size/lifecycle state.",
                    remediation_template=review_only_template(
                        f"Create an approved stop/start schedule for compute resource {resource.id}."
                    ),
                )
            )

        if (
            ("compute" in type_text or "instance" in type_text)
            and resource.cpu_avg_percent is not None
            and resource.cpu_avg_percent < 10
            and not has_advisor_overlap(resource.id, advisor_opportunities, ("right", "size", "underutilized"))
        ):
            estimate = (resource.monthly_cost * 0.25) if resource.monthly_cost else None
            output.append(
                Opportunity(
                    priority=0,
                    category="Rightsizing",
                    resource_id=resource.id,
                    resource_name=resource.name,
                    service=resource.service or "Compute",
                    problem=f"Average CPU is low at {resource.cpu_avg_percent:g}%.",
                    recommendation="Review memory and peak CPU, then downsize shape or move to flexible shape.",
                    monthly_savings=estimate,
                    confidence="Medium",
                    risk="Medium",
                    effort="Medium",
                    approval_needed="Performance owner validates peak usage and maintenance window.",
                    evidence="Inventory contains low average CPU utilization.",
                    rollback="Resize back to the previous shape.",
                    remediation_template=review_only_template(
                        f"oci compute instance update --instance-id {resource.id} --shape <APPROVED_TARGET_SHAPE>"
                    ),
                )
            )

        if ("object" in type_text or "bucket" in type_text) and resource.lifecycle_policy is False:
            estimate = (resource.monthly_cost * 0.15) if resource.monthly_cost else None
            output.append(
                Opportunity(
                    priority=0,
                    category="Object Lifecycle",
                    resource_id=resource.id,
                    resource_name=resource.name,
                    service=resource.service or "Object Storage",
                    problem="Bucket has no lifecycle policy evidence.",
                    recommendation="Define archive/delete lifecycle rules after data retention review.",
                    monthly_savings=estimate,
                    confidence="Medium",
                    risk="Low",
                    effort="Medium",
                    approval_needed="Data owner confirms retention and restore requirements.",
                    evidence="Inventory shows lifecycle_policy=false.",
                    rollback="Disable lifecycle rule before transition or deletion window.",
                    remediation_template=review_only_template(
                        f"oci os object-lifecycle-policy put --bucket-name {resource.name or '<BUCKET_NAME>'} "
                        "--items '<APPROVED_POLICY_JSON>'"
                    ),
                )
            )

        if resource.monthly_cost >= 50 and missing_tags:
            output.append(
                Opportunity(
                    priority=0,
                    category="Cost Governance",
                    resource_id=resource.id,
                    resource_name=resource.name,
                    service=resource.service or "OCI",
                    problem=f"High-cost resource is missing tags: {', '.join(missing_tags)}.",
                    recommendation="Add owner, application, and environment tags for accountability.",
                    monthly_savings=0.0,
                    confidence="High",
                    risk="Low",
                    effort="Low",
                    approval_needed="Tagging standard owner confirms values.",
                    evidence=f"monthly_cost={money(resource.monthly_cost)} and missing required tags.",
                    rollback="Remove or correct tags if owner mapping is wrong.",
                    remediation_template=review_only_template(
                        f"Add owner/application/environment tags to {resource.id} through approved IaC or service API."
                    ),
                )
            )
    return output


def rank_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    confidence_score = {"High": 3, "Medium": 2, "Low": 1}
    risk_score = {"Low": 3, "Medium": 2, "High": 1}
    effort_score = {"Low": 3, "Medium": 2, "High": 1}

    def score(item: Opportunity) -> tuple[float, int, int, int]:
        savings = item.monthly_savings or 0.0
        return (
            savings,
            confidence_score.get(item.confidence, 0),
            risk_score.get(item.risk, 0),
            effort_score.get(item.effort, 0),
        )

    ranked = sorted(opportunities, key=score, reverse=True)
    for index, item in enumerate(ranked, start=1):
        item.priority = index
    return ranked


def write_ledger(path: Path, opportunities: list[Opportunity]) -> None:
    fields = [
        "priority",
        "category",
        "resource_id",
        "resource_name",
        "service",
        "problem",
        "recommendation",
        "monthly_savings",
        "confidence",
        "risk",
        "effort",
        "approval_needed",
        "evidence",
        "rollback",
        "remediation_template",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in opportunities:
            writer.writerow({field: getattr(item, field) for field in fields})


def write_report(path: Path, opportunities: list[Opportunity], costs: dict[str, float], gaps: list[str]) -> None:
    total_savings = conservative_total(opportunities)
    direct_savings = [item for item in opportunities if item.monthly_savings and item.monthly_savings > 0]
    top = opportunities[:5]
    lines = [
        "# OCI Savings Autopilot Report",
        "",
        "## Executive Summary",
        "",
        f"Found {len(opportunities)} opportunities with conservative estimated monthly savings of {money(total_savings)}.",
        f"{len(direct_savings)} opportunities have direct savings estimates; overlapping recommendations are not added twice.",
        "No OCI resources were changed by this analysis.",
        "",
        "## Top Savings Actions",
        "",
        "| Priority | Action | Estimated Monthly Savings | Confidence | Risk | Approval Needed |",
        "|---:|---|---:|---|---|---|",
    ]
    for item in top:
        lines.append(
            f"| {item.priority} | {item.recommendation} | {money(item.monthly_savings)} | "
            f"{item.confidence} | {item.risk} | {item.approval_needed} |"
        )
    lines.extend(
        [
            "",
            "## Savings Ledger",
            "",
            "| Resource | Service | Problem | Evidence | Monthly Savings |",
            "|---|---|---|---|---:|",
        ]
    )
    for item in opportunities:
        resource = item.resource_name or item.resource_id or "Unknown resource"
        lines.append(
            f"| {resource} | {item.service} | {item.problem} | {item.evidence} | {money(item.monthly_savings)} |"
        )
    lines.extend(
        [
            "",
            "## Cost Context",
            "",
            f"Cost rows/resources loaded: {len(costs)}.",
            "",
            "## Implementation Plan",
            "",
            "1. Confirm owner, business criticality, and operating hours.",
            "2. Validate backup, retention, and rollback requirements.",
            "3. Pilot the change in non-prod or one low-risk compartment.",
            "4. Measure cost and performance for one billing cycle.",
            "5. Roll out to similar resources after customer approval.",
            "",
            "## Rollback Plan",
            "",
            "Each opportunity includes a rollback note in `savings_ledger.csv`. Do not implement cleanup or resizing without owner approval.",
            "",
            "## Assumptions and Gaps",
            "",
        ]
    )
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- No major input gaps detected for this first pass.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def existing_paths(values: list[str] | None) -> list[Path]:
    paths: list[Path] = []
    for value in values or []:
        path = Path(value)
        if path.is_dir():
            paths.extend(sorted(item for item in path.iterdir() if is_supported_input_path(item)))
        elif path.exists():
            paths.append(path)
    return paths


def is_csv_path(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".csv") or name.endswith(".csv.gz")


def is_supported_input_path(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".csv") or name.endswith(".csv.gz") or name.endswith(".json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate read-only OCI savings report from offline exports.")
    parser.add_argument("--cost-report", action="append", help="Path to OCI/FOCUS cost report CSV. Can be repeated.")
    parser.add_argument("--inventory", action="append", help="Path to offline inventory JSON. Can be repeated.")
    parser.add_argument("--cloud-advisor", action="append", help="Path to Cloud Advisor export JSON/CSV. Can be repeated.")
    parser.add_argument("--output-dir", default="output/oci-savings-autopilot", help="Output directory.")
    args = parser.parse_args()

    cost_paths = existing_paths(args.cost_report)
    inventory_paths = existing_paths(args.inventory)
    advisor_paths = existing_paths(args.cloud_advisor)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    costs = collect_costs(cost_paths)
    resources = collect_inventory(inventory_paths)
    for resource_id, cost in costs.items():
        if resource_id in resources and not resources[resource_id].monthly_cost:
            resources[resource_id].monthly_cost = cost

    recommendations = collect_cloud_advisor(advisor_paths)
    opportunities = cloud_advisor_opportunities(recommendations)
    opportunities.extend(inventory_opportunities(resources, opportunities))
    ranked = rank_opportunities(opportunities)

    gaps: list[str] = []
    if not cost_paths:
        gaps.append("No cost report was provided; savings estimates rely on inventory or Cloud Advisor values only.")
    if not inventory_paths:
        gaps.append("No inventory file was provided; cleanup and tagging checks are limited.")
    if not advisor_paths:
        gaps.append("No Cloud Advisor export was provided; confidence is lower for rightsizing and cleanup estimates.")
    if not ranked:
        gaps.append("No opportunities were detected from the provided files.")

    write_ledger(output_dir / "savings_ledger.csv", ranked)
    write_report(output_dir / "savings_report.md", ranked, costs, gaps)
    print(f"Wrote {output_dir / 'savings_report.md'}")
    print(f"Wrote {output_dir / 'savings_ledger.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
