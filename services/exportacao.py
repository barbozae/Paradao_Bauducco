"""Exportação dos dados atuais para Excel."""

from io import BytesIO

import pandas as pd

# Cabeçalhos originais da planilha, mais os campos preenchidos no dashboard.
COLUNAS_EXCEL = {
    "linha": "LINHA",
    "tarefa": "TAREFA",
    "ordem_de_trabalho": "ORDEM DE TRABALHO",
    "progresso": "PROGRESSO",
    "inicio": "INÍCIO",
    "termino": "TÉRMINO",
    "responsavel": "RESPONSÁVEL",
    "inicio_real": "INÍCIO REAL",
    "fim_real": "FIM REAL",
    "peso": "PESO",
}


def gerar_excel(df: pd.DataFrame) -> bytes:
    """Gera o .xlsx em memória; a coluna PESO só sai se tiver algum valor."""
    colunas = {
        chave: nome
        for chave, nome in COLUNAS_EXCEL.items()
        if chave != "peso" or df["peso"].notna().any()
    }
    saida = df[list(colunas)].rename(columns=colunas)

    arquivo = BytesIO()
    with pd.ExcelWriter(arquivo, engine="openpyxl", datetime_format="DD/MM/YYYY") as escritor:
        saida.to_excel(escritor, sheet_name="Planilha1", index=False)
    return arquivo.getvalue()
