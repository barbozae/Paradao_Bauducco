"""Testes das regras de negócio e da Curva S."""

from datetime import date
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from services.curva_s import calcular_indicadores, montar_curva, percentual_planejado, percentual_realizado
from services.exportacao import gerar_excel
from services.regras import (
    ATRASADA,
    CONCLUIDA,
    EM_ANDAMENTO,
    NAO,
    NAO_INICIADA,
    SIM,
    Criterios,
    aplicar_filtros,
    calcular_status,
    identificar_alteracoes,
    listar_responsaveis,
    validar_edicoes,
)

HOJE = date(2026, 12, 25)


def atividades(*linhas: dict) -> pd.DataFrame:
    """Monta um DataFrame no formato devolvido pelo repositório."""
    padrao = {
        "linha": "A", "tarefa": "T", "responsavel": "Ana", "progresso": 0.0,
        "inicio": "2026-12-22", "termino": "2026-12-24",
        "inicio_real": None, "fim_real": None, "peso": None,
    }
    df = pd.DataFrame([{"id": i, **padrao, **linha} for i, linha in enumerate(linhas, start=1)])
    for coluna in ("inicio", "termino", "inicio_real", "fim_real"):
        df[coluna] = pd.to_datetime(df[coluna])
    df["peso"] = pd.to_numeric(df["peso"]).astype(float)
    df["progresso"] = df["progresso"].astype(float)
    df["status"] = calcular_status(df, HOJE)
    return df


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [
        ({"progresso": 100.0, "termino": "2026-12-01"}, CONCLUIDA),
        ({"progresso": 50.0, "termino": "2026-12-24"}, ATRASADA),
        ({"termino": "2026-12-24"}, ATRASADA),
        ({"progresso": 99.0, "termino": "2026-12-25"}, EM_ANDAMENTO),
        ({"inicio_real": "2026-12-24", "termino": "2026-12-30"}, EM_ANDAMENTO),
        ({"termino": "2026-12-25"}, NAO_INICIADA),
    ],
)
def test_status_nas_fronteiras(linha, esperado):
    assert atividades(linha)["status"].iloc[0] == esperado


def test_validacao_aponta_erros():
    df = atividades(
        {"progresso": 101.0},
        {"progresso": -1.0},
        {"progresso": np.nan},
        {"inicio_real": "2026-12-23", "fim_real": "2026-12-22"},
    )
    assert len(validar_edicoes(df)) == 4


def test_validacao_aceita_limites_e_datas_vazias():
    df = atividades(
        {"progresso": 0.0},
        {"progresso": 100.0, "inicio_real": "2026-12-23", "fim_real": "2026-12-23"},
        {"fim_real": "2026-12-23"},
    )
    assert validar_edicoes(df) == []


def test_alteracoes_traz_so_o_que_mudou():
    original = atividades({}, {}, {"inicio_real": "2026-12-22"})
    editado = original.copy()
    editado.loc[1, "progresso"] = 40.0
    editado.loc[2, "inicio_real"] = pd.NaT

    assert identificar_alteracoes(original, editado) == [
        {"id": 2, "progresso": 40.0, "inicio_real": None, "fim_real": None},
        {"id": 3, "progresso": 0.0, "inicio_real": None, "fim_real": None},
    ]


def test_filtros_combinados():
    df = atividades(
        {"linha": "A", "progresso": 100.0},
        {"linha": "A"},
        {"linha": "B", "inicio": "2026-12-30", "termino": "2026-12-31"},
    )
    assert aplicar_filtros(df, Criterios(linhas=["A"], concluidas=NAO))["id"].tolist() == [2]
    assert aplicar_filtros(df, Criterios(atrasadas=SIM))["id"].tolist() == [2]
    assert aplicar_filtros(df, Criterios(atrasadas=NAO))["id"].tolist() == [1, 3]


def test_filtro_de_data_usa_cruzamento_de_periodos():
    df = atividades({"inicio": "2026-12-22", "termino": "2026-12-24"})
    assert len(aplicar_filtros(df, Criterios(periodo=(date(2026, 12, 24), date(2026, 12, 30))))) == 1
    assert len(aplicar_filtros(df, Criterios(periodo=(date(2026, 12, 25), date(2026, 12, 30))))) == 0


def test_responsavel_conjunto_aparece_nos_dois_nomes():
    df = atividades(
        {"responsavel": "RONALDO / VALMIR"},
        {"responsavel": "Valmir"},
        {"responsavel": "Valmir"},
        {"responsavel": None},
    )
    assert listar_responsaveis(df) == ["RONALDO", "Valmir"]
    assert aplicar_filtros(df, Criterios(responsaveis=["RONALDO"]))["id"].tolist() == [1]
    assert aplicar_filtros(df, Criterios(responsaveis=["Valmir"]))["id"].tolist() == [1, 2, 3]


def test_planejado_sobe_linear_e_termina_em_100():
    df = atividades({"inicio": "2026-12-22", "termino": "2026-12-25"})
    assert percentual_planejado(df, date(2026, 12, 21)) == 0
    assert percentual_planejado(df, date(2026, 12, 22)) == pytest.approx(25)
    assert percentual_planejado(df, date(2026, 12, 25)) == 100
    assert montar_curva(df, HOJE)["planejado"].iloc[-1] == pytest.approx(100)


def test_sem_peso_todas_valem_igual():
    df = atividades({"progresso": 100.0}, {"progresso": 0.0})
    assert percentual_realizado(df) == 50


def test_peso_pondera_o_avanco():
    df = atividades({"progresso": 100.0, "peso": 3.0}, {"progresso": 0.0, "peso": 1.0})
    assert percentual_realizado(df) == 75


@pytest.mark.parametrize(
    "linhas",
    [
        [{"progresso": 40.0, "inicio_real": "2026-12-22", "fim_real": "2026-12-23"}, {"progresso": 100.0}],
        [{"progresso": 30.0, "fim_real": "2026-12-23"}, {"progresso": 10.0, "inicio_real": "2026-12-29"}],
        [{"progresso": 80.0, "inicio_real": "2026-12-20", "fim_real": "2027-01-10", "peso": 2.0}, {}],
    ],
)
def test_ultimo_ponto_do_realizado_coincide_com_o_card(linhas):
    df = atividades(*linhas)
    ponto = montar_curva(df, HOJE)["realizado"].dropna().iloc[-1]
    assert ponto == pytest.approx(calcular_indicadores(df, HOJE)["realizado"])


def test_datas_reais_futuras_sao_respeitadas():
    df = atividades(
        {"progresso": 100.0, "inicio_real": "2026-12-27", "fim_real": "2026-12-28"},
        {"progresso": 0.0},
    )
    curva = montar_curva(df, HOJE).set_index("data")["realizado"]
    assert curva[pd.Timestamp("2026-12-25")] == 0
    assert curva[pd.Timestamp("2026-12-27")] == pytest.approx(25)
    assert curva[pd.Timestamp("2026-12-28")] == pytest.approx(50)
    assert curva.last_valid_index() == pd.Timestamp("2026-12-28")


def test_realizado_para_em_hoje():
    curva = montar_curva(atividades({"termino": "2026-12-31"}), HOJE)
    assert curva["realizado"].last_valid_index() == curva.index[curva["data"] == pd.Timestamp(HOJE)][0]


def test_projeto_futuro_nao_tem_linha_realizada():
    df = atividades({"inicio": "2026-12-30", "termino": "2026-12-31"})
    assert montar_curva(df, HOJE)["realizado"].notna().sum() == 0


def test_excel_exportado_mantem_cabecalhos():
    df = atividades({"inicio_real": "2026-12-23"})
    df["ordem_de_trabalho"] = None
    lido = pd.read_excel(BytesIO(gerar_excel(df)), sheet_name="Planilha1")
    assert list(lido.columns) == [
        "LINHA", "TAREFA", "ORDEM DE TRABALHO", "PROGRESSO", "INÍCIO", "TÉRMINO",
        "RESPONSÁVEL", "INÍCIO REAL", "FIM REAL",
    ]
