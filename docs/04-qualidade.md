# Qualidade e publicação

A edição pública possui histórico Git próprio. O projeto privado é usado
somente como referência de funcionalidades e apresentação. O gerador não lê
arquivos externos, não acessa rede e não carrega artefatos privados.

## Verificações automatizadas

- Gerador determinístico e grupos fictícios conhecidos.
- Reconciliação entre base, todas as árvores, SHAP e previsão salva.
- Contagens das rotas e soma de efeitos por folha e por árvore.
- Projeção recursiva alimentando o próximo ciclo com as previsões calibradas.
- Conteúdo dos arquivos de auditoria e ausência de identificadores pessoais.
- Navegação das três abas e execução dos controles de auditoria e catálogo.
- Ruff para erros de código e organização dos imports.

As verificações são executadas localmente e pelo GitHub Actions. O painel
carrega snapshots; o treinamento fica no comando de preparação. Catálogo e
auditorias são calculados sob demanda e armazenados em cache por versão dos
artefatos. Uma troca de modelo ou dados invalida os resultados anteriores.

## Organização

`dashboard/` reúne apresentação e carregamento; `demo_pipeline.py` reúne
geração, treino e reconstrução; `tree_audit.py` reúne regras, diagramas e
exportação. `artifacts/` contém apenas saídas reproduzíveis do gerador.
`docs/` organiza a leitura; `tests/` verifica as invariantes numéricas e a UI.

Antes de cada publicação, revisar o diff e os arquivos rastreados, incluindo
documentos e downloads. Não adicionar dados reais, screenshots privados,
credenciais ou arquivos do booster original. O e-mail do autor dos commits
deste repositório usa o endereço público `noreply` do GitHub.

A execução do app é local; não foi contratado ou configurado serviço de hospedagem.
