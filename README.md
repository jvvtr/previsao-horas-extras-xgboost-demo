# Previsão de horas extras · demonstração pública

Aplicação Streamlit que demonstra previsão mensal e explicabilidade de árvores com
**dados e modelo inteiramente sintéticos**. Esta é uma implementação independente
para divulgação técnica. O projeto original, seu histórico Git, seus dados de RH,
seu booster e seus resultados detalhados continuam em um repositório privado.

## O que a demonstração mostra

- Comparação de horas previstas e realizadas em ciclos sintéticos fora do treino.
- Previsão do próximo ciclo fictício e métricas calculadas somente na simulação.
- Reconciliação do valor-base, fatores por função e efeitos de todas as árvores.
- Perguntas e folhas de uma árvore selecionada.
- Diagramas de qualquer uma das 1.229 árvores sintéticas e rotas percorridas.
- Contribuições SHAP, auditoria completa em ZIP e catálogo em CSV/JSON.
- Projeções recursivas de até 12 ciclos e downloads da avaliação mensal.
- Separação temporal entre treino (2020–2023), calibração (2024) e teste (2025–set/2026).

Os indicadores desta página **não são os indicadores do modelo privado**. A
simulação serve para mostrar a estrutura do método e pode ser reproduzida por
qualquer pessoa com o código deste repositório.

## Executar

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app.py
```

Os comandos acima são para Windows. Em Linux/macOS, use `.venv/bin/python`.
Os artefatos necessários já estão em `artifacts/`; o app não treina ao abrir.

Para refazer o treinamento com a mesma semente sintética:

```bash
python scripts/build_demo.py
```

Para verificar a implementação:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check app.py demo_pipeline.py tree_audit.py dashboard scripts tests
```

## Como os dados foram criados

`demo_pipeline.py` atribui aleatoriamente pessoas fictícias a três unidades e
três funções genéricas. Horas são simuladas com sazonalidade, efeito de unidade,
função, comportamento individual e ruído. A semente `20261020` torna os
resultados reproduzíveis. Nenhum arquivo do projeto privado é lido pelo gerador.

O treino usa apenas ciclos anteriores à calibração e ao teste. A calibração
aprende fatores por função com o ano de 2024. O teste usa o realizado do ciclo
anterior como histórico: mede uma previsão de um ciclo à frente, não valida
automaticamente uma projeção recursiva longa.

A quantidade de 1.229 árvores é fixa para reproduzir a experiência do painel
original; não foi selecionada como a melhor quantidade para a simulação.
O calendário representa ciclos do dia 16 ao dia 15. A coorte permanece fixa.

## Documentação

Leia o [guia de documentação](docs/README.md) para entender o painel, o modelo,
a correspondência com o projeto privado e os controles de qualidade.

## Publicação

O ponto de entrada para Streamlit Community Cloud é `app.py`. Não há
credenciais nem variáveis de ambiente obrigatórias. Antes de adicionar prints
do estudo privado, confira o [guia de publicação](PUBLICACAO.md).

Este repositório tem histórico Git próprio. Nunca faça merge do histórico do
repositório privado para esta demonstração.
