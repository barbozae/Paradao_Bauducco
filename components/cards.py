"""Cards de indicadores do topo da página."""

import streamlit as st


def _percentual(valor: float) -> str:
    return f"{valor:.1f}%".replace(".", ",")


def _desvio(valor: float) -> str:
    return f"{valor:+.1f}".replace(".", ",") + " p.p."


def renderizar_cards(indicadores: dict) -> None:
    """Mostra os seis indicadores em uma linha."""
    desvio = round(indicadores["desvio"], 1) + 0.0  # Somar 0.0 elimina o "-0,0".

    colunas = st.columns(6)
    colunas[0].metric("% Realizado", _percentual(indicadores["realizado"]))
    colunas[1].metric("% Planejado até hoje", _percentual(indicadores["planejado"]))
    colunas[2].metric("Desvio", _desvio(desvio), help="Realizado menos Planejado.")
    colunas[3].metric("Atividades planejadas", indicadores["total"])
    colunas[4].metric("Concluídas", indicadores["concluidas"])
    colunas[5].metric("Atrasadas", indicadores["atrasadas"])
