# Limites da versão pública

Esta aplicação publica apenas uma **simulação sintética**. Os números do app
são fictícios; não devem ser apresentados como validação do modelo privado.

Os arquivos em `artifacts/` são regenerados integralmente por
`python scripts/build_demo.py`:

| Arquivo | Conteúdo |
|---|---|
| `demo_model.json` | Booster treinado somente com a simulação. |
| `metadata.json` | Períodos, fatores e métricas da simulação. |
| `monthly.csv` | Totais mensais sintéticos. |
| `future_features.csv` | Variáveis fictícias sem identificador pessoal. |
| `projection_features.csv` | Variáveis de cada um dos 12 ciclos projetados. |
| `forecast.csv` | Projeções recursivas sintéticas e seus períodos. |
| `history.csv` | Totais de todo o histórico sintético. |

Para compartilhar prints do painel privado separadamente, revise antes de
publicar: nomes de empresas/unidades, códigos de pessoas, funções raras,
datas específicas, totais reais, downloads e metadados da tela. Um print
aprovado não deve ser usado para substituir ou inserir artefatos reais neste
repositório.

O repositório original permanece privado. Não copie dele CSVs, Parquets,
booster, métricas, histórico Git, objetos LFS, screenshots ou arquivos de
cache para cá. Uma revisão deve incluir também os arquivos ignorados antes
de qualquer publicação ou implantação.
