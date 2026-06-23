"""
dashboards.py — Ponto de entrada único hospedando tanto o painel do
Corretor (público, padrão) quanto o Admin Dashboard (acesso discreto via
link no rodapé), dentro do mesmo serviço Streamlit — economia de recursos
no Railway durante a fase de validação do projeto.

Quando o negócio crescer e justificar, basta voltar a apontar o Railway
direto para admin_dashboard.py e corretor_dashboard.py como serviços
separados — nenhum dos dois arquivos precisa ser alterado para isso.
"""

import os
import runpy
import streamlit as str_app

# set_page_config só pode ser chamado uma vez por execução, e precisa ser
# a primeira chamada Streamlit do processo — por isso ele mora aqui, no
# roteador, e não nos arquivos individuais quando rodam juntos.
str_app.set_page_config(
    page_title="Sofia IA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "painel_escolhido" not in str_app.session_state:
    # "corretor" é a porta de entrada padrão — quem cai aqui de fora
    # (cliente pagante) nunca vê menção ao painel administrativo.
    str_app.session_state["painel_escolhido"] = "corretor"

DIR_BASE = os.path.dirname(os.path.abspath(__file__))


def render_link_discreto_admin():
    """Link minúsculo no canto inferior, visível só para quem já sabe que está lá."""
    str_app.markdown("""
        <style>
            div[class*="st-key-admin_access_link"] button {
                background: transparent !important;
                border: none !important;
                color: #2a2a31 !important;
                font-size: 0.72rem !important;
                font-weight: 400 !important;
                padding: 0 !important;
                text-decoration: none !important;
            }
            div[class*="st-key-admin_access_link"] button:hover {
                color: #52525b !important;
            }
            div[class*="st-key-admin_access_link"] {
                display: flex;
                justify-content: center;
                margin-top: 2.5rem;
            }
        </style>
    """, unsafe_allow_html=True)

    with str_app.container(key="admin_access_link"):
        if str_app.button("Painel Admin", key="btn_admin_discreto"):
            str_app.session_state["painel_escolhido"] = "admin"
            str_app.rerun()


# =============================================================================
# ROTEAMENTO PRINCIPAL
# =============================================================================
if str_app.session_state["painel_escolhido"] == "admin":
    if str_app.button("← Voltar"):
        str_app.session_state["painel_escolhido"] = "corretor"
        str_app.rerun()
    runpy.run_path(os.path.join(DIR_BASE, "admin_dashboard.py"), run_name="__main__")

else:
    runpy.run_path(os.path.join(DIR_BASE, "corretor_dashboard.py"), run_name="__main__")
    # O link discreto só aparece sob a tela de login/cadastro do corretor —
    # uma vez autenticado, não há necessidade dele (o corretor já está
    # dentro do próprio painel).
    if str_app.session_state.get("cliente_atual") is None:
        render_link_discreto_admin()