"""Gráfico de Curva S."""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

COR_PLANEJADO = "#2a78d6"
COR_REALIZADO = "#eb6834"
COR_HOJE = "#898781"


def _adicionar_serie(figura: go.Figure, curva: pd.DataFrame, coluna: str, nome: str, cor: str) -> None:
    pontos = curva.dropna(subset=[coluna])
    # Uma linha com um único ponto ficaria invisível sem marcador.
    figura.add_scatter(
        x=pontos["data"],
        y=pontos[coluna],
        name=nome,
        mode="lines" if len(pontos) > 1 else "markers",
        line={"color": cor, "width": 2},
        marker={"color": cor, "size": 8},
        hovertemplate="%{y:.1f}%",
    )


def _rotular_fim(figura: go.Figure, curva: pd.DataFrame, coluna: str, nome: str, deslocamento: int) -> None:
    """Escreve nome e valor no último ponto da série."""
    pontos = curva.dropna(subset=[coluna])
    if pontos.empty:
        return
    ultimo = pontos.iloc[-1]
    # Na borda direita o texto fica antes do ponto; no meio, depois dele, longe da linha.
    na_borda = ultimo["data"] == curva["data"].max()
    # Perto de 0% o rótulo fica acima da linha, para não cobrir as datas do eixo.
    if ultimo[coluna] < 8:
        deslocamento = abs(deslocamento)
    figura.add_annotation(
        x=ultimo["data"],
        y=ultimo[coluna],
        text=f"{nome} {ultimo[coluna]:.1f}%".replace(".", ","),
        showarrow=False,
        xanchor="right" if na_borda else "left",
        xshift=0 if na_borda else 6,
        yshift=deslocamento,
    )


def _marcar_hoje(figura: go.Figure, curva: pd.DataFrame, data_hoje: date) -> None:
    """Marca hoje com linha vertical ou, fora do período, com um aviso na borda."""
    referencia = pd.Timestamp(data_hoje)
    texto = data_hoje.strftime("%d/%m/%Y")

    if referencia < curva["data"].min():
        figura.add_annotation(
            x=0, xref="paper", y=1, yref="paper", yanchor="bottom", xanchor="left",
            text=f"◄ Hoje {texto} (antes do início)", showarrow=False,
        )
    elif referencia > curva["data"].max():
        figura.add_annotation(
            x=1, xref="paper", y=1, yref="paper", yanchor="bottom", xanchor="right",
            text=f"Hoje {texto} (após o fim) ►", showarrow=False,
        )
    else:
        # Forma e anotação separadas: add_vline falha com datas no plotly 5.22.
        figura.add_shape(
            type="line", x0=referencia, x1=referencia, y0=0, y1=1, yref="paper",
            line={"color": COR_HOJE, "width": 1},
        )
        figura.add_annotation(
            x=referencia, y=1, yref="paper", yanchor="bottom",
            text=f"Hoje {texto}", showarrow=False,
        )


def renderizar_grafico(curva: pd.DataFrame, data_hoje: date) -> None:
    """Desenha a Curva S e, abaixo, a tabela com os mesmos valores."""
    figura = go.Figure()
    _adicionar_serie(figura, curva, "planejado", "Planejado", COR_PLANEJADO)
    _adicionar_serie(figura, curva, "realizado", "Realizado", COR_REALIZADO)
    _rotular_fim(figura, curva, "planejado", "Planejado", 12)
    _rotular_fim(figura, curva, "realizado", "Realizado", -12)
    _marcar_hoje(figura, curva, data_hoje)

    figura.update_layout(
        separators=",.",
        hovermode="x unified",
        height=420,
        margin={"l": 10, "r": 10, "t": 36, "b": 10},
        legend={"orientation": "h", "y": -0.12, "x": 0},
    )
    figura.update_xaxes(tickformat="%d/%m", hoverformat="%d/%m/%Y", showgrid=False)
    figura.update_yaxes(range=[0, 105], ticksuffix="%", tick0=0, dtick=25)

    st.plotly_chart(figura, use_container_width=True)

    with st.expander("Ver valores da curva"):
        st.dataframe(
            curva,
            hide_index=True,
            use_container_width=True,
            column_config={
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "planejado": st.column_config.NumberColumn("Planejado acumulado", format="%.1f%%"),
                "realizado": st.column_config.NumberColumn("Realizado acumulado", format="%.1f%%"),
            },
        )
