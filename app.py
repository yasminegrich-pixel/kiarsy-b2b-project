import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
from datetime import date
import html
import os

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="Kiarsy Cultural Affinity Engine",
    layout="wide",
    page_icon="🌍"
)

BASE_DIR = os.path.dirname(__file__)
LOGO_HORIZONTAL = os.path.join(BASE_DIR, "assets", "logo_horizontal.png")
LOGO_EMBLEM = os.path.join(BASE_DIR, "assets", "logo_emblem.png")

# ==========================================================
# BRAND COLORS
# ==========================================================
INK = "#111111"
PAPER = "#FDFBF7"
CLAY = "#C05A36"
SLATE = "#4A4A4A"
LINE = "#E0DCD3"
WHITE = "#FFFFFF"

CULTURE_COLORS = {
    "Amazigh": "#C05A36",
    "Amérindienne": "#2F6F73",
    "Subsaharienne": "#8A6A2F",
}

SERIOUS_KEYWORDS = [
    "slavery", "captivity", "sacred", "funerary", "funeral",
    "reserved for", "legal", "eagle feather", "katsina", "kachina",
    "do not use", "do not reproduce", "religious"
]

# ==========================================================
# CSS
# ==========================================================
st.markdown(f"""
<style>
.stApp {{
    background-color: {PAPER};
    color: {INK};
    font-family: Inter, "Segoe UI", sans-serif;
}}

.block-container {{
    padding-top: 3.5rem;
}}

h1, h2, h3 {{
    color: {INK};
}}

section[data-testid="stSidebar"] {{
    background-color: {PAPER};
    border-right: 1px solid {LINE};
}}

section[data-testid="stSidebar"] * {{
    color: {INK} !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 28px;
    border-bottom: 1px solid {LINE};
}}

.stTabs [data-baseweb="tab"] {{
    color: {SLATE};
    font-weight: 600;
}}

.stTabs [aria-selected="true"] {{
    color: {INK} !important;
    border-bottom: 3px solid {CLAY} !important;
}}

.metric-card {{
    background: {WHITE};
    border: 1px solid {LINE};
    padding: 18px;
    border-radius: 2px;
    min-height: 110px;
}}

.metric-label {{
    font-size: 0.78rem;
    color: {SLATE};
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

.metric-value {{
    font-size: 1.6rem;
    font-weight: 700;
    color: {INK};
}}

.status-ready {{
    color: #1E6B3A;
    border: 1px solid #1E6B3A;
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 700;
}}

.status-review {{
    color: {CLAY};
    border: 1px solid {CLAY};
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 700;
}}

.status-nofit {{
    color: #777777;
    border: 1px solid #BBBBBB;
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 700;
}}

.status-blocked {{
    color: white;
    background: {INK};
    border: 1px solid {INK};
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 700;
}}

.symbol-card {{
    background: {WHITE};
    border: 1px solid {LINE};
    border-left: 5px solid {CLAY};
    padding: 18px;
    margin-bottom: 14px;
}}

.symbol-title {{
    font-family: Georgia, serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: {INK};
}}

.symbol-meta {{
    color: {SLATE};
    font-size: 0.84rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 3px;
}}

.symbol-meaning {{
    color: #222222;
    font-family: Georgia, serif;
    font-size: 1rem;
    line-height: 1.55;
    margin-top: 10px;
}}

.usage-note {{
    margin-top: 10px;
    background: #FAF3EA;
    border-left: 3px solid {CLAY};
    padding: 9px 12px;
    font-size: 0.88rem;
    color: {SLATE};
}}

.culture-pill {{
    display: inline-block;
    color: white;
    padding: 3px 9px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

.value-chip {{
    display: inline-block;
    padding: 6px 12px;
    margin: 4px;
    border: 1px solid {INK};
    background: transparent;
    font-size: 0.86rem;
}}

.value-chip-strong {{
    border-color: {SLATE};
    color: {SLATE};
}}

.value-chip-possible {{
    border-color: #AAAAAA;
    color: #777777;
    border-style: dashed;
}}

.print-button {{
    background: {INK};
    color: white;
    border: none;
    padding: 10px 18px;
    cursor: pointer;
    font-weight: 700;
    letter-spacing: 0.04em;
}}

.extrait-wrap {{
    background: white;
    padding: 26px 34px;
    border: 1px solid {LINE};
}}

.extrait-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 2px solid {INK};
    padding-bottom: 16px;
    margin-bottom: 20px;
}}

.extrait-title {{
    font-family: Georgia, serif;
    font-size: 1.8rem;
    font-weight: 400;
    margin: 0;
}}

.extrait-sub {{
    color: {SLATE};
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

.extrait-section-title {{
    font-size: 0.92rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {CLAY};
    font-weight: 800;
    margin: 20px 0 10px;
}}

.extrait-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
}}

.extrait-symbol {{
    border: 1px solid {LINE};
    padding: 13px;
    page-break-inside: avoid;
}}

.extrait-symbol-name {{
    font-family: Georgia, serif;
    font-size: 1.05rem;
    font-weight: 700;
}}

.extrait-small {{
    font-size: 0.84rem;
    color: {SLATE};
}}

@media print {{
    @page {{
        size: A4 landscape;
        margin: 10mm;
    }}

    header[data-testid="stHeader"],
    #MainMenu,
    footer,
    [data-testid="stSidebar"],
    div[data-baseweb="tab-list"],
    div[data-testid="stToolbar"],
    .no-print {{
        display: none !important;
    }}

    .block-container {{
        padding: 0 !important;
        max-width: 100% !important;
    }}

    .stApp {{
        background: white !important;
    }}

    .extrait-wrap {{
        border: none;
        padding: 0;
    }}

    .extrait-grid {{
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
    }}

    .symbol-card {{
        page-break-inside: avoid;
    }}
}}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# HELPERS
# ==========================================================
def get_culture_color(culture_name):
    for key, color in CULTURE_COLORS.items():
        if key in culture_name:
            return color
    return SLATE

def classify_readiness(usage_status, similarity, usage_note):
    note = (usage_note or "").lower()

    if usage_status == "restricted":
        return "🚫 BLOCKED", "status-blocked", "BLOCKED"

    if similarity is None or similarity <= 0:
        return "❌ NO FIT", "status-nofit", "NO FIT"

    if any(k in note for k in SERIOUS_KEYWORDS):
        return "🔍 REVIEW", "status-review", "REVIEW"

    if similarity < 0.15:
        return "🔍 REVIEW", "status-review", "REVIEW"

    return "✅ READY", "status-ready", "READY"

def safe(x):
    return html.escape(str(x)) if x is not None else ""

# ==========================================================
# DATABASE
# ==========================================================
@st.cache_resource
def get_connection():
    return psycopg2.connect(dbname="kiarsy_affinity", user="yasso")

conn = get_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cur.execute("SELECT max(run_id) FROM scoring_runs")
RUN_ID = cur.fetchone()[0]

if RUN_ID is None:
    st.error("No scoring runs found. Run the scorer first.")
    st.stop()

# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    if os.path.exists(LOGO_EMBLEM):
        st.image(LOGO_EMBLEM, width=78)
    else:
        st.markdown("## KIARSY")

    st.markdown("---")
    st.caption("Cultural Affinity Engine")
    st.markdown(f"**Active Run:** #{RUN_ID}")

    cur.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
    companies = {r["company_name"]: r["company_id"] for r in cur.fetchall()}

    selected_company_name = st.selectbox("Company", list(companies.keys()))
    selected_company_id = companies[selected_company_name]

cur.execute("""
    SELECT company_name, industry, country_region
    FROM companies
    WHERE company_id = %s
""", (selected_company_id,))
company_info = cur.fetchone()

# ==========================================================
# LOAD COMMON DATA
# ==========================================================
cur.execute("""
    SELECT d.dimension_name, c.final_position, c.method
    FROM company_dimension_scores c
    JOIN dimensions d ON c.dimension_id = d.dimension_id
    WHERE c.company_id = %s
      AND c.run_id = %s
      AND c.final_position IS NOT NULL
    ORDER BY d.sort_order
""", (selected_company_id, RUN_ID))
dims_data = cur.fetchall()

cur.execute("""
    SELECT 
        s.symbol_id,
        s.symbol_name,
        cul.culture_name,
        s.documented_meaning,
        s.usage_status,
        s.usage_note,
        s.verification_level,
        a.similarity,
        a.raw_similarity,
        a.shared_dimensions,
        a.rank_in_culture
    FROM company_symbol_affinity a
    JOIN symbols s ON s.symbol_id = a.symbol_id
    JOIN cultures cul ON cul.culture_id = s.culture_id
    WHERE a.company_id = %s
      AND a.run_id = %s
    ORDER BY a.similarity DESC
""", (selected_company_id, RUN_ID))
all_matches = cur.fetchall()

cur.execute("""
    SELECT uv.value_name, cv.tier
    FROM company_values cv
    JOIN universal_values uv ON uv.value_id = cv.value_id
    WHERE cv.company_id = %s
    ORDER BY cv.tier, uv.value_name
""", (selected_company_id,))
value_rows = cur.fetchall()

# ==========================================================
# TABS
# ==========================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Company DNA",
    "🏆 Symbol Matches",
    "📄 Client Extrait",
    "⚙️ Admin"
])

# ==========================================================
# TAB 1 — COMPANY DNA
# ==========================================================
with tab1:
    st.title(f"Company DNA — {selected_company_name}")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Scored Dimensions</div>
            <div class="metric-value">{len(dims_data)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        ready_count = 0
        for m in all_matches:
            badge, css, label = classify_readiness(m["usage_status"], float(m["similarity"]), m["usage_note"])
            if label == "READY":
                ready_count += 1
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Ready Symbols</div>
            <div class="metric-value">{ready_count}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_c:
        top_symbol = all_matches[0]["symbol_name"] if all_matches else "—"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Top Match</div>
            <div style="font-size:1.05rem;font-weight:700;color:{INK};">{safe(top_symbol)}</div>
        </div>
        """, unsafe_allow_html=True)

    if dims_data:
        df_dims = pd.DataFrame(dims_data, columns=["Dimension", "Score", "Method"])
        df_dims["Score"] = df_dims["Score"].astype(float)

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
        r=df_dims["Score"].tolist() + [df_dims["Score"].iloc[0]],
            theta=df_dims["Dimension"].tolist() + [df_dims["Dimension"].iloc[0]],
            fill="toself",
            line_color=CLAY,
            fillcolor="rgba(192, 90, 54, 0.18)",
            name=selected_company_name
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], color=SLATE),
                bgcolor=PAPER
            ),
            showlegend=False,
            height=560,
            font=dict(color=INK)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Dimension Breakdown")
        st.dataframe(df_dims, use_container_width=True, hide_index=True)

# ==========================================================
# TAB 2 — SYMBOL MATCHES
# ==========================================================
with tab2:
    st.title(f"Symbol Matches — {selected_company_name}")

    cultures = sorted(set([m["culture_name"] for m in all_matches]))
    statuses = ["READY", "REVIEW", "NO FIT", "BLOCKED"]

    f1, f2, f3 = st.columns([1.2, 1.2, 1])

    with f1:
        selected_cultures = st.multiselect(
            "Filter by culture",
            cultures,
            default=cultures
        )

    with f2:
        selected_statuses = st.multiselect(
            "Filter by readiness",
            statuses,
            default=statuses
        )

    with f3:
        top_n = st.slider("Number of results", 5, 50, 15)

    filtered = []
    for m in all_matches:
        sim = float(m["similarity"])
        badge, css, label = classify_readiness(m["usage_status"], sim, m["usage_note"])

        if m["culture_name"] not in selected_cultures:
            continue
        if label not in selected_statuses:
            continue

        filtered.append((m, badge, css, label))

    filtered = filtered[:top_n]

    if not filtered:
        st.warning("No symbols match the selected filters.")
    else:
        for rank, (m, badge, css, label) in enumerate(filtered, 1):
            sim = float(m["similarity"])
            raw = float(m["raw_similarity"]) if m["raw_similarity"] is not None else None
            culture_color = get_culture_color(m["culture_name"])

            st.markdown(f"""
            <div class="symbol-card" style="border-left-color:{culture_color};">
                <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
                    <div>
                        <div class="symbol-title">{rank}. {safe(m["symbol_name"])}</div>
                        <div class="symbol-meta">
                            <span class="culture-pill" style="background:{culture_color};">{safe(m["culture_name"])}</span>
                            &nbsp; Similarity <b>{sim:.3f}</b>
                            &nbsp; Raw <b>{raw:.3f}</b>
                            &nbsp; Shared dims <b>{m["shared_dimensions"]}</b>
                        </div>
                    </div>
                    <span class="{css}">{badge}</span>
                </div>
                <div class="symbol-meaning">"{safe(m["documented_meaning"])}"</div>
                {f'<div class="usage-note">⚠️ {safe(m["usage_note"])}</div>' if m["usage_note"] else ""}
            </div>
            """, unsafe_allow_html=True)

# ==========================================================
# TAB 3 — CLIENT EXTRAIT
# ==========================================================
with tab3:
    st.title("Client Extrait")

    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])

    with c1:
        extrait_n = st.slider("Symbols in extract", 3, 10, 6)

    with c2:
        include_review = st.toggle("Include review symbols", value=True)

    with c3:
        components.html("""
        <button onclick="window.parent.print()" style="
            background:#111111;
            color:white;
            border:none;
            padding:10px 18px;
            font-weight:700;
            cursor:pointer;
            margin-top:26px;">
            🖨️ Print / Save as PDF
        </button>
        """, height=70)

    st.info("The extract is optimized for A4 landscape. You can also press Ctrl+P and choose “Save as PDF”.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Prepare extract symbols
    extrait_symbols = []
    for m in all_matches:
        sim = float(m["similarity"])
        badge, css, label = classify_readiness(m["usage_status"], sim, m["usage_note"])

        if label == "NO FIT" or label == "BLOCKED":
            continue
        if label == "REVIEW" and not include_review:
            continue

        extrait_symbols.append((m, badge, css, label))

    extrait_symbols = extrait_symbols[:extrait_n]

    # Values grouped
    tier_groups = {
        "Explicit": [],
        "Strongly Supported": [],
        "Possible": []
    }

    for r in value_rows:
        if r["tier"] in tier_groups:
            tier_groups[r["tier"]].append(r["value_name"])

    today_str = date.today().strftime("%d %B %Y")

    st.markdown('<div class="extrait-wrap">', unsafe_allow_html=True)

    # Header
    hcol1, hcol2 = st.columns([1, 2])
    with hcol1:
        if os.path.exists(LOGO_HORIZONTAL):
            st.image(LOGO_HORIZONTAL, width=210)
        else:
            st.markdown("## KIARSY")

    with hcol2:
        st.markdown(f"""
        <div style="text-align:right;">
            <div class="extrait-title">{safe(company_info["company_name"])}</div>
            <div class="extrait-sub">
                {safe(company_info["industry"])} · {safe(company_info["country_region"])} · {today_str}
            </div>
            <div class="extrait-sub">Cultural Affinity Extract · Run #{RUN_ID}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Top summary cards
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Cultural Dimensions</div>
            <div class="metric-value">{len(dims_data)}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Recommended Symbols</div>
            <div class="metric-value">{len(extrait_symbols)}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        best_name = extrait_symbols[0][0]["symbol_name"] if extrait_symbols else "—"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Leading Symbol</div>
            <div style="font-size:1.05rem;font-weight:700;">{safe(best_name)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Values
    st.markdown('<div class="extrait-section-title">I · Company Values</div>', unsafe_allow_html=True)

    for tier_name, values in tier_groups.items():
        if values:
            css = ""
            if tier_name == "Strongly Supported":
                css = "value-chip-strong"
            elif tier_name == "Possible":
                css = "value-chip-possible"

            st.markdown(f"<b>{tier_name}</b>", unsafe_allow_html=True)
            chips = "".join([f'<span class="value-chip {css}">{safe(v)}</span>' for v in values])
            st.markdown(chips, unsafe_allow_html=True)

    # Dimensions — compact bar view, easier than radar for print
    st.markdown('<div class="extrait-section-title">II · Strongest Cultural Signals</div>', unsafe_allow_html=True)

    if dims_data:
        df_dim = pd.DataFrame(dims_data, columns=["Dimension", "Score", "Method"])
        df_dim["Score"] = df_dim["Score"].astype(float)
        df_dim["distance"] = (df_dim["Score"] - 0.5).abs()
        df_dim = df_dim.sort_values("distance", ascending=False).head(6)

        for _, row in df_dim.iterrows():
            score = float(row["Score"])
            st.markdown(f"""
            <div style="margin:8px 0;">
                <div style="font-size:0.86rem;"><b>{safe(row["Dimension"])}</b> · {score:.3f}</div>
                <div style="height:8px;background:#EEE8DD;">
                    <div style="height:8px;background:{CLAY};width:{score*100:.1f}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Symbols
    st.markdown('<div class="extrait-section-title">III · Recommended Symbols</div>', unsafe_allow_html=True)

    if not extrait_symbols:
        st.warning("No client-ready or reviewable symbols available with current filters.")
    else:
        for i in range(0, len(extrait_symbols), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j >= len(extrait_symbols):
                    continue

                m, badge, css, label = extrait_symbols[i + j]
                sim = float(m["similarity"])
                culture_color = get_culture_color(m["culture_name"])

                with col:
                    st.markdown(f"""
                    <div class="extrait-symbol" style="border-left:5px solid {culture_color};">
                        <div style="display:flex;justify-content:space-between;gap:10px;">
                            <div class="extrait-symbol-name">{i+j+1}. {safe(m["symbol_name"])}</div>
                            <span class="{css}">{badge}</span>
                        </div>
                        <div class="extrait-small">
                            {safe(m["culture_name"])} · Alignment <b>{sim:.3f}</b> · {m["shared_dimensions"]} dims
                        </div>
                        <div style="font-family:Georgia,serif;margin-top:8px;font-size:0.95rem;line-height:1.45;">
                            “{safe(m["documented_meaning"])}”
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # Notes
    notes = []
    for m, badge, css, label in extrait_symbols:
        if m["usage_note"]:
            notes.append((m["symbol_name"], m["usage_note"]))

    if notes:
        st.markdown('<div class="extrait-section-title">IV · Usage Notes</div>', unsafe_allow_html=True)
        for name, note in notes[:6]:
            st.markdown(f"""
            <div class="extrait-small" style="margin-bottom:6px;">
                ⚠️ <b>{safe(name)}:</b> {safe(note)}
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="border-top:1px solid {LINE};margin-top:20px;padding-top:10px;text-align:center;color:{SLATE};font-size:0.78rem;text-transform:uppercase;letter-spacing:0.08em;">
        Generated by Kiarsy Cultural Affinity Engine · {today_str}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================================
# TAB 4 — ADMIN PLACEHOLDER
# ==========================================================
with tab4:
    st.title("Admin Portal")
    st.info("Next step: this tab will let employees add companies, paste evidence, assign value tiers, and launch scoring without editing code.")

    st.markdown("""
    Planned modules:
    - Add new company
    - Add/edit company values
    - Upload new symbol workbook
    - Run scorer
    - Generate client extract
    - Export PDF/report
    """)