"""Full forecast reconciliation, feature effects and an interactive tree inventory."""

import streamlit as st

from tree_audit import LABELS, audit_package, tree_diagram, tree_dump

from .common import (
    csv_download,
    effect_chart,
    load_audit,
    load_catalog,
    load_model,
    number,
)


def render_trace(trace, saved, cycle, signature):
    cards = st.columns(4)
    cards[0].metric("Valor salvo no painel", f"{number(saved)} h")
    cards[1].metric("Reconstruído pelas árvores", f"{number(trace['total_hours'])} h")
    cards[2].metric("Base do modelo", f"{number(trace['base_hours'])} h")
    cards[3].metric("Soma das árvores", f"{number(trace['tree_hours'])} h")
    st.markdown(
        f"**Reconciliação:** base de {number(trace['base_hours'], 2)} h + "
        f"ajustes das {number(len(trace['trees']))} árvores "
        f"({number(trace['tree_hours'], 2)} h) = **{number(trace['total_hours'], 2)} h**."
    )
    with st.container(border=True):
        st.markdown("#### Como chegamos à base desta previsão?")
        st.markdown(
            f"**1. Ponto de partida: {number(trace['base_score'], 6)} h por pessoa.** "
            "É o intercepto que o XGBoost estimou com os alvos sintéticos de treino "
            "de 2020–2023 e gravou no booster. Ele é anterior aos ajustes das árvores."
        )
        st.markdown(
            f"**2. Pessoas e calibração: {number(trace['people'])} pessoas fictícias.** "
            f"{number(trace['zeroed'])} tiveram previsão bruta não positiva. "
            f"Para as {number(trace['positive'])} restantes, somamos os fatores "
            f"das respectivas funções, chegando a **{number(trace['factor_sum'], 6)}**. "
            "É uma soma de multiplicadores, não uma contagem de pessoas."
        )
        st.markdown(
            f"**3. Conta da base: {number(trace['base_score'], 6)} × "
            f"{number(trace['factor_sum'], 6)} ≈ {number(trace['base_hours'], 2)} h.** "
            "A mesma calibração multiplica os ajustes das folhas. Por isso a base "
            "e as árvores podem ser somadas diretamente."
        )
        st.caption(
            "A implementação soma as folhas realmente alcançadas; pequenas diferenças "
            "entre a multiplicação exibida e a base decorrem da precisão numérica."
        )
        st.dataframe(
            trace["factors"].rename(
                columns={
                    "funcao": "Função fictícia",
                    "pessoas": "Pessoas",
                    "fator": "Fator de calibração",
                    "positivas": "Previsões positivas",
                    "soma_fatores": "Soma efetiva dos fatores",
                }
            ),
            hide_index=True,
            width="stretch",
        )
    st.caption(
        f"Diferença da reconstrução para o valor salvo: "
        f"{number(trace['total_hours'] - saved, 6)} h."
    )
    st.markdown("#### Quais informações mais elevaram ou reduziram este valor?")
    features = trace["contributions"].copy()
    features["informacao"] = features.variavel.map(LABELS).fillna(features.variavel)
    st.altair_chart(
        effect_chart(features.loc[features.variavel.ne("Base SHAP")], "informacao"), width="stretch"
    )
    st.caption(
        "Contribuições SHAP: verde eleva e laranja reduz frente à referência do modelo. "
        "São efeitos da previsão, não causas comprovadas nem horas efetivamente realizadas. "
        "A Base SHAP é uma referência de atribuição diferente do intercepto inicial."
    )
    with st.expander("Ver todas as contribuições das variáveis"):
        st.dataframe(features[["informacao", "efeito_horas"]], hide_index=True, width="stretch")
        st.caption(f"Base SHAP + efeitos = {number(features.efeito_horas.sum(), 3)} h.")
    st.markdown("#### Efeito de cada uma das árvores")
    st.altair_chart(effect_chart(trace["trees"], "arvore"), width="stretch")
    st.caption(
        "As 18 árvores com maior efeito absoluto estão em destaque. "
        "Todas as árvores participam da soma e estão disponíveis no arquivo de auditoria."
    )
    ids = trace["trees"].arvore.tolist()
    default = int(trace["trees"].loc[trace["trees"].efeito_horas.abs().idxmax(), "arvore"])
    chosen = st.selectbox(
        "Veja quais rotas as pessoas percorreram em uma árvore",
        ids,
        index=ids.index(default),
        key="trace_tree_id",
    )
    st.graphviz_chart(tree_diagram(trace["nodes"], chosen), width="stretch")
    st.dataframe(
        trace["routes"]
        .loc[trace["routes"].arvore.eq(chosen)]
        .rename(
            columns={
                "condicoes": "Perguntas e respostas até a folha",
                "pessoas": "Pessoas que chegaram",
                "previsoes_positivas": "Previsões positivas",
                "correcao_por_pessoa_h": "Correção por pessoa (h)",
                "efeito_horas": "Efeito agregado (h)",
            }
        )
        .drop(columns="arvore"),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Cada linha é uma folha. O efeito soma o ajuste para quem chegou nela, "
        "com calibração por função. Nenhum identificador pessoal é exportado."
    )
    st.download_button(
        "Baixar auditoria completa deste ciclo (ZIP)",
        audit_package(trace, load_model(signature), cycle),
        file_name=f"auditoria_sintetica_{cycle}.zip",
        mime="application/zip",
    )


def render_trees(meta, tables, signature):
    count = meta["tree_count"]
    st.subheader("Como as árvores constroem a previsão")
    st.markdown(
        f"A estimativa começa em um valor-base. Para cada pessoa fictícia, as "
        f"**{number(count)} árvores** fazem perguntas sobre o histórico e o perfil. "
        "Cada caminho termina em uma folha com um ajuste em horas. Depois, o "
        "sistema zera resultados negativos, calibra por função e soma as pessoas."
    )
    with st.container(border=True):
        st.markdown(
            "**Como ler esta tela**\n\n"
            "1. Escolha um ciclo e reconstrua o cálculo para ver a soma das árvores.\n"
            "2. Abra uma árvore para visualizar suas perguntas e as folhas alcançadas.\n"
            "3. Consulte o catálogo para ler e baixar todas as regras."
        )
        st.caption(
            "As árvores são ajustes combinados; não formam uma votação. "
            "As regras desta página foram aprendidas somente com a simulação pública."
        )
    st.markdown("#### Reconstruir uma previsão")
    forecast = tables["forecast"]
    cycle = st.selectbox("Ciclo previsto", forecast.ciclo.tolist(), key="tree_audit_cycle")
    saved = float(forecast.loc[forecast.ciclo.eq(cycle), "horas_previstas"].iloc[0])
    st.caption(
        f"O painel prevê **{number(saved)} h** para {cycle}. "
        "A auditoria recupera as folhas percorridas e confere a soma."
    )
    audit_key = (signature, cycle)
    if st.button("Reconstruir este cálculo", type="primary", key="run_tree_audit"):
        with st.spinner("Rastreando árvores e contribuições no ciclo sintético..."):
            st.session_state["active_audit"] = audit_key
    if st.session_state.get("active_audit") == audit_key:
        render_trace(load_audit(signature, cycle), saved, cycle, signature)
    with st.expander(f"Abrir o catálogo visual das {number(count)} árvores"):
        if st.button("Carregar as regras das árvores", key="load_tree_catalog"):
            st.session_state["catalog_loaded"] = signature
        if st.session_state.get("catalog_loaded") == signature:
            catalog, leaves, nodes = load_catalog(signature)
            st.info(
                f"O booster sintético contém {number(count)} árvores, todas ativas. "
                "Essa quantidade foi fixada para reproduzir a experiência do projeto; "
                "não foi selecionada como a melhor configuração para a simulação."
            )
            st.dataframe(
                catalog[["arvore", "perguntas"]].rename(
                    columns={"arvore": "Árvore", "perguntas": "Perguntas"}
                ),
                hide_index=True,
                height=320,
                width="stretch",
            )
            left, right = st.columns(2)
            with left:
                csv_download(
                    "Baixar inventário das árvores (CSV)",
                    catalog,
                    "inventario_arvores_sinteticas.csv",
                )
            with right:
                csv_download(
                    "Baixar regras e folhas de todas (CSV)", leaves, "regras_folhas_sinteticas.csv"
                )
            chosen = st.selectbox(
                "Inspecione uma árvore", catalog.arvore.tolist(), key="inspect_tree_id"
            )
            st.graphviz_chart(tree_diagram(nodes, chosen), width="stretch")
            st.dataframe(
                leaves.loc[leaves.arvore.eq(chosen)].drop(columns="arvore"),
                hide_index=True,
                width="stretch",
            )
            st.download_button(
                "Baixar estrutura completa das árvores ativas (JSON compactado)",
                tree_dump(load_model(signature)),
                file_name="arvores_sinteticas.json.gz",
                mime="application/gzip",
            )
        else:
            st.info("Carregue o catálogo para consultar todas as perguntas e folhas do modelo.")
