"""Configurações gerais: credenciais do banco e data de referência."""

import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

RAIZ = Path(__file__).parent

# O servidor na nuvem roda em UTC; o "hoje" do projeto é sempre o do Brasil.
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")

load_dotenv(RAIZ / ".env")


def obter_database_url() -> str:
    """Busca a URL do banco no ambiente/.env (local) ou em st.secrets (nuvem)."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    import streamlit as st

    # Só consulta st.secrets se o arquivo existir; senão o Streamlit exibe um erro próprio.
    if st.secrets.load_if_toml_exists():
        url = st.secrets.get("DATABASE_URL")

    if not url:
        raise RuntimeError("DATABASE_URL não configurada. Preencha o arquivo .env.")
    return url


def hoje() -> date:
    """Data atual no fuso do projeto."""
    return datetime.now(FUSO_HORARIO).date()
