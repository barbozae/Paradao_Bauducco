"""Cálculo da Curva S e dos indicadores do projeto."""

from datetime import date

import numpy as np
import pandas as pd

from services.regras import ATRASADA, CONCLUIDA


def _pesos(df: pd.DataFrame) -> np.ndarray:
    """Usa a coluna peso; sem peso informado, cada atividade vale 1."""
    if "peso" not in df:
        return np.ones(len(df))

    pesos = pd.to_numeric(df["peso"]).fillna(1.0).clip(lower=0).to_numpy(dtype=float)
    return pesos if pesos.sum() > 0 else np.ones(len(df))


def _em_dias(datas: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    """Converte datas em números de dias, para fazer contas de calendário."""
    return np.asarray(datas, dtype="datetime64[D]").astype(int)


def _avanco_linear(datas: np.ndarray, inicios: np.ndarray, fins: np.ndarray) -> np.ndarray:
    """Fração concluída (0 a 1) por data e atividade, ao fim de cada dia.

    Devolve uma matriz com uma linha por data e uma coluna por atividade.
    """
    decorridos = datas[:, None] - inicios + 1
    return np.clip(decorridos / (fins - inicios + 1), 0, 1)


def _datas_reais(df: pd.DataFrame, data_hoje: date) -> tuple[pd.Series, pd.Series]:
    """Define o período em que o realizado é distribuído.

    As datas informadas são sempre respeitadas, mesmo que futuras. Só a data
    faltante é preenchida: sem nenhuma data real, o avanço cai em hoje.
    """
    referencia = pd.Timestamp(data_hoje)
    inicios = df["inicio_real"].fillna(df["fim_real"]).fillna(referencia)
    fins = df["fim_real"].fillna(referencia)
    return inicios, fins.where(fins >= inicios, inicios)


def percentual_realizado(df: pd.DataFrame) -> float:
    """Média do % Realizado ponderada pelo peso."""
    return float(np.average(df["progresso"].to_numpy(dtype=float), weights=_pesos(df)))


def percentual_planejado(df: pd.DataFrame, data: date) -> float:
    """% que deveria estar pronto ao fim da data informada."""
    avanco = _avanco_linear(
        _em_dias(pd.DatetimeIndex([data])), _em_dias(df["inicio"]), _em_dias(df["termino"])
    )
    return float(np.average(avanco[0], weights=_pesos(df)) * 100)


def montar_curva(df: pd.DataFrame, data_hoje: date) -> pd.DataFrame:
    """Monta a série diária com Planejado e Realizado acumulados.

    O Realizado fica vazio depois de hoje ou da última data real informada,
    o que vier por último.
    """
    inicios_reais, fins_reais = _datas_reais(df, data_hoje)

    # O eixo cobre o planejado e também as atividades que já têm avanço real.
    com_avanco = df["progresso"] > 0
    primeira = pd.concat([df["inicio"], inicios_reais[com_avanco]]).min()
    ultima = pd.concat([df["termino"], fins_reais[com_avanco]]).max()
    datas = pd.date_range(primeira, ultima, freq="D")
    dias = _em_dias(datas)
    pesos = _pesos(df)

    planejado = _avanco_linear(dias, _em_dias(df["inicio"]), _em_dias(df["termino"]))
    realizado = _avanco_linear(dias, _em_dias(inicios_reais), _em_dias(fins_reais))
    realizado = realizado * df["progresso"].to_numpy(dtype=float)

    curva = pd.DataFrame(
        {
            "data": datas,
            "planejado": planejado @ pesos / pesos.sum() * 100,
            "realizado": realizado @ pesos / pesos.sum(),
        }
    )
    fim_realizado = pd.concat([pd.Series([pd.Timestamp(data_hoje)]), fins_reais[com_avanco]]).max()
    curva.loc[curva["data"] > fim_realizado, "realizado"] = np.nan
    return curva


def calcular_indicadores(df: pd.DataFrame, data_hoje: date) -> dict:
    """Calcula os números dos cards sobre as atividades filtradas."""
    realizado = percentual_realizado(df)
    planejado = percentual_planejado(df, data_hoje)
    return {
        "realizado": realizado,
        "planejado": planejado,
        "desvio": realizado - planejado,
        "total": len(df),
        "concluidas": int((df["status"] == CONCLUIDA).sum()),
        "atrasadas": int((df["status"] == ATRASADA).sum()),
    }
