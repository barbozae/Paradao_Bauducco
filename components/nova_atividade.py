"""Formulário para incluir novas atividades."""

from collections.abc import Callable

import pandas as pd
import streamlit as st

from services.regras import listar_responsaveis, padronizar_texto, validar_nova_atividade

SEM_RESPONSAVEL = "— Sem responsável —"
CHAVE_VERSAO = "versao_nova_atividade"


def renderizar_nova_atividade(df: pd.DataFrame, incluir: Callable[[dict], bool]) -> None:
    """Mostra o formulário; ao enviar, valida e grava pela função `incluir`."""
    linhas = sorted(df["linha"].unique())
    responsaveis = listar_responsaveis(df)

    # A chave muda depois de cada inclusão, o que devolve os campos ao estado inicial.
    # Com clear_on_submit os campos também seriam apagados quando houvesse erro.
    versao = st.session_state.get(CHAVE_VERSAO, 0)

    def chave(nome: str) -> str:
        return f"nova_{nome}_{versao}"

    with st.expander("Adicionar atividade"):
        st.caption("Salve antes as edições da tabela: incluir uma atividade descarta o que não foi salvo.")
        with st.form(chave("form"), border=False):
            col_linha, col_nova_linha = st.columns(2)
            linha_lista = col_linha.selectbox("Linha", linhas, key=chave("linha"))
            linha_nova = col_nova_linha.text_input(
                "Nova linha",
                key=chave("linha_nova"),
                help="Preencha só se a linha não estiver na lista ao lado.",
            )
            tarefa = st.text_input("Tarefa", key=chave("tarefa"))

            col_resp, col_novo_resp, col_ordem = st.columns(3)
            resp_lista = col_resp.selectbox(
                "Responsável", [SEM_RESPONSAVEL, *responsaveis], key=chave("resp")
            )
            resp_novo = col_novo_resp.text_input(
                "Novo responsável",
                key=chave("resp_novo"),
                help="Preencha só se o responsável não estiver na lista ao lado.",
            )
            ordem = col_ordem.text_input("Ordem de trabalho", key=chave("ordem"))

            col_inicio, col_fim = st.columns(2)
            # Datas começam vazias: Enter em um campo de texto envia o formulário, e
            # com datas padrão isso gravaria a atividade com datas erradas sem aviso.
            inicio = col_inicio.date_input(
                "Início planejado", value=None, format="DD/MM/YYYY", key=chave("inicio")
            )
            fim = col_fim.date_input(
                "Fim planejado", value=None, format="DD/MM/YYYY", key=chave("fim")
            )
            enviado = st.form_submit_button("Incluir atividade", type="primary")

    if not enviado:
        return

    linha = padronizar_texto(linha_nova or linha_lista, linhas)
    tarefa = padronizar_texto(tarefa)
    nome_resp = padronizar_texto(resp_novo, responsaveis) or (
        "" if resp_lista == SEM_RESPONSAVEL else resp_lista
    )

    erros = validar_nova_atividade(linha, tarefa, inicio, fim)
    if erros:
        st.error("Nada foi incluído. Corrija:\n" + "\n".join(f"- {erro}" for erro in erros))
        return

    registro = {
        "linha": linha,
        "tarefa": tarefa,
        "ordem_de_trabalho": padronizar_texto(ordem) or None,
        "inicio": inicio,
        "termino": fim,
        "responsavel": nome_resp or None,
    }
    if incluir(registro):
        st.session_state[CHAVE_VERSAO] = versao + 1
        st.session_state["mensagem_salvo"] = (
            f"Atividade incluída: {linha} · {tarefa}. "
            "Se ela não aparecer na tabela, confira os filtros da barra lateral."
        )
        st.rerun()
