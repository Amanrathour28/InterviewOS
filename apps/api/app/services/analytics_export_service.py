"""
Phase 16 — Analytics Export Service.

Provides secure, tenant-isolated CSV and JSON export generation.
All exports respect:
- Current workspace and role authorization (caller's responsibility)
- Applied date/filter scoping
- Exclusion of private/sensitive fields (interviewer personal data, raw evidence content)
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("interviewos.api.analytics_export_service")

# Fields strictly excluded from all exports (privacy/security boundaries)
_EXCLUDED_FIELDS = {
    "email",
    "password",
    "hashed_password",
    "api_key",
    "token",
    "access_token",
    "refresh_token",
    "raw_content",
    "integrity_hash",
    "snapshot_payload",
    "private_notes",
    "hidden_tests",
    "hidden_test_cases",
    "system_prompt",
    "chain_of_thought",
    "cot",
}


class AnalyticsExportService:
    """Generates structured, privacy-respecting CSV and JSON analytics exports."""

    def sanitize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Remove private or sensitive fields from an export record."""
        return {k: v for k, v in record.items() if k.lower() not in _EXCLUDED_FIELDS}

    def to_csv(self, records: List[Dict[str, Any]], field_order: Optional[List[str]] = None) -> str:
        """
        Converts a list of flat record dictionaries to CSV format.
        Nested objects are serialized as JSON strings.
        """
        if not records:
            return ""

        sanitized = [self.sanitize_record(r) for r in records]

        # Flatten nested dicts to JSON strings
        flat_records: List[Dict[str, str]] = []
        for record in sanitized:
            flat = {}
            for k, v in record.items():
                if isinstance(v, (dict, list)):
                    flat[k] = json.dumps(v)
                elif v is None:
                    flat[k] = ""
                else:
                    flat[k] = str(v)
            flat_records.append(flat)

        # Determine column order
        if field_order:
            all_keys = field_order + [k for k in flat_records[0].keys() if k not in field_order]
        else:
            all_keys = list(flat_records[0].keys())

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat_records)
        return output.getvalue()

    def to_json(self, records: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Serializes records to a structured JSON export with metadata envelope.
        """
        sanitized = [self.sanitize_record(r) for r in records]
        payload = {
            "export_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "record_count": len(sanitized),
                **(metadata or {}),
            },
            "records": sanitized,
        }
        return json.dumps(payload, indent=2, default=str)

    def build_evaluation_export_records(
        self,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Flattens candidate decision records for CSV/JSON export.
        Only includes fields appropriate for export.
        """
        export_fields = [
            "evaluation_id",
            "interview_id",
            "candidate_id",
            "candidate_name",
            "job_id",
            "overall_score",
            "overall_rubric_level",
            "recommendation",
            "confidence",
            "status",
            "is_authoritative",
            "evidence_count",
            "contradiction_count",
            "finalized_at",
            "created_at",
        ]
        records = []
        for cand in candidates:
            record = {f: cand.get(f) for f in export_fields}
            # Flatten competency_scores as summary
            comp_summary = ", ".join(
                f"{cs['name']}: {cs['score']:.1f}"
                for cs in (cand.get("competency_scores") or [])
            )
            record["competency_summary"] = comp_summary
            records.append(record)
        return records


analytics_export_service = AnalyticsExportService()
