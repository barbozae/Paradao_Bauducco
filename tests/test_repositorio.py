"""Testes do repositório em um SQLite temporário."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from repositories.atividades_repository import (
    criar_engine,
    criar_tabela,
    excluir_atividades,
    inserir_atividades,
    ler_atividades,
)


@pytest.fixture
def engine(tmp_path):
    engine = criar_engine(f"sqlite:///{(tmp_path / 'teste.db').as_posix()}")
    criar_tabela(engine)
    return engine


def nova(**extra) -> dict:
    return {
        "linha": "SILOS", "tarefa": "LIMPEZA", "ordem_de_trabalho": None,
        "inicio": date(2026, 12, 22), "termino": date(2026, 12, 23),
        "responsavel": None, **extra,
    }


def test_nova_atividade_entra_zerada_e_com_id_proprio(engine):
    inserir_atividades(engine, [nova()])
    inserir_atividades(engine, [nova(tarefa="OUTRA", responsavel="Valmir")])

    df = ler_atividades(engine)
    assert df["id"].tolist() == [1, 2]
    assert df["progresso"].tolist() == [0.0, 0.0]
    assert df["inicio_real"].isna().all()
    assert df.loc[1, "responsavel"] == "Valmir"


def test_excluir_apaga_so_os_ids_informados(engine):
    inserir_atividades(engine, [nova(tarefa=nome) for nome in ("A", "B", "C")])

    assert excluir_atividades(engine, [1, 3]) == 2
    assert ler_atividades(engine)["tarefa"].tolist() == ["B"]
    assert excluir_atividades(engine, [99]) == 0


def test_banco_recusa_fim_antes_do_inicio(engine):
    with pytest.raises(IntegrityError):
        inserir_atividades(engine, [nova(termino=date(2026, 12, 21))])
    assert ler_atividades(engine).empty
