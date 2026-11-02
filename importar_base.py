"""Carga inicial: copia a aba Planilha1 do Base.xlsx para a tabela do Neon.

Uso:
    python importar_base.py               carrega em uma tabela vazia
    python importar_base.py --substituir  apaga tudo e recarrega (pede confirmação)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from configuracao import RAIZ, obter_database_url
from repositories.atividades_repository import (
    contar_atividades,
    criar_engine,
    criar_tabela,
    inserir_atividades,
)
from services.exportacao import COLUNAS_EXCEL

ABA = "Planilha1"
OBRIGATORIAS = ["LINHA", "TAREFA", "ORDEM DE TRABALHO", "PROGRESSO", "INÍCIO", "TÉRMINO", "RESPONSÁVEL"]
COLUNAS_DATA = ["inicio", "termino", "inicio_real", "fim_real"]


def unificar_grafias(serie: pd.Series) -> pd.Series:
    """Tira espaços das pontas e adota a grafia mais frequente de cada nome."""
    limpa = serie.str.strip()
    chaves = limpa.str.casefold()
    preferidas = limpa.groupby(chaves).agg(lambda grupo: grupo.value_counts().index[0])
    return chaves.map(preferidas)


def ler_planilha(caminho: Path) -> pd.DataFrame:
    """Lê a aba, confere a estrutura e devolve as colunas com os nomes do banco."""
    df = pd.read_excel(caminho, sheet_name=ABA, engine="openpyxl", dtype={"ORDEM DE TRABALHO": str})
    df.columns = [str(coluna).strip() for coluna in df.columns]

    faltando = [coluna for coluna in OBRIGATORIAS if coluna not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes na aba {ABA}: {', '.join(faltando)}")

    # INÍCIO REAL e FIM REAL são opcionais: existem no Excel exportado pelo app.
    nomes_banco = {nome: chave for chave, nome in COLUNAS_EXCEL.items() if nome in df.columns}
    df = df[list(nomes_banco)].rename(columns=nomes_banco)

    df["tarefa"] = df["tarefa"].str.strip()
    df["linha"] = unificar_grafias(df["linha"])
    df["responsavel"] = unificar_grafias(df["responsavel"])
    for coluna in COLUNAS_DATA:
        if coluna in df:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce").dt.date
    return df


def validar_planilha(df: pd.DataFrame) -> list[str]:
    """Aponta linhas que seriam recusadas pelo banco, usando a numeração do Excel."""
    erros = []
    for numero, linha in enumerate(df.itertuples(index=False), start=2):
        if pd.isna(linha.linha) or pd.isna(linha.tarefa):
            erros.append(f"Linha {numero}: LINHA e TAREFA são obrigatórias.")
        if pd.isna(linha.inicio) or pd.isna(linha.termino):
            erros.append(f"Linha {numero}: INÍCIO e TÉRMINO são obrigatórios.")
        elif linha.termino < linha.inicio:
            erros.append(f"Linha {numero}: TÉRMINO anterior ao INÍCIO.")
        if pd.isna(linha.progresso) or not 0 <= linha.progresso <= 100:
            erros.append(f"Linha {numero}: PROGRESSO deve ficar entre 0 e 100.")
    return erros


def como_registros(df: pd.DataFrame) -> list[dict]:
    """Converte o DataFrame em dicionários, trocando vazios por None."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa o Base.xlsx para o banco.")
    parser.add_argument("--arquivo", type=Path, default=RAIZ / "Base.xlsx")
    parser.add_argument("--substituir", action="store_true", help="apaga os dados atuais e recarrega")
    args = parser.parse_args()

    df = ler_planilha(args.arquivo)
    erros = validar_planilha(df)
    if erros:
        print("Importação cancelada:", *erros, sep="\n  ")
        return 1

    engine = criar_engine(obter_database_url())
    criar_tabela(engine)

    existentes = contar_atividades(engine)
    if existentes and not args.substituir:
        print(f"A tabela já tem {existentes} atividades; nada foi alterado.")
        print("Use --substituir para apagar tudo e recarregar. O progresso lançado será perdido.")
        return 1

    if existentes:
        print(f"Isso apaga {existentes} atividades, incluindo o progresso lançado.")
        if input("Digite SUBSTITUIR para confirmar: ").strip() != "SUBSTITUIR":
            print("Cancelado; nada foi alterado.")
            return 1

    inserir_atividades(engine, como_registros(df), substituir=args.substituir)
    print(f"{len(df)} atividades importadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
