"""Dashboard spacing, typography, and neutral card treatments."""

import streamlit as st


def apply_style() -> None:
    st.markdown(
        """<style>
    :root { --ink:#193247; --muted:#647789; --line:#e3e9ee; --surface:#ffffff; }
    [data-testid="stMainBlockContainer"]{max-width:1320px;padding-top:2rem;padding-bottom:3rem;}
    [data-testid="stHeader"]{background:rgba(245,247,250,.92);}
    [data-testid="stSidebar"]{border-right:1px solid var(--line);}
    h1,h2,h3,h4{color:var(--ink);letter-spacing:-.025em;}
    h2{font-size:1.55rem!important;margin-top:1.5rem!important;}
    h3{font-size:1.2rem!important;}
    p,li{line-height:1.65;}
    [data-testid="stMetric"]{background:var(--surface);border:1px solid var(--line);
      border-radius:12px;padding:16px 18px;min-height:105px;}
    [data-testid="stMetricLabel"]{color:var(--muted);font-size:.82rem;}
    [data-testid="stMetricValue"]{color:var(--ink);font-size:1.7rem;font-weight:650;}
    [data-testid="stMetricDelta"]{font-size:.8rem;}
    .hero{background:#fff;border:1px solid var(--line);border-radius:16px;
      padding:24px 30px;margin:0 0 22px;box-shadow:0 4px 18px rgba(25,50,71,.035);}
    .hero .eyebrow{color:#087f73;font-size:.72rem;letter-spacing:.12em;
      font-weight:700;text-transform:uppercase;}
    .hero h1{color:var(--ink);font-size:2rem;margin:.4rem 0;font-weight:680;}
    .hero p{color:var(--muted);margin:0;line-height:1.6;}
    .stTabs [data-baseweb="tab-list"]{gap:28px;border-bottom:1px solid var(--line);margin-bottom:24px;}
    .stTabs [data-baseweb="tab"]{font-weight:600;padding:13px 2px;color:#52687a;}
    .stTabs [aria-selected="true"]{color:#087f73;}
    [data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:10px;overflow:hidden;}
    [data-testid="stExpander"]{border:1px solid var(--line);border-radius:10px;background:#fff;}
    [data-testid="stAlert"]{border-radius:10px;}
    hr{border-color:var(--line);}
    @media(max-width:760px){
      [data-testid="stMainBlockContainer"]{padding:3.7rem 1rem 1.5rem;}
      .hero{padding:20px;}.hero h1{font-size:1.55rem;}
      .stTabs [data-baseweb="tab-list"]{gap:16px;overflow-x:auto;}
      [data-testid="stMetricValue"]{font-size:1.35rem;}
      [data-testid="stHorizontalBlock"]{flex-wrap:wrap;}
      [data-testid="stColumn"]{flex:1 1 calc(50% - 12px)!important;min-width:220px!important;}
    }
    </style>""",
        unsafe_allow_html=True,
    )
