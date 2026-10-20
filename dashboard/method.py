"""Plain-language methodology with examples and synthetic training details."""

import pandas as pd
import streamlit as st

from demo_pipeline import FEATURES
from tree_audit import LABELS

from .common import ROOT, number


def render_method(meta, tables):
    st.subheader("Como o XGBoost transforma dados em uma previsão")
    st.caption(
        "O modelo estima horas por pessoa e ciclo. Depois, o sistema calibra "
        "por função e soma os resultados."
    )
    monthly = tables["monthly"]
    recent = monthly.loc[monthly.ciclo.str.startswith("2026-")]
    recent_mape = ((recent.previstas - recent.realizadas).abs() / recent.realizadas).mean() * 100
    cards = st.columns(4)
    cards[0].metric("Árvores usadas", number(meta["tree_count"]))
    cards[1].metric("MAPE · teste completo", f"{number(meta['mape_pct'], 2)}%")
    cards[2].metric("WAPE · teste completo", f"{number(meta['wape_pct'], 2)}%")
    cards[3].metric("MAPE · jan–set/2026", f"{number(recent_mape, 2)}%")
    st.markdown("#### O cálculo, em quatro etapas")
    for column, text in zip(
        st.columns(4),
        [
            "**1 · Organiza**\n\nCada linha é uma pessoa fictícia em um ciclo de 16 a 15.",
            "**2 · Compara**\n\nLê histórico individual, função, unidade e calendário.",
            f"**3 · Ajusta**\n\nAs {number(meta['tree_count'])} árvores corrigem a estimativa inicial.",
            "**4 · Soma**\n\nZera saídas negativas, calibra por função e soma a coorte.",
        ],
        strict=True,
    ):
        column.markdown(text)
    with st.container(border=True):
        st.markdown(f"#### O que significa ter {number(meta['tree_count'])} árvores?")
        st.write(
            "Cada árvore faz perguntas como ‘as horas do ciclo anterior são menores que "
            "6?’. A resposta conduz a outra pergunta ou a uma folha. A folha guarda "
            "um pequeno ajuste positivo ou negativo em horas por pessoa."
        )
        st.write(
            "Durante o treino, novas árvores tentam corrigir o que o conjunto anterior "
            "ainda erra. Na previsão, todos esses ajustes são somados ao valor inicial. "
            "Não são previsões independentes nem uma votação."
        )
        st.code(
            "valor inicial + folha da árvore 1 + … + folha da árvore 1.229\n"
            "→ máximo entre resultado e zero → fator da função → soma das pessoas",
            language="text",
        )
        st.markdown(
            "**Exemplo ilustrativo:** ponto inicial de 4 h; ajustes de +1,2 h, −0,3 h "
            "e +0,1 h resultam em 5 h. Com fator de calibração 1,10, essa pessoa "
            "contribui com 5,5 h para o total. Os valores desse exemplo são didáticos."
        )
        st.caption(
            "A quantidade de 1.229 árvores reproduz a experiência da edição oficial. "
            "O booster público foi treinado do zero, e essa quantidade não foi otimizada na simulação."
        )
    st.markdown("#### Que informações entram no modelo")
    st.dataframe(
        pd.DataFrame(
            [
                ("Perfil e vínculo", "Unidade, função e tempo de casa fictícios."),
                (
                    "Histórico individual",
                    "Horas anteriores e médias dos últimos três e seis ciclos.",
                ),
                ("Tipo de dia", "Divisão sintética entre extras em dias de trabalho e em folgas."),
                ("Calendário", "Sazonalidade e quantidade de dias de segunda a sexta no ciclo."),
                ("Equipe", "Média anterior das pessoas da mesma unidade e função."),
            ],
            columns=["Grupo", "Como ajuda a estimar"],
        ),
        hide_index=True,
        width="stretch",
    )
    st.markdown("#### Como foi avaliado")
    for column, title, key, explanation in zip(
        st.columns(3),
        ["Aprendizado", "Calibração", "Avaliação registrada"],
        ["training_cycles", "calibration_cycles", "test_cycles"],
        [
            "Aprende as perguntas e os ajustes das árvores.",
            "Calcula fatores por função para ajustar a escala.",
            "Mede previsões de um ciclo à frente sem ajustar fatores com o teste.",
        ],
        strict=True,
    ):
        column.markdown(f"**{title}**\n\n{meta[key][0]} a {meta[key][1]}\n\n{explanation}")
    st.info(
        "Todos os indicadores pertencem apenas à simulação. "
        "O MAPE é erro percentual médio, não uma taxa de acerto. "
        "O recorte de 2026 tem menos ciclos e não substitui o teste completo."
    )
    st.markdown("#### Como a calibração funciona")
    st.write(
        "O objetivo de treino é o erro absoluto por pessoa. Mesmo assim, a soma pode "
        "ficar sistematicamente acima ou abaixo do total. Em 2024, calculamos a razão "
        "entre horas realizadas e previstas por função e a razão global. Misturamos "
        "60% da razão da função com 40% da global e limitamos o fator entre 0,75 e 1,35. "
        "O teste usa esses fatores congelados."
    )
    st.dataframe(
        pd.DataFrame(meta["calibration_factors"].items(), columns=["Função fictícia", "Fator"]),
        hide_index=True,
        width="stretch",
    )
    st.markdown("#### O que a explicação permite concluir")
    st.write(
        "A trilha das árvores prova como a implementação chegou ao valor. As contribuições "
        "SHAP distribuem a previsão entre informações usando uma referência do modelo. "
        "Nenhuma dessas leituras comprova causas ou justifica uma hora extra operacionalmente."
    )
    st.write(
        "O teste usa o realizado do ciclo anterior. As projeções futuras são recursivas e "
        "mantêm a coorte fixa. Não simulamos admissões, desligamentos, feriados locais ou "
        "a necessidade real de cobertura. A demonstração não é uma ferramenta de decisão de pessoal."
    )
    with st.expander("Detalhes técnicos do treinamento"):
        st.dataframe(
            pd.DataFrame({"Variável usada": [LABELS.get(name, name) for name in FEATURES]}),
            hide_index=True,
            width="stretch",
        )
        st.json(
            {
                "objective": "reg:absoluteerror",
                "max_depth": 3,
                "eta": 0.025,
                "seed": meta["seed"],
                "tree_count": meta["tree_count"],
                "tree_count_policy": meta["tree_count_policy"],
                "data_origin": meta["data_origin"],
            }
        )
    with st.expander("Abrir a documentação técnica completa"):
        st.markdown((ROOT / "docs" / "02-modelo.md").read_text(encoding="utf-8"))
