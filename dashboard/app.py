"""Three pages mirroring the final official dashboard, on fictional records."""

import logging

import streamlit as st

from .common import load_artifacts, render_safely, version
from .forecast import render_forecast
from .method import render_method
from .style import apply_style
from .trees import render_trees


def main():
    st.set_page_config(
        page_title="Previsão de horas extras · demonstração", page_icon="📊", layout="wide"
    )
    apply_style()
    st.markdown(
        '<div class="hero"><div class="eyebrow">Demonstração pública · dados 100% sintéticos '
        "· ciclo do dia 16 ao dia 15</div><h1>Previsão de horas extras</h1>"
        "<p>Histórico mensal, explicação das árvores e uma leitura clara de como o XGBoost calcula.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Dados, pessoas, unidades, modelo e indicadores desta edição são fictícios. "
        "A experiência reproduz o fluxo do projeto privado, com resultados próprios."
    )
    try:
        signature = version()
        meta, tables = load_artifacts(signature)
    except Exception:
        logging.getLogger(__name__).exception("Falha ao carregar artefatos sintéticos")
        st.error(
            "Artefatos indisponíveis ou incompatíveis. Reinicie a aplicação. "
            "Se necessário, execute python scripts/build_demo.py para regenerar a demonstração."
        )
        st.stop()
    forecast, trees, method = st.tabs(
        ["Previsão", "Explicabilidade das árvores", "Como funciona o XGBoost"],
        key="main_page",
        on_change="rerun",
    )
    if forecast.open:
        with forecast:
            render_safely(render_forecast, meta, tables)
    if trees.open:
        with trees:
            render_safely(render_trees, meta, tables, signature)
    if method.open:
        with method:
            render_safely(render_method, meta, tables)
