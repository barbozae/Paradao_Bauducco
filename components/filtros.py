"""Filtros da barra lateral."""

import pandas as pd
import streamlit as st

from services.regras import NAO, SIM, TODAS, Criterios, listar_responsaveis

OPCOES_SIM_NAO = [TODAS, SIM, NAO]


def renderizar_filtros(df: pd.DataFrame) -> Criterios:
    """Desenha os filtros e devolve a seleção atual."""
    st.sidebar.header("Filtros")

    menor_data = df["inicio"].min().date()
    maior_data = df["termino"].max().date()
    selecao_datas = st.sidebar.date_input(
        "Data",
        value=(menor_data, maior_data),
        min_value=menor_data,
        max_value=maior_data,
        format="DD/MM/YYYY",
        help="Mostra as atividades cujo período planejado cruza este intervalo.",
    )
    
    linhas = st.sidebar.multiselect("Linha", sorted(df["linha"].unique()), placeholder="Todas")
    
    # Enquanto o usuário escolhe o fim do intervalo, só existe uma data selecionada.
    periodo = None
    if len(selecao_datas) == 2:
        periodo = (selecao_datas[0], selecao_datas[1])
    elif len(selecao_datas) == 1:
        periodo = (selecao_datas[0], selecao_datas[0])

    responsaveis = st.sidebar.multiselect("Responsável", listar_responsaveis(df), placeholder="Todos")
    concluidas = st.sidebar.radio("Atividades concluídas", OPCOES_SIM_NAO, horizontal=True)
    atrasadas = st.sidebar.radio("Atividades atrasadas", OPCOES_SIM_NAO, horizontal=True)

    return Criterios(linhas, responsaveis, periodo, concluidas, atrasadas)
