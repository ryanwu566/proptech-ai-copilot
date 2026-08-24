"""Static regression contracts for Experience Architecture v3 Phases 2-4."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homepage_has_one_canonical_primary_action_and_secondary_entry_disclosure() -> None:
    page = read("frontend_next/app/page.tsx")
    hero = read("frontend_next/components/hero-intro.tsx")
    journey = read("frontend_next/components/guided-journey/guided-property-journey.tsx")
    tool = read("frontend_next/components/guided-journey/journey-tool-card.tsx")
    assert 'data-action-kind="primary"' in hero
    assert hero.count('data-action-kind="primary"') == 1
    assert 'data-primary-action-id="property-finder"' in hero
    assert 'id="secondary-entry-points"' in page
    assert '<DecisionFlowEntry' in page.split('id="secondary-entry-points"', 1)[1]
    assert '<DecisionWorkspaceSteps' in page.split('id="secondary-entry-points"', 1)[1]
    assert 'useState<JourneyStepId>("property")' in journey
    assert 'data-action-kind={primary ? "primary" : "secondary"}' in tool


def test_primary_action_contract_is_explicit_for_all_five_steps() -> None:
    helper = read("frontend_next/lib/guided-journey.ts")
    contract = read("frontend_next/lib/experience-architecture.ts")
    stage = read("frontend_next/components/guided-journey/journey-stage.tsx")
    for action_id in ("property-finder", "location-insight", "valuation", "loan", "viewing-decision"):
        assert f'primaryActionId: "{action_id}"' in helper
    assert 'data-action-contract="one-primary-per-view"' in stage
    assert 'data-primary-action-id={step.primaryActionId}' in stage
    assert "HOMEPAGE_PRIMARY_ACTION_CONTRACT" in contract
    assert 'primaryActionId: "property-finder"' in contract
    assert "automaticEffects: false" in contract


def test_navigation_is_not_a_duplicate_primary_action_and_expert_tools_are_closed() -> None:
    navigation = read("frontend_next/components/guided-journey/journey-navigation.tsx")
    expert = read("frontend_next/components/guided-journey/journey-expert-tools.tsx")
    page = read("frontend_next/app/page.tsx")
    assert navigation.count('data-action-kind="primary"') == 0
    assert navigation.count('data-action-kind="navigation"') == 2
    assert 'data-default-open="false"' in expert
    assert 'open={true}' not in expert
    assert '<details id="advanced-tools"' in page
    assert '<details id="advanced-tools" open' not in page


def test_existing_routes_and_decision_surfaces_remain_reachable() -> None:
    sidebar = read("frontend_next/components/sidebar.tsx")
    page = read("frontend_next/app/page.tsx")
    case_route = read("frontend_next/app/cases/[caseId]/page.tsx")
    assert "Map Insight Lite" in sidebar
    assert "Terrain Risk" in sidebar
    assert "Market Insight Lite" in sidebar
    assert "ViewingDecisionPanel" in page
    assert "Decision Report" in page
    assert "PropertyCaseCommandCenter" in case_route


def test_rendering_and_step_selection_add_no_automatic_side_effects() -> None:
    journey_dir = FRONTEND / "components" / "guided-journey"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in journey_dir.glob("*.tsx"))
    assert "api." not in sources
    assert "fetch(" not in sources
    assert "sessionStorage" not in sources
    assert "localStorage" not in sources
    assert "document.cookie" not in sources
    assert "URLSearchParams" not in sources


def test_state_contract_keeps_conservative_states_distinct() -> None:
    state = read("frontend_next/lib/experience-architecture.ts")
    panel = read("frontend_next/components/experience-state-panel.tsx")
    for name in ("empty", "loading", "unavailable", "no_official_data", "partial", "limited", "no_match", "unknown", "not_assessed", "error", "ready"):
        assert f'{name}:' in state
    assert "不代表低風險" in state
    assert "零值" in read("frontend_next/components/data-visualization/chart-empty-state.tsx") or 'copy("viz.chartEmptyExplanation")' in read("frontend_next/components/data-visualization/chart-empty-state.tsx")
    assert "data-experience-state={state}" in panel
    assert "aria-live=\"polite\"" in panel


def test_terrain_and_valuation_missing_data_do_not_become_positive_evidence() -> None:
    terrain = read("frontend_next/components/terrain-risk-analysis.tsx")
    valuation = read("frontend_next/components/data-visualization/valuation-visual-panel.tsx")
    visual_state = read("frontend_next/components/data-visualization/visual-data-unavailable-state.tsx")
    assert "安全保證" not in terrain
    assert "no_official_data" in valuation
    assert "不以零值或低風險" in valuation
    assert "ExperienceStatePanel" in visual_state


def test_evidence_is_summary_first_and_details_are_keyboard_accessible() -> None:
    panel = read("frontend_next/components/data-visualization/valuation-visual-panel.tsx")
    details = read("frontend_next/components/data-visualization/evidence-details.tsx")
    summary = read("frontend_next/components/data-visualization/evidence-summary.tsx")
    assert panel.index("ValuationEvidenceSummary") < panel.index("<details")
    assert 'data-evidence-summary="true"' in summary
    assert "focus:ring-2" in details
    assert "focus:ring-2" in panel


def test_empty_or_unavailable_charts_use_text_states_and_responsive_wrapping() -> None:
    visual_dir = FRONTEND / "components" / "data-visualization"
    chart_sources = [path.read_text(encoding="utf-8") for path in visual_dir.glob("*.tsx")]
    for source in chart_sources:
        assert "min-h-[320px]" not in source
    trend = read("frontend_next/components/data-visualization/trend-line-chart.tsx")
    volume = read("frontend_next/components/data-visualization/volume-bar-chart.tsx")
    empty = read("frontend_next/components/data-visualization/chart-empty-state.tsx")
    assert '!marketStateHasEvidence(status) || data.length === 0' in trend
    assert "data.length === 1" in trend
    assert '!marketStateHasEvidence(status) || data.length === 0' in volume
    assert "data.length === 1" in volume
    assert "ExperienceStatePanel" in empty
    assert "role=\"img\"" in trend and "<desc>" in trend
    assert "role=\"img\"" in volume and "<desc>" in volume


def test_no_new_storage_dependency_or_domain_contract_rewrite() -> None:
    changed_presentation = [
        read("frontend_next/lib/experience-architecture.ts"),
        read("frontend_next/components/experience-state-panel.tsx"),
        read("frontend_next/components/data-visualization/evidence-summary.tsx"),
        read("frontend_next/components/data-visualization/evidence-details.tsx"),
    ]
    combined = "\n".join(changed_presentation).lower()
    for forbidden in ("localstorage", "sessionstorage", "document.cookie", "urlsearchparams", "fetch(", "api.", "raw_payload", "provider_payload", "token", "sql"):
        assert forbidden not in combined
    assert "automaticEffects: false".lower() in combined
