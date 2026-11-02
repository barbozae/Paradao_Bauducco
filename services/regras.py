"""Regras de negócio: status, validação das edições e filtros."""

import re
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

CONCLUIDA = "Concluída"
ATRASADA = "Atrasada"
EM_ANDAMENTO = "Em andamento"
NAO_INICIADA = "Não iniciada"

TODAS = "Todas"
SIM = "Sim"
NAO = "Não"

# Separa responsáveis conjuntos, como "RONALDO / VALMIR".
SEPARADOR_RESPONSAVEIS = re.compile(r"\s*/\s*")


@dataclass
class Criterios:
    """Seleção feita na barra lateral. Lista vazia significa "todos"."""

    linhas: list[str] = field(default_factory=list)
    responsaveis: list[str] = field(default_factory=list)
    periodo: tuple[date, date] | None = None
    concluidas: str = TODAS
    atrasadas: str = TODAS


def calcular_status(df: pd.DataFrame, data_hoje: date) -> pd.Series:
    """Calcula o status; a primeira condição verdadeira vence."""
    referencia = pd.Timestamp(data_hoje)
    condicoes = [
        df["progresso"] >= 100,
        df["termino"] < referencia,
        (df["progresso"] > 0) | df["inicio_real"].notna(),
    ]
    status = np.select(condicoes, [CONCLUIDA, ATRASADA, EM_ANDAMENTO], default=NAO_INICIADA)
    return pd.Series(status, index=df.index)


def validar_edicoes(df: pd.DataFrame) -> list[str]:
    """Devolve uma mensagem para cada problema (lista vazia = tudo certo)."""
    progresso = pd.to_numeric(df["progresso"], errors="coerce")
    inicio_real = pd.to_datetime(df["inicio_real"])
    fim_real = pd.to_datetime(df["fim_real"])

    erros = []
    for posicao in range(len(df)):
        atividade = f"{df['linha'].iloc[posicao]} · {df['tarefa'].iloc[posicao]}"
        if pd.isna(progresso.iloc[posicao]):
            erros.append(f"{atividade}: informe o % Realizado.")
        elif not 0 <= progresso.iloc[posicao] <= 100:
            erros.append(f"{atividade}: o % Realizado deve ficar entre 0 e 100.")
        if fim_real.iloc[posicao] < inicio_real.iloc[posicao]:
            erros.append(f"{atividade}: o Fim Real não pode ser anterior ao Início Real.")
    return erros


def identificar_alteracoes(original: pd.DataFrame, editado: pd.DataFrame) -> list[dict]:
    """Compara as duas versões pelo id e devolve só as linhas que mudaram."""
    antes = original.set_index("id")
    depois = editado.set_index("id").reindex(antes.index)

    progresso_depois = pd.to_numeric(depois["progresso"])
    inicio_depois = pd.to_datetime(depois["inicio_real"])
    fim_depois = pd.to_datetime(depois["fim_real"])

    def mudou(serie_antes: pd.Series, serie_depois: pd.Series) -> pd.Series:
        # Dois vazios são iguais, embora NaT == NaT seja falso no pandas.
        iguais = (serie_antes == serie_depois) | (serie_antes.isna() & serie_depois.isna())
        return ~iguais

    alteradas = (
        mudou(pd.to_numeric(antes["progresso"]), progresso_depois)
        | mudou(pd.to_datetime(antes["inicio_real"]), inicio_depois)
        | mudou(pd.to_datetime(antes["fim_real"]), fim_depois)
    )

    def como_data(valor: pd.Timestamp) -> date | None:
        return None if pd.isna(valor) else valor.date()

    return [
        {
            "id": int(id_atividade),
            "progresso": float(progresso_depois[id_atividade]),
            "inicio_real": como_data(inicio_depois[id_atividade]),
            "fim_real": como_data(fim_depois[id_atividade]),
        }
        for id_atividade in antes.index[alteradas]
    ]


def separar_responsaveis(valor: object) -> list[str]:
    """Quebra um responsável conjunto nos nomes individuais."""
    if pd.isna(valor):
        return []
    return [nome for nome in SEPARADOR_RESPONSAVEIS.split(str(valor).strip()) if nome]


def listar_responsaveis(df: pd.DataFrame) -> list[str]:
    """Nomes individuais para o filtro, sem repetição.

    "VALMIR" e "Valmir" são a mesma pessoa; fica a grafia mais frequente.
    """
    nomes: dict[str, str] = {}
    for valor in df["responsavel"].value_counts().index:
        for nome in separar_responsaveis(valor):
            nomes.setdefault(nome.casefold(), nome)
    return sorted(nomes.values(), key=str.casefold)


def _filtro_sim_nao(condicao: pd.Series, escolha: str) -> pd.Series:
    """Aplica uma opção Sim / Não / Todas sobre uma condição."""
    if escolha == SIM:
        return condicao
    if escolha == NAO:
        return ~condicao
    return pd.Series(True, index=condicao.index)


def aplicar_filtros(df: pd.DataFrame, criterios: Criterios) -> pd.DataFrame:
    """Aplica todos os filtros juntos sobre o DataFrame que já tem a coluna status."""
    mascara = pd.Series(True, index=df.index)

    if criterios.linhas:
        mascara &= df["linha"].isin(criterios.linhas)

    if criterios.responsaveis:
        selecionados = {nome.casefold() for nome in criterios.responsaveis}
        mascara &= df["responsavel"].map(
            lambda valor: any(nome.casefold() in selecionados for nome in separar_responsaveis(valor))
        )

    if criterios.periodo:
        # A atividade entra se o período planejado dela cruza o intervalo escolhido.
        inicio, fim = (pd.Timestamp(data) for data in criterios.periodo)
        mascara &= (df["inicio"] <= fim) & (df["termino"] >= inicio)

    mascara &= _filtro_sim_nao(df["status"] == CONCLUIDA, criterios.concluidas)
    mascara &= _filtro_sim_nao(df["status"] == ATRASADA, criterios.atrasadas)

    return df[mascara]
