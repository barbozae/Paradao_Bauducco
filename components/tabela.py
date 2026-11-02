"""Tabela editável de progresso."""

import hashlib
from collections.abc import Callable

import pandas as pd
import streamlit as st

from services.regras import (
    ATRASADA,
    CONCLUIDA,
    EM_ANDAMENTO,
    NAO_INICIADA,
    identificar_alteracoes,
    validar_edicoes,
)

# O status nunca depende só de cor: cada um tem símbolo e texto.
ROTULOS_STATUS = {
    CONCLUIDA: "✓ Concluída",
    ATRASADA: "! Atrasada",
    EM_ANDAMENTO: "▶ Em andamento",
    NAO_INICIADA: "○ Não iniciada",
}

# As colunas editáveis vêm logo após a tarefa, para não exigir rolagem lateral.
COLUNAS_VISIVEIS = [
    "status_rotulo",
    "linha",
    "tarefa",
    "progresso",
    "inicio_real",
    "fim_real",
    "inicio",
    "termino",
    "responsavel",
    "ordem_de_trabalho",
]
COLUNAS_EDITAVEIS = {"progresso", "inicio_real", "fim_real"}
ERROS_EXIBIDOS = 10


def _chave_editor(df: pd.DataFrame, versao: int) -> str:
    """Gera uma chave própria para cada conjunto de linhas.

    O st.data_editor guarda as edições por posição. Sem isso, trocar o filtro
    aplicaria as edições pendentes nas linhas erradas.
    """
    ids = ",".join(df["id"].astype(str))
    return f"editor_{versao}_{hashlib.md5(ids.encode()).hexdigest()}"


def _mostrar_erros(erros: list[str]) -> None:
    excedente = len(erros) - ERROS_EXIBIDOS
    texto = "\n".join(f"- {erro}" for erro in erros[:ERROS_EXIBIDOS])
    if excedente > 0:
        texto += f"\n- e mais {excedente} erro(s)."
    st.error(f"Nada foi salvo. Corrija:\n{texto}")


def renderizar_tabela(df: pd.DataFrame, versao: int, salvar: Callable[[list[dict]], None]) -> None:
    """Mostra o editor e, ao clicar em Salvar, valida e grava as alterações."""
    original = df.assign(
        status_rotulo=df["status"].map(ROTULOS_STATUS),
        ordem_de_trabalho=df["ordem_de_trabalho"].fillna(""),
    )
    # O formulário segura as edições até o Salvar. Sem ele, cada célula alterada
    # recarrega a página inteira e atrapalha quem digita em sequência.
    # Não usar use_container_width aqui: no Streamlit 1.38, junto com st.form, ele
    # causa o erro React #185 (ciclo infinito de atualização) no navegador.
    with st.form("form_atividades", border=False):
        editado = st.data_editor(
            original,
            key=_chave_editor(df, versao),
            hide_index=True,
            num_rows="fixed",
            height=460,
            column_order=COLUNAS_VISIVEIS,
            disabled=[coluna for coluna in COLUNAS_VISIVEIS if coluna not in COLUNAS_EDITAVEIS],
            column_config={
                "status_rotulo": st.column_config.TextColumn("Status"),
                "linha": st.column_config.TextColumn("Linha"),
                "tarefa": st.column_config.TextColumn("Tarefa", width="medium"),
                "responsavel": st.column_config.TextColumn("Responsável"),
                "ordem_de_trabalho": st.column_config.TextColumn("Ordem de trabalho"),
                "inicio": st.column_config.DateColumn("Início planejado", format="DD/MM/YYYY"),
                "termino": st.column_config.DateColumn("Fim planejado", format="DD/MM/YYYY"),
                "progresso": st.column_config.NumberColumn(
                    "% Realizado", min_value=0, max_value=100, step=1, format="%d%%"
                ),
                "inicio_real": st.column_config.DateColumn("Início Real", format="DD/MM/YYYY"),
                "fim_real": st.column_config.DateColumn("Fim Real", format="DD/MM/YYYY"),
            },
        )
        st.caption(
            "Confirme cada célula com Enter e depois clique em Salvar. "
            "Mudar os filtros antes de salvar descarta as edições."
        )
        enviado = st.form_submit_button("Salvar", type="primary")

    if enviado:
        erros = validar_edicoes(editado)
        if erros:
            _mostrar_erros(erros)
            return

        alteracoes = identificar_alteracoes(original, editado)
        if alteracoes:
            salvar(alteracoes)
        else:
            # Célula ainda sem Enter só é confirmada depois do clique no Salvar.
            st.info(
                "Nenhuma alteração para salvar. Se você acabou de digitar um valor, "
                "confira se ele aparece na tabela e clique em Salvar de novo."
            )
