"""Unit tests verifying canonical domain contracts, enums, and immutability."""

import pytest
from pydantic import ValidationError

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding


def test_finding_evidence_immutability():
    """Verifies FindingEvidence is strictly frozen (immutable)."""
    evidence = FindingEvidence(
        observedValue="HTTP 200",
        expectedValue="HTTP 200",
        provenance=ProvenanceCategory.DIRECT_OBSERVATION,
    )

    with pytest.raises(ValidationError):
        # Attempting to mutate an immutable frozen model must raise ValidationError
        evidence.observedValue = "HTTP 404"  # type: ignore[misc]


def test_finding_immutability():
    """Verifies Finding contract is strictly frozen."""
    finding = Finding(
        ruleId="test-rule",
        category=RuleCategory.CRAWLABILITY,
        title="Test Rule",
        description="Rule for immutability verification",
        state=RuleState.PASS,
        severity=IssueSeverity.HIGH,
        weight=8,
        evidence=FindingEvidence(
            observedValue="test",
            expectedValue="test",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        ),
        remediationGuidance="None needed",
    )

    with pytest.raises(ValidationError):
        finding.state = RuleState.FAIL  # type: ignore[misc]


def test_five_state_rule_enum_membership():
    """Verifies all five required states are defined."""
    expected_states = {"PASS", "FAIL", "UNKNOWN", "NOT_TESTED", "NOT_APPLICABLE"}
    actual_states = {state.value for state in RuleState}
    assert actual_states == expected_states

