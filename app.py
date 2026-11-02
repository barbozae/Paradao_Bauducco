"""Dashboard de acompanhamento das atividades do Paradão.

Execute com: streamlit run app.py
"""

import pandas as pd
import streamlit as st
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

import configuracao
from components.cards import renderizar_cards
from components.filtros import renderizar_filtros
from components.grafico import renderizar_grafico
from components.nova_atividade import renderizar_nova_atividade
from components.tabela import renderizar_tabela
from repositories.atividades_repository import (
    atualizar_progresso,
    criar_engine,
    excluir_atividades,
    inserir_atividades,
    ler_atividades,
)
from services.curva_s import calcular_indicadores, montar_curva
from services.exportacao import gerar_excel
from services.regras import aplicar_filtros, calcular_status

st.set_page_config(
    page_title="Paradão 2026",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def obter_engine() -> Engine:
    return criar_engine(configuracao.obter_database_url())


@st.cache_data(ttl=60, show_spinner="Carregando atividades...")
def carregar_atividades() -> pd.DataFrame:
    return ler_atividades(obter_engine())


def salvar_alteracoes(alteracoes: list[dict]) -> None:
    """Grava no banco e recarrega a página com os dados novos."""
    try:
        atualizar_progresso(obter_engine(), alteracoes)
    except SQLAlchemyError:
        st.error("Não foi possível salvar; nenhuma alteração foi gravada. Tente de novo.")
        return

    carregar_atividades.clear()
    st.session_state["versao_dados"] = st.session_state.get("versao_dados", 0) + 1
    st.session_state["mensagem_salvo"] = f"{len(alteracoes)} atividade(s) salva(s)."
    st.rerun()


def incluir_atividade(registro: dict) -> bool:
    """Grava uma nova atividade e informa se deu certo."""
    try:
        inserir_atividades(obter_engine(), [registro])
    except SQLAlchemyError:
        st.error("Não foi possível incluir a atividade; nada foi gravado. Tente de novo.")
        return False

    carregar_atividades.clear()
    return True


def excluir_selecionadas(ids: list[int]) -> None:
    """Apaga as atividades e recarrega a página com os dados novos."""
    try:
        excluidas = excluir_atividades(obter_engine(), ids)
    except SQLAlchemyError:
        st.error("Não foi possível excluir; nenhuma atividade foi apagada. Tente de novo.")
        return

    carregar_atividades.clear()
    st.session_state["versao_dados"] = st.session_state.get("versao_dados", 0) + 1
    st.session_state["mensagem_salvo"] = f"{excluidas} atividade(s) excluída(s)."
    st.rerun()


st.title("Acompanhamento do Paradão")

try:
    atividades = carregar_atividades()
except (RuntimeError, SQLAlchemyError):
    st.error(
        "Não foi possível ler o banco de dados. Confira a DATABASE_URL e se o "
        "script importar_base.py já foi executado."
    )
    st.stop()

if atividades.empty:
    st.warning("Ainda não há atividades. Execute o script importar_base.py.")
    st.stop()

data_hoje = configuracao.hoje()
atividades["status"] = calcular_status(atividades, data_hoje)

# Os mesmos dados filtrados alimentam cards, gráfico e tabela.
filtradas = aplicar_filtros(atividades, renderizar_filtros(atividades))

st.sidebar.divider()
st.sidebar.download_button(
    "Exportar Excel",
    data=gerar_excel(atividades),
    file_name="Paradao_atividades.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Baixa todas as atividades, sem considerar os filtros.",
)

mensagem = st.session_state.pop("mensagem_salvo", None)
if mensagem:
    st.success(mensagem)

# Fica antes do aviso de "nenhuma atividade" para continuar acessível com filtros vazios.
renderizar_nova_atividade(atividades, incluir_atividade)

if filtradas.empty:
    st.info("Nenhuma atividade atende aos filtros selecionados.")
    st.stop()

renderizar_cards(calcular_indicadores(filtradas, data_hoje))

st.subheader("Curva S")
renderizar_grafico(montar_curva(filtradas, data_hoje), data_hoje)

st.subheader("Atividades")
renderizar_tabela(
    filtradas,
    st.session_state.get("versao_dados", 0),
    salvar_alteracoes,
    excluir_selecionadas,
)
