# Da simulação à previsão

## 1. Pessoas e horas fictícias

O gerador usa a semente 20261020 e cria 180 pessoas fictícias, em três unidades
e três funções genéricas. Cada pessoa tem uma propensão aleatória para horas extras.
Os alvos combinam essa propensão, efeito da unidade e função, sazonalidade, horas
do ciclo anterior e ruído. Alguns registros são zerados aleatoriamente.
Nenhum parâmetro foi estimado a partir da base privada.

O tempo de casa é inventado. A separação das extras anteriores entre trabalho e
folga usa proporções fixas por função: 25%, 35% e 20% em folgas, respectivamente.
Ela demonstra o fluxo de variáveis do painel, sem alegar uma escala real ou um
registro diário. A contagem de dias úteis considera apenas segunda a sexta,
sem descontar feriados. Não usamos ausências, desligamentos ou dados demográficos.

## 2. Somente informações anteriores

Para prever um ciclo, as variáveis de horas são construídas com ciclos anteriores:
último ciclo, dois ciclos atrás, médias de três e seis ciclos, divisão por tipo de
dia e média anterior da unidade e função. Tempo de casa e calendário complementam
o exemplo. Unidade e função usam codificação binária (one-hot).

## 3. Treino e calibração

O XGBoost aprende com 2020–2023, com objetivo `reg:absoluteerror`, profundidade
máxima 3, taxa de aprendizado 0,025 e 1.229 rodadas. A quantidade de árvores é
fixada para reproduzir a experiência visual do projeto original; não resulta
de uma busca de hiperparâmetros na simulação. Todas as árvores salvas são usadas.

O ano de 2024 é usado somente para calcular fatores de calibração. Primeiro,
previsões brutas negativas são zeradas. Para cada função, calculamos:

```text
razão da função = soma do realizado em 2024 / soma da previsão bruta positiva em 2024
razão global = soma do realizado de todos / soma da previsão bruta positiva de todos
fator = limitar(0,60 × razão da função + 0,40 × razão global, 0,75, 1,35)
```

O fator fica congelado durante o teste e as projeções.

## 4. Uma previsão individual

```text
bruta da pessoa = intercepto + soma das folhas alcançadas em todas as árvores
previsão individual = máximo(bruta da pessoa, 0) × fator da função
total do ciclo = soma das previsões individuais
```

O intercepto é a estimativa inicial registrada no booster. Para erro absoluto,
o critério favorece uma referência mediana dos alvos; usamos o valor efetivamente
armazenado pelo XGBoost. Ele não é a média do mês previsto.

Exemplo apenas didático: intercepto 4 h, soma das folhas +1 h e fator 1,10
resultam em 5,5 h. A auditoria real usa todas as folhas do booster sintético.

## 5. Reconstrução e zeragem

Para cada pessoa com previsão bruta positiva, o intercepto e cada folha são
multiplicados pelo fator da função. Para quem teve previsão não positiva,
o fator efetivo é zero. Assim:

```text
base agregada ≈ intercepto × soma dos fatores efetivos
efeito da árvore = soma(folha alcançada × fator efetivo)
total = base agregada + soma dos efeitos das árvores
```

A base auditada é recuperada do resíduo entre a saída bruta e a soma das folhas,
minimizando diferenças de precisão numérica. A mesma regra de zeragem entra em
todas as parcelas. A tabela de fatores permite conferir como a soma foi obtida.
Uma folha negativa reduz a estimativa; não representa horas negativas realizadas.

## 6. Contribuições das informações

`pred_contribs=True` calcula as contribuições TreeSHAP. Multiplicamos cada parcela
pelo mesmo fator efetivo. A Base SHAP e as contribuições somam a previsão final.
A Base SHAP é uma referência de atribuição do ensemble, diferente do intercepto
usado antes das árvores; não se deve somar as duas decomposições entre si.
São explicações matemáticas da previsão e não evidências causais.

## 7. Avaliação e projeções

O teste cobre janeiro/2025 a setembro/2026, sem refazer o ajuste do modelo ou
dos fatores. Cada ciclo usa o histórico realizado anterior conhecido. Os
indicadores são calculados nos totais mensais, e não por pessoa.

As 12 projeções posteriores são recursivas: cada previsão individual calibrada
entra nos históricos do próximo ciclo. A coorte e os grupos permanecem fixos.
Não há realizado disponível para validar esses ciclos futuros. A precisão no
teste sintético não é evidência de precisão com dados reais.
