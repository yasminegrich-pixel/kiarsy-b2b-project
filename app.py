import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
from datetime import date
import html
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

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
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "kiarsy_affinity"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )

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
# ==========================================================
# TAB 2 — SYMBOL MATCHES (internal view, unchanged layout)
# ==========================================================
def _readiness(status, sim, note):
    note = (note or "").lower()
    serious = ["slavery","captivity","sacred","funerary","funeral","reserved for",
               "legal","eagle feather","katsina","kachina","do not use","do not reproduce","religious"]
    if status == "restricted":
        return "🚫 BLOCKED", "status-blocked", "BLOCKED"
    if sim is None or sim <= 0:
        return "❌ NO FIT", "status-nofit", "NO FIT"
    if any(k in note for k in serious):
        return "🔍 REVIEW", "status-review", "REVIEW"
    if sim < 0.15:
        return "🔍 REVIEW", "status-review", "REVIEW"
    return "✅ READY", "status-ready", "READY"

with tab2:
    st.title(f"Symbol Matches — {selected_company_name}")

    cultures = sorted(set([m["culture_name"] for m in all_matches]))
    statuses = ["READY", "REVIEW", "NO FIT", "BLOCKED"]

    f1, f2, f3 = st.columns([1.2, 1.2, 1])
    with f1:
        selected_cultures = st.multiselect("Filter by culture", cultures, default=cultures)
    with f2:
        selected_statuses = st.multiselect("Filter by readiness", statuses, default=statuses)
    with f3:
        top_n = st.slider("Number of results", 5, 50, 15)

    filtered = []
    for m in all_matches:
        sim = float(m["similarity"])
        badge, css, label = _readiness(m["usage_status"], sim, m["usage_note"])
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
            raw_txt = f"{raw:.3f}" if raw is not None else "—"
            culture_color = get_culture_color(m["culture_name"])
            note_html = f'<div class="usage-note">⚠️ {safe(m["usage_note"])}</div>' if m["usage_note"] else ""
            st.markdown(f"""
            <div class="symbol-card" style="border-left-color:{culture_color};">
                <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
                    <div>
                        <div class="symbol-title">{rank}. {safe(m["symbol_name"])}</div>
                        <div class="symbol-meta">
                            <span class="culture-pill" style="background:{culture_color};">{safe(m["culture_name"])}</span>
                            &nbsp; Similarity <b>{sim:.3f}</b>
                            &nbsp; Raw <b>{raw_txt}</b>
                            &nbsp; Shared dims <b>{m["shared_dimensions"]}</b>
                        </div>
                    </div>
                    <span class="{css}">{badge}</span>
                </div>
                <div class="symbol-meaning">"{safe(m["documented_meaning"])}"</div>
                {note_html}
            </div>
            """, unsafe_allow_html=True)

# ==========================================================
# TAB 3 — CLIENT EXTRAIT (clean, client-facing: no badges, no notes)
# ==========================================================
with tab3:
    st.title("Client Extrait")

    c1, c2 = st.columns([1, 3])
    with c1:
        extrait_n = st.slider("Symbols in extract", 3, 10, 6)
    with c2:
        components.html("""
        <button onclick="window.parent.print()" style="background:#111111;color:white;border:none;
        padding:10px 18px;font-weight:700;cursor:pointer;margin-top:26px;">🖨️ Print / Save as PDF</button>
        """, height=70)
    st.caption("You can also press Ctrl+P and choose “Save as PDF”. The layout is print-optimized (A4 landscape).")

    # READY + REVIEW symbols appear, but with NO internal flags shown
    extrait_symbols = []
    for m in all_matches:
        sim = float(m["similarity"])
        badge, css, label = _readiness(m["usage_status"], sim, m["usage_note"])
        if label in ("NO FIT", "BLOCKED"):
            continue
        extrait_symbols.append((m, sim))
    extrait_symbols = extrait_symbols[:extrait_n]

    cur.execute("""SELECT uv.value_name, cv.tier FROM company_values cv
                   JOIN universal_values uv ON uv.value_id = cv.value_id
                   WHERE cv.company_id = %s""", (selected_company_id,))
    tier_groups = {"Explicit": [], "Strongly Supported": [], "Possible": []}
    for r in cur.fetchall():
        if r["tier"] in tier_groups:
            tier_groups[r["tier"]].append(r["value_name"])

    today_str = date.today().strftime("%d %B %Y")
    st.markdown('<div class="extrait-wrap">', unsafe_allow_html=True)

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
            <div class="extrait-sub">{safe(company_info["industry"])} · {safe(company_info["country_region"])} · {today_str}</div>
            <div class="extrait-sub">Cultural Affinity Extract · Run #{RUN_ID}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Cultural Dimensions</div><div class="metric-value">{len(dims_data)}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Recommended Symbols</div><div class="metric-value">{len(extrait_symbols)}</div></div>', unsafe_allow_html=True)
    with m3:
        best = extrait_symbols[0][0]["symbol_name"] if extrait_symbols else "—"
        st.markdown(f'<div class="metric-card"><div class="metric-label">Leading Symbol</div><div style="font-size:1.05rem;font-weight:700;">{safe(best)}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="extrait-section-title">I · Company Values</div>', unsafe_allow_html=True)
    for tier_name, vals in tier_groups.items():
        if vals:
            chip = "" if tier_name == "Explicit" else ("value-chip-strong" if tier_name == "Strongly Supported" else "value-chip-possible")
            st.markdown(f"<b>{tier_name}</b>", unsafe_allow_html=True)
            st.markdown("".join(f'<span class="value-chip {chip}">{safe(v)}</span>' for v in vals), unsafe_allow_html=True)

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
                <div style="height:8px;background:#EEE8DD;"><div style="height:8px;background:{CLAY};width:{score*100:.1f}%;"></div></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="extrait-section-title">III · Recommended Symbols</div>', unsafe_allow_html=True)
    if not extrait_symbols:
        st.warning("No client-suitable symbols available.")
    else:
        for i in range(0, len(extrait_symbols), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(extrait_symbols):
                    continue
                m, sim = extrait_symbols[idx]
                culture_color = get_culture_color(m["culture_name"])
                with col:
                    st.markdown(f"""
                    <div class="extrait-symbol" style="border-left:5px solid {culture_color};">
                        <div class="extrait-symbol-name">{idx+1}. {safe(m["symbol_name"])}</div>
                        <div class="extrait-small">{safe(m["culture_name"])} · Alignment <b>{sim:.3f}</b> · {m["shared_dimensions"]} dims</div>
                        <div style="font-family:Georgia,serif;margin-top:8px;font-size:0.95rem;line-height:1.45;">“{safe(m["documented_meaning"])}”</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="border-top:1px solid {LINE};margin-top:20px;padding-top:10px;text-align:center;color:{SLATE};
    font-size:0.78rem;text-transform:uppercase;letter-spacing:0.08em;">
        Generated by Kiarsy Cultural Affinity Engine · {today_str}
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================================
# TAB 4 — ADMIN (add / scrape / delete)
# ==========================================================
with tab4:
    st.title("⚙️ Admin Portal")
    admin_tab1, admin_tab2 = st.tabs(["➕ Add / Scrape Company", "🗑️ Manage / Delete Companies"])

    with admin_tab1:
        st.subheader("Add New Company")
        with st.form("add_company_form"):
            c_name = st.text_input("Company Name")
            c_ind = st.text_input("Industry")
            c_reg = st.text_input("Region / Country")
            c_url = st.text_input("Website URL (e.g., https://company.com)")
            submitted = st.form_submit_button("1. Scrape Website Text")

        if submitted and c_url:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urlparse, urljoin

            def scrape_site(url, timeout=15):
                HEADERS = {"User-Agent": "Mozilla/5.0 (Kiarsy Cultural Affinity Engine)"}
                def clean(soup):
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                        tag.decompose()
                    return " ".join(soup.get_text(separator=" ", strip=True).split())
                def try_fetch(u):
                    try:
                        r = requests.get(u, headers=HEADERS, timeout=timeout, allow_redirects=True)
                        if r.status_code == 200:
                            return r.text
                    except Exception:
                        pass
                    return None
                html_txt = try_fetch(url)
                if html_txt:
                    c_soup = BeautifulSoup(html_txt, "html.parser")
                    c_text = clean(c_soup)
                    links = c_soup.find_all("a", href=True)
                    targets = set()
                    keywords = ["a-propos", "qui-sommes-nous", "rse", "csr", "engagement", "valeurs", "about", "mission"]
                    for link in links:
                        href = link["href"].lower()
                        if any(k in href for k in keywords):
                            targets.add(urljoin(url, link["href"]))
                    for deep in list(targets)[:2]:
                        sub = try_fetch(deep)
                        if sub:
                            c_text += "\n\n" + clean(BeautifulSoup(sub, "html.parser"))
                    return c_text, url
                return None, None

            with st.spinner("Scraping website..."):
                text_res, used_url = scrape_site(c_url)
            if text_res:
                st.session_state["scraped_text"] = text_res
                st.session_state["form_name"] = c_name
                st.session_state["form_ind"] = c_ind
                st.session_state["form_reg"] = c_reg
                st.rerun()
            else:
                st.error("❌ Could not connect to this URL.")
                st.session_state["scraped_text"] = ""

        if st.session_state.get("scraped_text"):
            st.markdown("---")
            st.subheader("2. Review Text & Assign Values")
            if len(st.session_state["scraped_text"]) < 1000:
                st.warning("⚠️ This site loads content via JavaScript; only surface text was captured. Paste fuller text below if needed.")
            edited_text = st.text_area("Scraped / pasted text", value=st.session_state["scraped_text"], height=220)

            cur.execute("SELECT value_id, value_name FROM universal_values ORDER BY value_id")
            uvs = cur.fetchall()
            tiers = ["Explicit", "Strongly Supported", "Possible"]
            value_assignments = []
            for v in uvs:
                cols = st.columns([0.5, 2.5, 2, 4])
                with cols[0]:
                    checked = st.checkbox("Use", key=f"chk_{v['value_id']}")
                with cols[1]:
                    st.markdown(f"**{v['value_name']}**")
                with cols[2]:
                    tier = st.selectbox("Tier", tiers, key=f"tier_{v['value_id']}", disabled=not checked)
                with cols[3]:
                    quote = st.text_input("Evidence quote", key=f"quote_{v['value_id']}", disabled=not checked)
                if checked:
                    value_assignments.append((v["value_id"], tier, quote))

            if st.button("3. Save Company to Database", type="primary"):
                if not st.session_state.get("form_name"):
                    st.error("Company name missing.")
                elif not edited_text:
                    st.error("Text is empty.")
                else:
                    try:
                        c_id = f"CO-{uuid.uuid4().hex[:4].upper()}"
                        cur.execute("""INSERT INTO companies (company_id, company_name, industry, country_region, company_summary)
                                       VALUES (%s,%s,%s,%s,%s)""",
                                    (c_id, st.session_state["form_name"], st.session_state.get("form_ind"),
                                     st.session_state.get("form_reg"), edited_text))
                        for vid, tier, quote in value_assignments:
                            cur.execute("""INSERT INTO company_values (company_id, value_id, tier, evidence_summary)
                                           VALUES (%s,%s,%s,%s)""", (c_id, vid, tier, quote))
                        conn.commit()
                        st.success(f"✅ Saved {st.session_state['form_name']}. Now run the auto-pipeline to score it:")
                        st.code(f'python scripts/auto_pipeline.py "{st.session_state["form_name"]}" "<url>"')
                        for k in ["scraped_text", "form_name", "form_ind", "form_reg"]:
                            st.session_state.pop(k, None)
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Database error: {e}")

    with admin_tab2:
        st.subheader("Manage / Delete Companies")
        st.warning("⚠️ Deleting a company permanently removes its values, scores, and symbol matches.")
        cur.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
        all_companies = {r["company_name"]: r["company_id"] for r in cur.fetchall()}
        if all_companies:
            del_name = st.selectbox("Select company to delete", list(all_companies.keys()))
            del_id = all_companies[del_name]
            if st.button("🗑️ Delete Company Permanently", type="primary"):
                try:
                    cur.execute("DELETE FROM company_symbol_affinity WHERE company_id = %s", (del_id,))
                    cur.execute("DELETE FROM company_dimension_scores WHERE company_id = %s", (del_id,))
                    cur.execute("DELETE FROM company_values WHERE company_id = %s", (del_id,))
                    cur.execute("DELETE FROM companies WHERE company_id = %s", (del_id,))
                    conn.commit()
                    st.success(f"✅ {del_name} deleted.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Failed to delete: {e}")
        else:
            st.info("No companies in the database.")
