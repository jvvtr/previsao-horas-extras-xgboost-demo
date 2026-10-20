"""Historical evaluation and recursive future-cycle projections."""

import pandas as pd
import streamlit as st

from .common import csv_download, line_chart, number


def render_forecast(meta, tables):
    monthly = tables["monthly"].copy()
    monthly["desvio_h"] = monthly.previstas - monthly.realizadas
    monthly["desvio_pct"] = monthly.desvio_h / monthly.realizadas.replace(0, float("nan")) * 100
    st.subheader("Histórico mensal: previsão e realizado")
    st.caption(
        f"Avaliação sintética: {monthly.ciclo.iloc[0]} a {monthly.ciclo.iloc[-1]}. "
        "Cada ponto é um ciclo operacional, com previsão feita um ciclo à frente."
    )
    cards = st.columns(3)
    cards[0].metric("MAPE · erro médio por ciclo", f"{number(meta['mape_pct'], 2)}%")
    cards[1].metric("WAPE · erro ponderado", f"{number(meta['wape_pct'], 2)}%")
    cards[2].metric("MAE · erro médio em horas", f"{number(meta['mae_hours'], 1)} h")
    chart = monthly.melt(
        id_vars="ciclo",
        value_vars=["realizadas", "previstas"],
        var_name="serie",
        value_name="horas",
    )
    chart["serie"] = chart.serie.map({"realizadas": "Realizado", "previstas": "Previsão do modelo"})
    chart["data"] = pd.to_datetime(chart.ciclo + "-15")
    st.altair_chart(line_chart(chart, ["Realizado", "Previsão do modelo"]), width="stretch")
    worst = monthly.loc[monthly.desvio_pct.abs().idxmax()]
    st.caption(
        f"Maior desvio: {worst.ciclo} ({number(abs(worst.desvio_pct), 2)}%). "
        f"Ciclo mais recente: {monthly.ciclo.iloc[-1]} "
        f"({number(abs(monthly.desvio_pct.iloc[-1]), 2)}% de erro)."
    )
    with st.expander("Ver a tabela mensal e baixar os resultados"):
        display = monthly.rename(
            columns={
                "ciclo": "Ciclo",
                "realizadas": "Realizado (h)",
                "previstas": "Previsto (h)",
                "desvio_h": "Desvio (h)",
                "desvio_pct": "Desvio (%)",
            }
        )
        st.dataframe(display, hide_index=True, width="stretch")
        csv_download("Baixar avaliação em CSV", display, "avaliacao_sintetica.csv")
    with st.expander("Entenda as métricas"):
        st.markdown(
            "**MAPE:** média dos erros percentuais absolutos dos ciclos. "
            "Cada ciclo tem o mesmo peso.\n\n"
            "**WAPE:** soma dos erros absolutos em horas ÷ soma das horas realizadas.\n\n"
            "**MAE:** média da distância em horas entre previsto e realizado.\n\n"
            "Exemplo: realizado de 1.000 h e previsto de 1.100 h significa "
            "erro absoluto de 100 h e erro percentual de 10%. MAPE não é taxa de acerto."
        )
    with st.expander("Ver a projeção dos próximos ciclos"):
        st.markdown("#### Próximos ciclos")
        controls = st.columns([1, 2])
        horizon = controls[0].slider("Ciclos para exibir", 1, 12, 3)
        window = controls[1].select_slider("Histórico no gráfico", [12, 24, 36], value=24)
        st.caption("Último ciclo completo: 2026-09. Projeções do modelo sintético desta edição.")
        forecast = tables["forecast"].head(horizon)
        cards = st.columns(3)
        cards[0].metric("Próximo ciclo previsto", f"{number(forecast.horas_previstas.iloc[0])} h")
        cards[1].metric("Total no horizonte", f"{number(forecast.horas_previstas.sum())} h")
        cards[2].metric("Pessoas no próximo ciclo", number(meta["people"]))
        history = tables["history"].tail(window).copy().assign(serie="Realizado")
        future = forecast.rename(columns={"horas_previstas": "horas"}).assign(serie="Previsão")
        combined = pd.concat([history, history.tail(1).assign(serie="Previsão"), future])
        combined["data"] = pd.to_datetime(combined.ciclo + "-15")
        st.altair_chart(line_chart(combined, ["Realizado", "Previsão"]), width="stretch")
        display = forecast.rename(
            columns={
                "ciclo": "Ciclo",
                "periodo": "Período",
                "horas_previstas": "Horas previstas",
                "pessoas_elegiveis": "Pessoas elegíveis",
            }
        )
        st.dataframe(display, hide_index=True, width="stretch")
        csv_download("Baixar projeções em CSV", display, "projecoes_sinteticas.csv")
        st.warning(
            "Do segundo ciclo em diante, as previsões anteriores alimentam o histórico. "
            "O erro histórico foi medido para um ciclo à frente e não valida os 12 horizontes."
        )
        st.caption(
            "A coorte fictícia permanece fixa. A simulação não antecipa admissões ou desligamentos."
        )
