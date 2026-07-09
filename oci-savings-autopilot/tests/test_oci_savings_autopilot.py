import csv
import gzip
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PLUGIN_ROOT / "scripts" / "oci_savings_autopilot.py"

spec = importlib.util.spec_from_file_location("oci_savings_autopilot", SCRIPT_PATH)
osa = importlib.util.module_from_spec(spec)
sys.modules["oci_savings_autopilot"] = osa
assert spec.loader is not None
spec.loader.exec_module(osa)


class OciSavingsAutopilotTests(unittest.TestCase):
    def test_gzip_focus_csv_streams_into_cost_collector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "focus.csv.gz"
            with gzip.open(path, "wt", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ResourceId", "BilledCost", "ServiceName"])
                writer.writeheader()
                writer.writerow(
                    {
                        "ResourceId": "ocid1.instance.oc1..gzip",
                        "BilledCost": "12.34",
                        "ServiceName": "COMPUTE",
                    }
                )

            self.assertEqual(osa.collect_costs([path]), {"ocid1.instance.oc1..gzip": 12.34})

    def test_zero_billed_cost_does_not_fall_through_to_list_cost(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "focus.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ResourceId", "BilledCost", "ListCost"])
                writer.writeheader()
                writer.writerow(
                    {
                        "ResourceId": "ocid1.vnic.oc1..free",
                        "BilledCost": "0.00000000000",
                        "ListCost": "99.99",
                    }
                )

            self.assertEqual(osa.collect_costs([path]), {"ocid1.vnic.oc1..free": 0.0})

    def test_missing_cpu_percent_is_safe_for_compute_inventory(self):
        resource = osa.Resource(
            id="ocid1.instance.oc1..missingcpu",
            name="missing-cpu",
            service="Compute",
            type="compute_instance",
            monthly_cost=100,
        )

        opportunities = osa.inventory_opportunities({resource.id: resource}, [])

        self.assertNotIn("Rightsizing", [item.category for item in opportunities])

    def test_invalid_cpu_percent_is_not_treated_as_low_cpu(self):
        resource = osa.resource_from_row(
            {
                "ResourceId": "ocid1.instance.oc1..invalidcpu",
                "ResourceName": "invalid-cpu",
                "ServiceName": "COMPUTE",
                "ResourceType": "compute_instance",
                "BilledCost": "100",
                "cpu_avg_percent": "not available",
            }
        )

        self.assertIsNone(resource.cpu_avg_percent)
        opportunities = osa.inventory_opportunities({resource.id: resource}, [])
        self.assertNotIn("Rightsizing", [item.category for item in opportunities])

    def test_focus_dimensions_are_mapped_from_standard_headers(self):
        resource = osa.resource_from_row(
            {
                "ResourceId": "ocid1.instance.oc1..focus",
                "ResourceName": "focus-instance",
                "ServiceName": "COMPUTE",
                "ResourceType": "compute_instance",
                "RegionName": "us-ashburn-1",
                "AvailabilityZone": "phx-ad-1",
                "ServiceCategory": "Compute",
                "ChargeCategory": "Usage",
                "EffectiveCost": "42.50",
                "Tags": '{"environment":"dev","application":"erp"}',
            }
        )

        self.assertEqual(resource.id, "ocid1.instance.oc1..focus")
        self.assertEqual(resource.name, "focus-instance")
        self.assertEqual(resource.service, "COMPUTE")
        self.assertEqual(resource.type, "compute_instance")
        self.assertEqual(resource.region, "us-ashburn-1")
        self.assertEqual(resource.availability_zone, "phx-ad-1")
        self.assertEqual(resource.service_category, "Compute")
        self.assertEqual(resource.charge_category, "Usage")
        self.assertEqual(resource.monthly_cost, 42.50)
        self.assertEqual(resource.tags["environment"], "dev")

    def test_ledger_includes_review_only_remediation_template(self):
        opportunity = osa.Opportunity(
            priority=1,
            category="Rightsizing",
            resource_id="ocid1.instance.oc1..resize",
            resource_name="resize-me",
            service="Compute",
            problem="Average CPU is low.",
            recommendation="Review memory and peak CPU, then downsize shape.",
            monthly_savings=25.0,
            confidence="Medium",
            risk="Medium",
            effort="Medium",
            approval_needed="Performance owner validates the change.",
            evidence="Inventory contains low average CPU utilization.",
            rollback="Resize back to the previous shape.",
            remediation_template=osa.review_only_template(
                "oci compute instance update --instance-id ocid1.instance.oc1..resize --shape <APPROVED_TARGET_SHAPE>"
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ledger.csv"
            osa.write_ledger(path, [opportunity])
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(rows[0]["remediation_template"], opportunity.remediation_template)
        self.assertTrue(rows[0]["remediation_template"].startswith("REVIEW_ONLY_APPROVAL_REQUIRED:"))


if __name__ == "__main__":
    unittest.main()
