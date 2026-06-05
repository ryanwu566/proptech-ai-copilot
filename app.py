"""Streamlit entry point for the PropTech AI Copilot MVP."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Callable

import pandas as pd
import streamlit as st

from backend.db import health_check
from backend.repositories.sqlite_repo import get_tax_analysis, list_tax_analyses
from models.schemas import DISCLAIMER, TaxCase
from rules.legal_risk_rules import summarize_legal_risk
from rules.mortgage_rules import evaluate_mortgage_risk
from services.data_service import MockDataError, load_mock_csv
from services.market_insight_service import get_market_summary, load_market_insights
from services.report_service import generate_tax_html_report
from services.tax_service import analyze_tax_case


BOOL_COLUMNS = [field.name for field in fields(TaxCase) if field.type == "bool"]
DEMO_LABELS = {
    "DEMO-LOW": "低風險：eligible / green",
    "DEMO-MEDIUM": "中風險：manual_review / yellow",
    "DEMO-HIGH": "高風險：not_eligible / red",
}
SIGNAL_ICONS = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}
STATUS_LABELS = {
    "eligible": "初步符合資格",
    "manual_review": "需要人工複核",
    "not_eligible": "初步不符合資格",
}


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    """Cache bundled mock CSV loading for the Streamlit process."""

    return load_mock_csv(name)


def as_bool(value: Any) -> bool:
    """Normalize pandas and Streamlit values into booleans."""

    return str(value).strip().lower() in {"true", "1", "yes"}


def inject_styles() -> None:
    """Add lightweight SaaS dashboard styling."""

    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .hero { padding: 1.25rem 1.4rem; border: 1px solid #e2e8f0; border-radius: 16px;
                background: linear-gradient(135deg, #f8fafc, #eef2ff); margin-bottom: 1rem; }
        .hero h1 { margin: 0; font-size: 2rem; color: #0f172a; }
        .hero p { margin: .35rem 0 0; color: #475569; }
        .status-card { padding: .9rem 1rem; border-radius: 12px; border: 1px solid #e2e8f0;
                       background: #ffffff; min-height: 92px; }
        .status-card small { color: #64748b; } .status-card strong { font-size: 1.35rem; }
        .signal-green { border-left: 8px solid #22c55e; background: #f0fdf4; }
        .signal-yellow { border-left: 8px solid #eab308; background: #fefce8; }
        .signal-red { border-left: 8px solid #ef4444; background: #fef2f2; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str) -> None:
    """Render a consistent dashboard heading."""

    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def render_signal_card(result: dict[str, Any]) -> None:
    """Render a visually distinct TaxOracle signal."""

    color = result["signal_color"]
    st.markdown(
        f"""
        <div class="status-card signal-{color}">
          <small>TaxOracle Signal</small><br>
          <strong>{SIGNAL_ICONS[color]} / {color.upper()}</strong><br>
          資格：{STATUS_LABELS[result["eligibility_status"]]}（{result["eligibility_status"]}），風險分數：{result["risk_score"]}
        </div>
        """,
        unsafe_allow_html=True,
    )


def demo_cases() -> pd.DataFrame | None:
    """Load demo cases and surface friendly UI errors."""

    try:
        return load_csv("mock_tax_cases.csv")
    except MockDataError as exc:
        st.error(str(exc))
        return None


def _open_taxoracle_demo(case_id: str) -> None:
    """Select a demo case and navigate before Streamlit redraws widgets."""

    st.session_state["selected_demo_id"] = case_id
    st.session_state["navigation"] = "TaxOracle 稅務先知"


def _open_market_insight() -> None:
    """Navigate from the dashboard to the offline market insight page."""

    st.session_state["navigation"] = "Market Insight Lite"


def dashboard() -> None:
    """Render the SaaS-style dashboard landing page."""

    render_hero("PropTech AI Copilot", "台灣房仲 AI 競賽展示型 MVP：以 TaxOracle 稅務先知為核心")
    cases = demo_cases()
    if cases is None:
        return
    history_rows = list_tax_analyses()
    cols = st.columns(3)
    cols[0].metric("TaxOracle Demo Cases", len(cases))
    cols[1].metric("歷史分析", len(history_rows))
    cols[2].metric("系統狀態", "Ready")
    st.subheader("Demo Mode / 競賽展示模式")
    st.info("三步驟完成展示：1. 選擇 demo case → 2. 執行 TaxOracle 分析 → 3. 下載 HTML report")
    buttons = st.columns(3)
    for column, (case_id, label) in zip(buttons, DEMO_LABELS.items()):
        column.button(label, width="stretch", on_click=_open_taxoracle_demo, args=(case_id,))
    st.dataframe(
        pd.DataFrame(
            [
                {"展示案件": "低風險", "預期資格": "eligible", "預期燈號": "green", "展示重點": "條件完整，可進入文件準備"},
                {"展示案件": "中風險", "預期資格": "manual_review", "預期燈號": "yellow", "展示重點": "缺件，需人工複核"},
                {"展示案件": "高風險", "預期資格": "not_eligible", "預期燈號": "red", "展示重點": "存在必要條件未通過"},
            ]
        ),
        width="stretch",
        hide_index=True,
    )
    st.subheader("Market Insight Lite")
    st.info("延續 OmniUrbanAI v2 的都市機能概念，以離線 mock data 展示區域行情、生活機能與 ESG / SDG 11 指標。")
    st.button("開啟 Market Insight Lite", width="stretch", on_click=_open_market_insight)
    st.subheader("產品模組")
    st.dataframe(
        pd.DataFrame(
            [
                {"模組": "TaxOracle", "定位": "完整展示", "內容": "稅務資格快篩與五年列管提醒"},
                {"模組": "Aegis-Credit Lite", "定位": "Lite Demo", "內容": "房貸風險展示型 heuristic，不代表銀行核貸"},
                {"模組": "LexProp Lite", "定位": "Lite Demo", "內容": "公開判決摘要模糊比對，不輸出完整門牌與個資"},
            ]
        ),
        width="stretch",
        hide_index=True,
    )


def render_tax_result(result: dict[str, Any], case: TaxCase | None = None) -> None:
    """Render cards, tables, explainers, and an HTML report download."""

    st.subheader("分析結果")
    render_signal_card(result)
    cols = st.columns(3)
    cols[0].metric("資格結果", result["eligibility_status"])
    cols[1].metric("風險分數", result["risk_score"])
    cols[2].metric("燈號", result["signal_color"])
    with st.expander("為什麼是這個結果？", expanded=True):
        st.write(_explain_tax_result(result))
        if result["hard_fail_rules"]:
            st.error(f"必要條件未通過：{', '.join(result['hard_fail_rules'])}")
        elif result["manual_review_rules"]:
            st.warning(f"需要人工複核：{', '.join(result['manual_review_rules'])}")
        else:
            st.success("TX001-TX009 初步檢核皆已通過。")
    with st.expander("Rule Trace", expanded=True):
        st.dataframe(result["rule_traces"], width="stretch", hide_index=True)
    with st.expander("補件清單", expanded=True):
        st.write(result["missing_docs"] or ["目前無補件項目"])
    with st.expander("五年列管 Timeline"):
        st.write(result["reminder_timeline"] or ["本案目前未建立五年列管提醒"])
    with st.expander("AI 或 fallback 中文說明", expanded=True):
        st.write(result["ai_explanation"]["headline"])
        st.write(result["ai_explanation"]["customer_script"])
        st.caption(f"說明來源：{result['ai_explanation']['source']}")
    case = case or _case_from_result(result)
    if case is not None:
        html = generate_tax_html_report(case, result)
        st.download_button(
            "下載 TaxOracle HTML 報告",
            data=html.encode("utf-8"),
            file_name=f"taxoracle-{case.case_id}.html",
            mime="text/html",
            type="primary",
        )


def _case_from_result(result: dict[str, Any]) -> TaxCase | None:
    """Restore a TaxCase from a persisted result when available."""

    case_input = result.get("case_input")
    return TaxCase(**case_input) if case_input else None


def _explain_tax_result(result: dict[str, Any]) -> str:
    """Explain the deterministic status without changing the rule conclusion."""

    status = result["eligibility_status"]
    if status == "not_eligible":
        return "規則引擎發現必要條件未通過，因此初步判定為不符合資格。風險分數只用於排序與展示，不會取代資格結論。"
    if status == "manual_review":
        return "目前沒有必要條件直接失敗，但仍有缺件或例外條件需要人工確認，因此標示為需要人工複核。"
    return "所有初步規則均已通過，因此標示為初步符合資格。正式資格仍須由主管機關與專業人士確認。"


def tax_oracle() -> None:
    """Render demo selector, manual form, and deterministic TaxOracle analysis."""

    render_hero("TaxOracle 稅務先知", "稅務資格快篩與五年列管提醒。資格結論由 TX001-TX009 規則引擎產生，不交由 AI 判斷。")
    st.info("展示流程：選擇 demo case → 按下「開始分析」→ 檢視結果並下載 HTML report")
    cases = demo_cases()
    if cases is None:
        return
    case_ids = cases["case_id"].tolist()
    preferred = st.session_state.get("selected_demo_id", case_ids[0])
    selected_id = st.selectbox("載入 demo case", case_ids, index=case_ids.index(preferred) if preferred in case_ids else 0)
    selected = cases[cases["case_id"] == selected_id].iloc[0].to_dict()
    with st.form("tax-case-form"):
        case_id = st.text_input("案件編號", value=str(selected["case_id"]))
        client_name = st.text_input("客戶名稱", value=str(selected["client_name"]))
        labels = {
            "sold_self_occupied": "TX001 賣出物件為自住",
            "residency_condition_met": "TX002 已設籍或符合自住條件",
            "purchase_within_reasonable_period": "TX003 換購時間合理",
            "purchased_self_occupied": "TX004 換購物件為自住",
            "same_owner": "TX005 所有權主體一致",
            "land_value_available": "TX006 公告土地現值齊備",
            "required_docs_complete": "TX007 文件足夠",
            "enters_five_year_monitoring": "TX008 進入五年列管",
            "exceptional_circumstances": "TX009 有例外事由",
        }
        values = {key: st.checkbox(labels[key], value=as_bool(selected[key])) for key in BOOL_COLUMNS}
        submitted = st.form_submit_button("開始分析", type="primary")
    if submitted:
        try:
            case = TaxCase(case_id=case_id, client_name=client_name, **values)
            st.session_state["latest_tax_result"] = analyze_tax_case(case)
        except Exception as exc:
            st.error(f"分析失敗，請確認輸入資料後重試。詳細資訊：{exc}")
    if "latest_tax_result" in st.session_state:
        render_tax_result(st.session_state["latest_tax_result"])


def aegis_credit() -> None:
    """Render the Aegis-Credit Lite heuristic demo."""

    render_hero("Aegis-Credit Lite", "房貸風險展示型 heuristic，不代表銀行核貸")
    income = st.number_input("買方每月收入", min_value=0, value=90000, step=5000)
    debt = st.number_input("每月負債", min_value=0, value=15000, step=5000)
    cash = st.number_input("可用現金", min_value=0, value=3500000, step=100000)
    price = st.number_input("物件價格", min_value=0, value=22000000, step=500000)
    property_count = st.number_input("名下房屋數", min_value=0, value=0)
    mortgage_count = st.number_input("既有房貸數", min_value=0, value=0)
    if st.button("計算房貸風險"):
        st.json(evaluate_mortgage_risk(income, debt, cash, property_count, mortgage_count, price))
    st.warning("展示版，不代表正式判斷。這不是銀行核貸承諾。")


def market_insight() -> None:
    """Render offline area pricing, POI, and ESG / SDG 11 Lite insights."""

    render_hero("Market Insight Lite", "區域行情、生活機能與 ESG / SDG 11 Lite。全頁使用展示型 mock data，不串外部 API。")
    try:
        data = load_market_insights()
    except MockDataError as exc:
        st.error(str(exc))
        return
    cities = sorted(data["city"].dropna().unique().tolist())
    selected_city = st.selectbox("選擇縣市", cities)
    districts = sorted(data[data["city"] == selected_city]["district"].dropna().unique().tolist())
    selected_district = st.selectbox("選擇行政區", districts)
    try:
        result = get_market_summary(selected_city, selected_district)
    except MockDataError as exc:
        st.error(str(exc))
        return
    if result is None:
        st.warning("找不到該區域的展示資料，請改選其他區域。")
        return

    st.subheader("區域行情摘要")
    market_cols = st.columns(4)
    market_cols[0].metric("區域", f"{result['city']} {result['district']}")
    market_cols[1].metric("平均單價", f"{result['avg_price_per_ping']:.1f} 萬 / 坪")
    market_cols[2].metric("六期交易量", result["transaction_volume"])
    market_cols[3].metric("生活機能分數", result["livability_score"])
    st.write(result["summary"])
    trend = pd.DataFrame(
        {"平均單價（萬 / 坪）": result["trend"]},
        index=[f"第 {period} 期" for period in range(1, 7)],
    )
    st.line_chart(trend, width="stretch")

    st.subheader("POI 生活機能分數卡")
    poi_cols = st.columns(len(result["poi_breakdown"]))
    for column, (label, score) in zip(poi_cols, result["poi_breakdown"].items()):
        column.metric(label, score)

    st.subheader("ESG / SDG 11 Lite")
    esg_cols = st.columns(2)
    esg_cols[0].metric("ESG Lite 分數", result["esg_lite_score"])
    esg_cols[1].metric("步行生活圈", int(data[(data["city"] == selected_city) & (data["district"] == selected_district)].iloc[0]["walkability_score"]))
    st.info(result["sdg11_note"])
    st.warning(result["disclaimer"])


def lex_prop() -> None:
    """Render the privacy-preserving LexProp Lite mock lookup."""

    render_hero("LexProp Lite", "公開判決摘要模糊比對，不輸出完整門牌與個資")
    city = st.text_input("縣市", "台北市")
    district = st.text_input("行政區", "信義區")
    road = st.text_input("遮罩路名", "松仁路***號")
    community = st.text_input("社區", "信義首席")
    if st.button("查詢匿名化風險"):
        try:
            st.json(summarize_legal_risk(load_csv("mock_judgments.csv"), city, district, road, community))
        except MockDataError as exc:
            st.error(str(exc))
    st.info("展示版，不代表正式判斷。只比對 city、district、road_masked、community，不輸出完整門牌、姓名或個資。")


def history() -> None:
    """Render history rows and reload stored structured results."""

    render_hero("History", "SQLite 保存的 TaxOracle 分析紀錄")
    rows = list_tax_analyses()
    if not rows:
        st.info("尚無歷史案件。請先至 TaxOracle 執行分析。")
        return
    st.dataframe(rows, width="stretch", hide_index=True)
    options = {f"#{row['id']} {row['client_name']} / {row['case_id']}": row["id"] for row in rows}
    selected_label = st.selectbox("選擇歷史案件", list(options))
    if st.button("重新載入歷史分析"):
        record = get_tax_analysis(options[selected_label])
        if record is None:
            st.error("找不到該筆歷史案件，請重新整理頁面。")
        else:
            st.session_state["history_tax_result"] = record["payload"]
    if "history_tax_result" in st.session_state:
        render_tax_result(st.session_state["history_tax_result"])


def main() -> None:
    """Configure and run the Streamlit application."""

    st.set_page_config(page_title="PropTech AI Copilot", layout="wide")
    inject_styles()
    try:
        status = health_check()
    except Exception as exc:
        st.error(f"SQLite 啟動檢查失敗：{exc}")
        st.stop()
    pages: dict[str, Callable[[], None]] = {
        "儀表板": dashboard,
        "TaxOracle 稅務先知": tax_oracle,
        "Market Insight Lite": market_insight,
        "Aegis-Credit": aegis_credit,
        "LexProp": lex_prop,
        "歷史案件": history,
    }
    with st.sidebar:
        st.header("PropTech AI Copilot")
        page = st.radio("頁面", list(pages), key="navigation")
        st.caption(f"SQLite: {status['database']}")
        st.caption("Mock data mode")
    pages[page]()
    st.divider()
    st.caption(DISCLAIMER)


if __name__ == "__main__":
    main()
