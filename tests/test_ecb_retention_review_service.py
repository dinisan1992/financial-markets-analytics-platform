import unittest

from services.ecb_retention_review_service import (
    RETAINED_CONTRACTS,
    build_review_payload,
    evaluate_contract,
)


def evidence(rows, total_bytes=100):
    return {
        "exact_rows": rows,
        "row_count_matches": True,
        "storage": {"total_bytes": total_bytes},
    }


class EcbRetentionReviewTests(unittest.TestCase):
    def test_verified_contract_is_always_retain_only(self):
        contract = RETAINED_CONTRACTS[0]
        result = evaluate_contract(
            contract,
            active_evidence=evidence(contract.expected_active_rows),
            retained_evidence=evidence(contract.expected_retained_rows),
        )
        self.assertEqual(result["status"], "verified_retain")
        self.assertEqual(result["recommendation"], "retain")
        self.assertFalse(result["full_data_fingerprint_recomputed"])

    def test_missing_retained_table_blocks_review(self):
        contract = RETAINED_CONTRACTS[1]
        result = evaluate_contract(
            contract,
            active_evidence=evidence(contract.expected_active_rows),
        )
        self.assertEqual(result["status"], "review_required")
        self.assertIn("retained_table_missing", result["blockers"])

    def test_changed_count_and_residual_artifact_are_explicit(self):
        contract = RETAINED_CONTRACTS[2]
        retained = evidence(contract.expected_retained_rows - 1)
        retained["row_count_matches"] = False
        result = evaluate_contract(
            contract,
            active_evidence=evidence(contract.expected_active_rows),
            retained_evidence=retained,
            residual_artifacts=("example__failed_v079_suffix",),
        )
        self.assertIn("retained_row_count_changed", result["blockers"])
        self.assertIn(
            "shadow_or_failed_artifact_present",
            result["blockers"],
        )

    def test_summary_totals_only_existing_retained_storage(self):
        results = []
        for index, contract in enumerate(RETAINED_CONTRACTS):
            results.append(
                evaluate_contract(
                    contract,
                    active_evidence=evidence(contract.expected_active_rows),
                    retained_evidence=evidence(
                        contract.expected_retained_rows,
                        total_bytes=(index + 1) * 100,
                    ),
                )
            )
        payload = build_review_payload(results)
        self.assertTrue(payload["summary"]["all_valid"])
        self.assertEqual(payload["summary"]["total_retained_bytes"], 600)
        self.assertFalse(payload["database_write_performed"])
        self.assertFalse(payload["table_deleted"])


if __name__ == "__main__":
    unittest.main()
