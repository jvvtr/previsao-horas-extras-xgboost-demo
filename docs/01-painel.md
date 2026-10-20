# Como ler o painel

## Previsão

O histórico compara totais realizados sintéticos com previsões de um ciclo à frente.
O ciclo operacional começa no dia 16 do mês anterior e termina no dia 15 do mês indicado.
Por exemplo, 2026-10 representa 16/09/2026 a 15/10/2026. O gerador cria exemplos
diretamente por ciclo: não há um CSV diário escondido por trás desta demonstração.

MAPE é a média do erro percentual absoluto; WAPE divide a soma dos erros absolutos
pela soma dos realizados; MAE é o erro absoluto médio em horas. Valores menores
indicam menor erro na simulação. Os resultados não medem desempenho em uma operação real.

A tabela mensal permite conferir os desvios com sinal e baixar os resultados.
A projeção permite selecionar de 1 a 12 ciclos e exibir 12, 24 ou 36 ciclos de histórico.
Do segundo ciclo futuro em diante, previsões anteriores substituem os realizados
nas variáveis históricas. O erro registrado no teste não valida esses horizontes longos.

## Explicabilidade das árvores

Escolha um ciclo e clique em **Reconstruir este cálculo**. A tela mostra:

- comparação entre o valor salvo e a recomputação;
- intercepto inicial, soma dos fatores por função, base agregada e soma das árvores;
- efeitos SHAP das informações e efeitos agregados por árvore;
- diagrama de uma árvore e rotas que as pessoas fictícias percorreram;
- quantidade de pessoas por folha, ajuste individual e efeito após calibração;
- pacote ZIP com tabelas, reconciliação e regras completas.

O catálogo pode ser carregado sem executar uma auditoria de ciclo. Ele permite
inspecionar qualquer uma das 1.229 árvores e baixar regras e folhas em CSV e JSON.
O diagrama mostra limites com oito algarismos significativos para facilitar leitura;
o JSON exportado mantém os valores serializados pelo XGBoost.

## Como funciona o XGBoost

A terceira aba explica etapas, variáveis, separação temporal, calibração e limites.
Os exemplos pequenos são didáticos. Os números do painel são calculados pelo booster
sintético, e não são digitados para imitar as métricas do projeto original.
