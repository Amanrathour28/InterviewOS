"""
Phase 16.1 — Analytics Export Sanitization & PII Minimization Tests.

Verifies:
- Sensitive credentials (passwords, tokens, api keys) are stripped
- Raw chain of thought / system prompts / hidden tests are stripped
- CSV and JSON generation formats are valid and deterministic
"""

import json
import pytest
from app.services.analytics_export_service import analytics_export_service


class TestExportSanitization:
    """Verify that private notes, tokens, credentials, and internal prompts are stripped."""

    def test_sensitive_tokens_and_passwords_stripped(self):
        record = {
            "evaluation_id": "eval-1",
            "candidate_name": "Alice Smith",
            "overall_score": 85.0,
            "password": "SecretPassword!",
            "hashed_password": "$2b$12$xyz...",
            "api_key": "sk-live-12345",
            "access_token": "eyJh...",
            "hidden_tests": "assert secret_function() == 42",
            "chain_of_thought": "Model reasoning: Candidate was slow...",
            "raw_content": "Transcript raw audio dump",
            "integrity_hash": "sha256-abc123",
            "recommendation": "strong_hire",
        }

        sanitized = analytics_export_service.sanitize_record(record)

        assert "password" not in sanitized
        assert "hashed_password" not in sanitized
        assert "api_key" not in sanitized
        assert "access_token" not in sanitized
        assert "hidden_tests" not in sanitized
        assert "chain_of_thought" not in sanitized
        assert "raw_content" not in sanitized
        assert "integrity_hash" not in sanitized

        assert sanitized["evaluation_id"] == "eval-1"
        assert sanitized["candidate_name"] == "Alice Smith"
        assert sanitized["overall_score"] == 85.0
        assert sanitized["recommendation"] == "strong_hire"

    def test_json_export_envelope_structure(self):
        records = [
            {"evaluation_id": "e1", "score": 90.0, "recommendation": "strong_hire"},
            {"evaluation_id": "e2", "score": 75.0, "recommendation": "hire"},
        ]
        metadata = {"workspace_id": "ws-1", "window": "30d"}

        output = analytics_export_service.to_json(records, metadata)
        parsed = json.loads(output)

        assert "export_metadata" in parsed
        assert parsed["export_metadata"]["record_count"] == 2
        assert parsed["export_metadata"]["workspace_id"] == "ws-1"
        assert len(parsed["records"]) == 2

    def test_csv_export_determinism(self):
        records = [
            {"evaluation_id": "e1", "score": 90.0, "recommendation": "strong_hire"},
            {"evaluation_id": "e2", "score": 75.0, "recommendation": "hire"},
        ]

        csv1 = analytics_export_service.to_csv(records)
        csv2 = analytics_export_service.to_csv(records)

        assert csv1 == csv2
        assert "evaluation_id" in csv1
        assert "strong_hire" in csv1
