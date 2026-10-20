"""Public Streamlit demonstration built exclusively from synthetic records."""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import xgboost as xgb

from demo_pipeline import audit_demo

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
LABELS = {
    "horas_ciclo_anterior": "Horas no ciclo anterior",
    "media_3_ciclos": "Média dos três ciclos anteriores",
    "mes_sin": "Época do ano (seno)",
    "mes_cos": "Época do ano (cosseno)",
    **{f"unidade_{i}": f"Unidade {chr(65 + i)}" for i in range(3)},
    **{f"funcao_{i}": role for i, role in enumerate(("Operação", "Manutenção", "Logística"))},
}


def pt(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


@st.cache_data(show_spinner=False)
def load_data() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    metadata = json.loads((ARTIFACTS / "metadata.json").read_text(encoding="utf-8"))
    return (
        metadata,
        pd.read_csv(ARTIFACTS / "monthly.csv"),
        pd.read_csv(ARTIFACTS / "future_features.csv"),
    )


@st.cache_resource(show_spinner=False)
def load_model() -> xgb.Booster:
    model = xgb.Booster()
    model.load_model(ARTIFACTS / "demo_model.json")
    return model


def tree_paths(nodes: pd.DataFrame, tree_id: int) -> pd.DataFrame:
    """Describe the decisions in one numeric tree of the synthetic booster."""
    rows = nodes.loc[nodes.Tree.eq(tree_id - 1)].set_index("Node")
    paths: list[dict] = []

    def walk(node: int, conditions: list[str]) -> None:
        row = rows.loc[node]
        if row.Feature == "Leaf":
            paths.append(
                {
                    "Perguntas e respostas": " → ".join(conditions) or "Folha única",
                    "Ajuste por pessoa (h)": float(row.Gain),
                }
            )
            return
        name = LABELS.get(str(row.Feature), str(row.Feature))
        limit = pt(float(row.Split), 2)
        yes = int(str(row.Yes).rsplit("-", 1)[-1])
        no = int(str(row.No).rsplit("-", 1)[-1])
        walk(yes, [*conditions, f"{name} < {limit}"])
        walk(no, [*conditions, f"{name} ≥ {limit}"])

    walk(0, [])
    return pd.DataFrame(paths)


def forecast_page(meta: dict, monthly: pd.DataFrame) -> None:
    st.subheader("Previsão e comparação mensal")
    st.write(
        "O gráfico compara totais previstos e realizados fora do treino. Todos os registros "
        "desta demonstração foram criados por um gerador sintético."
    )
    columns = st.columns(3)
    columns[0].metric("Erro médio percentual · demo", f"{pt(meta['mape_pct'], 2)}%")
    columns[1].metric("Erro ponderado · demo", f"{pt(meta['wape_pct'], 2)}%")
    columns[2].metric(
        f"Próximo ciclo · {meta['future_cycle']}", f"{pt(meta['future_hours'])} h"
    )
    chart_data = monthly.melt(
        id_vars="ciclo", value_vars=["realizadas", "previstas"], var_name="Série", value_name="Horas"
    )
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("ciclo:N", title="Ciclo", sort=monthly.ciclo.tolist()),
            y=alt.Y("Horas:Q", title="Horas extras sintéticas"),
            color=alt.Color(
                "Série:N",
                scale=alt.Scale(
                    domain=["realizadas", "previstas"], range=["#55718a", "#087f73"]
                ),
            ),
            tooltip=["ciclo:N", "Série:N", alt.Tooltip("Horas:Q", format=",.1f")],
        )
        .properties(height=350)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "Teste de um ciclo à frente: o histórico realizado do ciclo anterior é conhecido. "
        "O valor futuro usa o último histórico sintético disponível."
    )


def explanation_page(meta: dict, future: pd.DataFrame) -> None:
    st.subheader("Como o modelo chegou à previsão?")
    st.write(
        "Cada pessoa fictícia começa com um valor-base. As árvores ajustam esse valor "
        "conforme o histórico e o perfil; a calibração por função é aplicada antes da soma."
    )
    trace = audit_demo(load_model(), future, meta["calibration_factors"])
    columns = st.columns(3)
    columns[0].metric("Base do cálculo", f"{pt(trace['base_hours'])} h")
    columns[1].metric("Ajustes das árvores", f"{pt(trace['tree_hours'])} h")
    columns[2].metric("Previsão final", f"{pt(trace['total_hours'])} h")
    with st.container(border=True):
        st.markdown("#### A conta, passo a passo")
        st.markdown(
            f"**1. Valor inicial: {pt(trace['base_score'], 6)} h por pessoa.** "
            "O XGBoost o estimou com os dados sintéticos de treino; ele fica gravado "
            "no booster e não é a média do mês previsto."
        )
        st.markdown(
            f"**2. Quem entra: {pt(trace['people'])} pessoas fictícias.** "
            f"{pt(trace['zeroed'])} tiveram previsão bruta não positiva. Para as outras "
            f"{pt(trace['positive'])}, somamos os fatores por função: "
            f"**{pt(trace['factor_sum'], 2)}**. Essa soma não é um número de pessoas."
        )
        st.markdown(
            f"**3. Base: {pt(trace['base_score'], 6)} × {pt(trace['factor_sum'], 2)} "
            f"≈ {pt(trace['base_hours'], 2)} h.** "
            f"As {meta['tree_count']} árvores acrescentam {pt(trace['tree_hours'], 2)} h, "
            f"chegando a **{pt(trace['total_hours'], 2)} h**."
        )
        st.caption(
            "A auditoria usa as folhas realmente percorridas; a multiplicação exibida "
            "é aproximada porque os fatores estão arredondados."
        )
    st.markdown("#### Quais árvores mais alteraram o total?")
    trees = trace["trees"]
    largest = trees.assign(magnitude=trees.efeito_horas.abs()).nlargest(15, "magnitude")
    chart = (
        alt.Chart(largest)
        .mark_bar()
        .encode(
            x=alt.X("efeito_horas:Q", title="Efeito agregado após calibração (h)"),
            y=alt.Y("arvore:O", title="Árvore", sort="-x"),
            color=alt.condition(
                alt.datum.efeito_horas >= 0, alt.value("#087f73"), alt.value("#ca8751")
            ),
            tooltip=["arvore:O", alt.Tooltip("efeito_horas:Q", format="+.2f")],
        )
        .properties(height=340)
    )
    st.altair_chart(chart, width="stretch")
    selected = st.selectbox(
        "Veja as perguntas de uma árvore",
        trees.arvore.tolist(),
        index=trees.arvore.tolist().index(int(largest.iloc[0].arvore)),
        format_func=lambda tree: f"Árvore {tree}",
    )
    st.dataframe(
        tree_paths(trace["nodes"], selected),
        hide_index=True,
        width="stretch",
        column_config={"Ajuste por pessoa (h)": st.column_config.NumberColumn(format="%+.4f")},
    )
    st.caption("Uma árvore isolada não explica o total: seus ajustes se somam aos demais.")


def method_page(meta: dict) -> None:
    st.subheader("Método e limites desta demonstração")
    st.markdown(
        f"""**1. Dados.** Um gerador determinístico cria {meta["people"]} pessoas fictícias
em três unidades e três funções inventadas. Nenhum registro ou modelo do projeto privado
entra neste repositório.

**2. Treino.** O XGBoost aprende com {meta["training_cycles"][0]} a
{meta["training_cycles"][1]}. Usa somente mês, unidade, função e horas de ciclos anteriores.

**3. Calibração.** Os fatores são calculados com {meta["calibration_cycles"][0]} a
{meta["calibration_cycles"][1]}. O teste de {meta["test_cycles"][0]} a
{meta["test_cycles"][1]} não ajusta esses fatores.

**4. Previsão.** Cada uma das {meta["tree_count"]} árvores aplica pequenos ajustes.
Previsões negativas são zeradas; a saída positiva é calibrada e agregada por ciclo."""
    )
    st.info(
        "Os indicadores e volumes exibidos neste app pertencem apenas à simulação. "
        "Eles não reproduzem o desempenho nem os dados do modelo privado."
    )
    st.code("python scripts/build_demo.py", language="bash")
    st.caption("O comando regenera todos os artefatos públicos com a mesma semente sintética.")


def main() -> None:
    st.set_page_config(
        page_title="Previsão de horas extras · demo sintética", page_icon="📊", layout="wide"
    )
    st.markdown(
        """<style>
[data-testid="stMainBlockContainer"]{max-width:1180px;padding-top:2rem}
.hero{border:1px solid #dfe8ed;border-radius:16px;padding:24px 28px;background:#fff;margin-bottom:20px}
.hero small{color:#087f73;font-weight:700;letter-spacing:.08em}
.hero h1{color:#193247;margin:.3rem 0}
.hero p{color:#526779;margin:0;line-height:1.6}
[data-testid="stMetric"]{background:#fff;border:1px solid #dfe8ed;border-radius:12px;padding:14px}
</style>
<div class="hero"><small>DEMONSTRAÇÃO PÚBLICA · DADOS 100% SINTÉTICOS</small>
<h1>Previsão de horas extras</h1>
<p>Uma versão reproduzível do fluxo de previsão e explicabilidade.
Os números e o modelo desta página são fictícios e independentes do projeto privado.</p></div>""",
        unsafe_allow_html=True,
    )
    try:
        meta, monthly, future = load_data()
    except FileNotFoundError:
        st.error("Artefatos ausentes. Execute python scripts/build_demo.py.")
        st.stop()
    if meta.get("data_origin") != "synthetic":
        st.error("A demonstração aceita somente artefatos marcados como sintéticos.")
        st.stop()
    forecast, explanation, method = st.tabs(
        ["Previsão", "Explicabilidade das árvores", "Como funciona"],
        key="main_page",
        on_change="rerun",
    )
    if forecast.open:
        with forecast:
            forecast_page(meta, monthly)
    if explanation.open:
        with explanation:
            explanation_page(meta, future)
    if method.open:
        with method:
            method_page(meta)


if __name__ == "__main__":
    main()
