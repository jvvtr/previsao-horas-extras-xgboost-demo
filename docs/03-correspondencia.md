# Correspondência com a aplicação original

Esta edição acompanha o painel final de três abas do projeto privado.

| Recurso | Edição pública |
|---|---|
| Visual clean, cartões e navegação | Mesmo estilo de apresentação e três abas equivalentes. |
| Histórico previsto × realizado | Gráfico temporal, MAPE, WAPE, MAE, maior desvio e tabela mensal. |
| Downloads da avaliação | CSV com valores calculados na simulação. |
| Próximos ciclos | Horizonte de 1–12 ciclos, gráfico e CSV, com histórico selecionável. |
| Ciclo de 16 a 15 | Mantido na apresentação e no calendário das variáveis. |
| Previsão por pessoa e soma calibrada | Mantida com coorte fictícia fixa e fatores por função. |
| 1.229 árvores | Booster novo com 1.229 árvores treinadas somente na simulação. |
| Trilha de cálculo | Base, fatores, folhas alcançadas, efeitos por árvore e reconciliação. |
| Explicação por variável | TreeSHAP com calibração e zeragem consistentes com a previsão. |
| Catálogo completo | Perguntas, regras, folhas, CSVs e JSON compactado. |
| Visualização da árvore | Diagrama de perguntas e folhas para qualquer árvore selecionada. |
| Auditoria por ciclo | ZIP com regras, rotas, contagens, efeitos, fatores e total. |
| Explicação técnica | Etapas, exemplos, fórmulas, dados, avaliação e limitações. |

## Diferenças necessárias para a divulgação

O modelo e os dados originais, seus resultados, categorias e histórico Git não
foram copiados. As variáveis da demonstração representam os mesmos conceitos,
com um conjunto menor e inteiramente fictício. O gerador produz diretamente
linhas pessoa-ciclo: não reproduz o processo privado de ingestão diária.

No projeto original, a seleção de árvores faz parte da avaliação do modelo.
Nesta edição, 1.229 é uma quantidade fixa de demonstração e todas as árvores
salvas entram no cálculo. Os indicadores públicos são próprios e não devem
ser usados para divulgar o desempenho do estudo privado.

Não reativamos análises operacionais de ausências e desligamentos que não fazem
parte do painel final de três abas. Não inventamos eventos para sugerir que
uma hora extra real foi justificada. A fidelidade buscada é a experiência de
uso e de auditoria da previsão, com uma fonte de dados própria para divulgação.
