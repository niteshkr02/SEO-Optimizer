"""Unit tests for Mathematical Model E11: Redirect Hop Count & Loop Detection."""

from app.contracts.enums import IssueSeverity, RuleState
from app.crawler.redirects import RedirectHop, evaluate_redirect_chain


def test_e11_direct_url_evaluates_to_pass():
    res = evaluate_redirect_chain(
        hops=[],
        initial_url="https://example.com/",
        final_url="https://example.com/",
    )
    assert res.total_hops == 0
    assert res.rule_state == RuleState.PASS
    assert res.severity == IssueSeverity.INFO
    assert res.has_loop is False


def test_e11_single_hop_evaluates_to_pass():
    hop = RedirectHop(
        hop_index=0,
        status_code=301,
        request_url="http://example.com/",
        target_url="https://example.com/",
    )
    res = evaluate_redirect_chain(
        hops=[hop],
        initial_url="http://example.com/",
        final_url="https://example.com/",
    )
    assert res.total_hops == 1
    assert res.rule_state == RuleState.PASS


def test_e11_multi_hop_evaluates_to_medium_warning():
    hops = [
        RedirectHop(hop_index=0, status_code=301, request_url="http://example.com", target_url="https://example.com"),
        RedirectHop(hop_index=1, status_code=302, request_url="https://example.com", target_url="https://example.com/en"),
    ]
    res = evaluate_redirect_chain(
        hops=hops,
        initial_url="http://example.com",
        final_url="https://example.com/en",
    )
    assert res.total_hops == 2
    assert res.rule_state == RuleState.FAIL
    assert res.severity == IssueSeverity.MEDIUM


def test_e11_excessive_hops_evaluates_to_high_warning():
    hops = [
        RedirectHop(hop_index=i, status_code=301, request_url=f"http://example.com/{i}", target_url=f"http://example.com/{i+1}")
        for i in range(4)
    ]
    res = evaluate_redirect_chain(
        hops=hops,
        initial_url="http://example.com/0",
        final_url="http://example.com/4",
    )
    assert res.total_hops == 4
    assert res.rule_state == RuleState.FAIL
    assert res.severity == IssueSeverity.HIGH


def test_e11_loop_detected_evaluates_to_critical():
    res = evaluate_redirect_chain(
        hops=[],
        initial_url="https://example.com/a",
        final_url="https://example.com/a",
        has_loop=True,
    )
    assert res.has_loop is True
    assert res.rule_state == RuleState.FAIL
    assert res.severity == IssueSeverity.CRITICAL

