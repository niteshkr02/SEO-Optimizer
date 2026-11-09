"""Mathematical Model E11: Redirect Hop Count & Loop Detection."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import IssueSeverity, RuleState


class RedirectHop(BaseModel):
    """Immutable representation of an individual redirect hop."""

    model_config = ConfigDict(frozen=True)

    hop_index: int = Field(..., ge=0, description="0-indexed hop sequence number.")
    status_code: int = Field(
        ..., description="HTTP status code (301, 302, 307, 308, etc.)."
    )
    request_url: str = Field(..., description="URL requested in this hop.")
    target_url: str = Field(
        ..., description="Destination URL indicated in Location header."
    )
    latency_ms: int | None = Field(
        default=None, description="Round-trip network timing in ms."
    )


class RedirectEvaluation(BaseModel):
    """Result of evaluating a redirect chain against Model E11."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = "E11"
    formula_version: str = "1.0.0"
    total_hops: int = Field(
        ..., ge=0, description="Count of actual 3xx redirect hops followed."
    )
    has_loop: bool = Field(
        default=False, description="True if a cyclic destination was detected."
    )
    initial_url: str = Field(..., description="First requested URL.")
    final_url: str = Field(..., description="Final landing URL.")
    hops: list[RedirectHop] = Field(
        default_factory=list, description="Ordered chain of redirect hops."
    )
    rule_state: RuleState = Field(..., description="Deterministic 5-state outcome.")
    severity: IssueSeverity = Field(..., description="Impact severity rating.")
    deduction_points: int = Field(
        default=0, ge=0, description="Points deducted in legacy scoring."
    )
    guidance: str = Field(..., description="Actionable remediation advice.")


def evaluate_redirect_chain(
    hops: list[RedirectHop],
    initial_url: str,
    final_url: str,
    has_loop: bool = False,
) -> RedirectEvaluation:
    """Evaluates an observed HTTP redirect chain according to Model E11 specifications.

    Operational Classification:
    - 0-1 hops: PASS (Optimal)
    - 2-3 hops: FAIL / WARNING (Sub-optimal, latency overhead)
    - 4+ hops: FAIL / CRITICAL (Excessive latency / crawl budget waste)
    - Loop detected: FAIL / CRITICAL (Crawl failure)
    """
    total_hops = len(hops)

    if has_loop:
        return RedirectEvaluation(
            total_hops=total_hops,
            has_loop=True,
            initial_url=initial_url,
            final_url=final_url,
            hops=hops,
            rule_state=RuleState.FAIL,
            severity=IssueSeverity.CRITICAL,
            deduction_points=25,
            guidance=(
                f"A redirect loop was detected after {total_hops} hops involving '{final_url}'. "
                "Resolve circular HTTP 3xx rules to prevent crawlers and browsers from failing."
            ),
        )

    if total_hops <= 1:
        return RedirectEvaluation(
            total_hops=total_hops,
            has_loop=False,
            initial_url=initial_url,
            final_url=final_url,
            hops=hops,
            rule_state=RuleState.PASS,
            severity=IssueSeverity.INFO,
            deduction_points=0,
            guidance=(
                f"Direct or single-hop redirect ({total_hops} hop). "
                "Crawl latency and PageRank transfer are preserved."
            ),
        )

    if 2 <= total_hops <= 3:
        return RedirectEvaluation(
            total_hops=total_hops,
            has_loop=False,
            initial_url=initial_url,
            final_url=final_url,
            hops=hops,
            rule_state=RuleState.FAIL,
            severity=IssueSeverity.MEDIUM,
            deduction_points=10,
            guidance=(
                f"Multi-hop redirect chain detected ({total_hops} hops). "
                "Update internal links and server rules to redirect directly to the final landing URL."
            ),
        )

    # 4+ hops
    return RedirectEvaluation(
        total_hops=total_hops,
        has_loop=False,
        initial_url=initial_url,
        final_url=final_url,
        hops=hops,
        rule_state=RuleState.FAIL,
        severity=IssueSeverity.HIGH,
        deduction_points=25,
        guidance=(
            f"Excessive redirect chain detected ({total_hops} hops). "
            "Search bots may abandon crawling before reaching the final URL. Collapse redirects to 1 direct hop."
        ),
    )
