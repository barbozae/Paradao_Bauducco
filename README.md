# Acompanhamento do Paradão

Dashboard em Streamlit para acompanhar as atividades do Paradão: cards de indicadores, Curva S, tabela editável e filtros. Os dados ficam em um banco PostgreSQL no Neon. O `Base.xlsx` é usado apenas na carga inicial.

## Instalação

Na pasta `app`, com Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha `DATABASE_URL` com a URL completa do Neon. O `.env` não vai para o Git.

## Carga inicial

```powershell
python importar_base.py
```

O comando cria a tabela `atividades` e copia a aba `Planilha1`. Se a tabela já tiver dados, ele não altera nada.

Para recarregar do zero, use `python importar_base.py --substituir`. O comando pede confirmação, porque **apaga todo o progresso lançado**. Para restaurar o progresso de um backup, use o arquivo gerado pelo botão Exportar Excel: `python importar_base.py --arquivo caminho.xlsx --substituir`.

## Execução

```powershell
streamlit run app.py
```

## Como funciona

- **Tabela:** edite % Realizado, Início Real e Fim Real e clique em **Salvar**. Confirme cada célula com Enter antes de clicar em Salvar; mudar os filtros antes de salvar descarta as edições.
- **Status:** Concluída (100%), Atrasada (fim planejado já passou e % abaixo de 100), Em andamento (% acima de 0 ou Início Real preenchido), Não iniciada.
- **Curva S:** cada atividade avança em linha reta, em dias corridos, entre as datas planejadas (Planejado) e entre as datas reais (Realizado). Sem data real, o avanço é lançado em hoje.
- **Peso:** a coluna `peso` da tabela pondera o avanço. Vazia, cada atividade vale 1.
- **Filtros:** valem ao mesmo tempo para cards, gráfico e tabela.
- **Exportar Excel:** baixa todas as atividades, sem considerar os filtros.
- Alterações feitas no `Base.xlsx` depois da carga não chegam ao dashboard.

## Testes

```powershell
pip install pytest
python -m pytest
```

## Publicação no Streamlit Cloud

1. Crie um repositório no GitHub com o conteúdo desta pasta. `.env` e `Base.xlsx` ficam de fora pelo `.gitignore`.
2. No Streamlit Cloud, crie o app apontando para `app.py`, com Python 3.12.
3. Em **Settings > Secrets**, cole a `DATABASE_URL` no formato de `.streamlit/secrets.toml.example`.
4. **O app não tem login: quem tiver o link pode editar os dados.** Em **Settings > Sharing**, deixe o app privado e libere apenas os e-mails autorizados.
