"""Acesso ao banco de dados: única camada que conhece a tabela `atividades`."""

import pandas as pd
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    bindparam,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

# As 7 colunas da planilha, na mesma ordem, mais id e os campos de acompanhamento.
atividades = Table(
    "atividades",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("linha", Text, nullable=False),
    Column("tarefa", Text, nullable=False),
    Column("ordem_de_trabalho", Text),
    Column("progresso", Numeric(5, 2), nullable=False, server_default="0"),
    Column("inicio", Date, nullable=False),
    Column("termino", Date, nullable=False),
    Column("responsavel", Text),
    Column("inicio_real", Date),
    Column("fim_real", Date),
    Column("peso", Numeric),
    Column("atualizado_em", DateTime(timezone=True), server_default=func.now()),
    CheckConstraint("progresso BETWEEN 0 AND 100", name="ck_progresso_faixa"),
    CheckConstraint("termino >= inicio", name="ck_datas_planejadas"),
    CheckConstraint("fim_real >= inicio_real", name="ck_datas_reais"),
)


def criar_engine(url: str) -> Engine:
    """Cria a conexão; o Neon suspende conexões ociosas, daí o pre_ping e o recycle."""
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


def criar_tabela(engine: Engine) -> None:
    """Cria a tabela se ela ainda não existir."""
    metadata.create_all(engine)


def contar_atividades(engine: Engine) -> int:
    with engine.connect() as conexao:
        return conexao.execute(select(func.count()).select_from(atividades)).scalar_one()


def ler_atividades(engine: Engine) -> pd.DataFrame:
    """Lê todas as atividades, com datas em datetime64 e números em float."""
    consulta = select(atividades).order_by(atividades.c.id)
    with engine.connect() as conexao:
        df = pd.read_sql(consulta, conexao)

    for coluna in ("inicio", "termino", "inicio_real", "fim_real"):
        df[coluna] = pd.to_datetime(df[coluna])
    for coluna in ("progresso", "peso"):
        df[coluna] = pd.to_numeric(df[coluna]).astype(float)
    return df


def inserir_atividades(engine: Engine, registros: list[dict], substituir: bool = False) -> None:
    """Grava a carga inicial; apagar e inserir ficam na mesma transação."""
    with engine.begin() as conexao:
        if substituir:
            conexao.execute(delete(atividades))
        conexao.execute(insert(atividades), registros)


def atualizar_progresso(engine: Engine, alteracoes: list[dict]) -> None:
    """Grava as linhas alteradas em uma transação: ou salva todas, ou nenhuma."""
    comando = (
        update(atividades)
        .where(atividades.c.id == bindparam("b_id"))
        .values(
            progresso=bindparam("b_progresso"),
            inicio_real=bindparam("b_inicio_real"),
            fim_real=bindparam("b_fim_real"),
            atualizado_em=func.now(),
        )
    )
    parametros = [
        {
            "b_id": item["id"],
            "b_progresso": item["progresso"],
            "b_inicio_real": item["inicio_real"],
            "b_fim_real": item["fim_real"],
        }
        for item in alteracoes
    ]
    with engine.begin() as conexao:
        conexao.execute(comando, parametros)
