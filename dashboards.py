"""
dashboards.py — Roteador único que hospeda tanto o Admin Dashboard quanto o
Corretor Dashboard dentro do mesmo serviço Streamlit, para economizar
recursos no Railway enquanto o projeto está em fase de testes/validação.

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
    page_title="Sofia IA — Dashboards",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "painel_escolhido" not in str_app.session_state:
    str_app.session_state["painel_escolhido"] = None


def render_selecao():
    str_app.markdown("""
        <style>
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #09090b !important;
            }
            [data-testid="stAppViewContainer"] > .main {
                background:
                    radial-gradient(circle at 18% 20%, rgba(124,58,237,0.16), transparent 38%),
                    radial-gradient(circle at 82% 78%, rgba(99,102,241,0.14), transparent 42%),
                    #09090b;
            }
            #MainMenu, header, footer { visibility: hidden; }

            .select-wrapper {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding-top: 6vh;
                margin-bottom: 1.6rem;
            }
            .select-badge {
                width: 56px; height: 56px; border-radius: 16px;
                display: flex; align-items: center; justify-content: center;
                font-size: 26px; margin-bottom: 18px;
                background: linear-gradient(135deg, #7d33ff 0%, #5b21b6 100%);
                box-shadow: 0 8px 24px rgba(124,58,237,0.45);
            }
            .select-title {
                color: #fafafa; font-size: 1.7rem; font-weight: 700;
                margin: 0; text-align: center; letter-spacing: -0.01em;
            }
            .select-subtitle {
                color: #71717a; font-size: 0.92rem;
                margin: 0.4rem 0 0 0; text-align: center;
            }

            div[class*="st-key-card_admin"] button, div[class*="st-key-card_corretor"] button {
                height: 11rem;
                border-radius: 16px !important;
                border: 1px solid #232328 !important;
                background: linear-gradient(155deg, #15151a 0%, #101012 100%) !important;
                color: #fafafa !important;
                font-size: 1.1rem !important;
                font-weight: 700 !important;
                transition: border-color 0.15s ease, transform 0.05s ease;
            }
            div[class*="st-key-card_admin"] button:hover, div[class*="st-key-card_corretor"] button:hover {
                border-color: #7d33ff !important;
            }
            div[class*="st-key-card_admin"] button:active, div[class*="st-key-card_corretor"] button:active {
                transform: scale(0.99);
            }
        </style>
    """, unsafe_allow_html=True)

    str_app.markdown("""
        <div class="select-wrapper">
            <div class="select-badge">⚡</div>
            <p class="select-title">Sofia IA</p>
            <p class="select-subtitle">Selecione qual painel você deseja acessar</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = str_app.columns([1, 0.05, 1])

    with c1:
        with str_app.container(key="card_admin"):
            if str_app.button("🛠️\n\nSou Admin", use_container_width=True, key="btn_admin"):
                str_app.session_state["painel_escolhido"] = "admin"
                str_app.rerun()

    with c3:
        with str_app.container(key="card_corretor"):
            if str_app.button("🏠\n\nSou Corretor(a)", use_container_width=True, key="btn_corretor"):
                str_app.session_state["painel_escolhido"] = "corretor"
                str_app.rerun()


# =============================================================================
# ROTEAMENTO PRINCIPAL
# =============================================================================
DIR_BASE = os.path.dirname(os.path.abspath(__file__))

if str_app.session_state["painel_escolhido"] == "admin":
    if str_app.button("← Voltar à seleção de painéis"):
        str_app.session_state["painel_escolhido"] = None
        str_app.rerun()
    runpy.run_path(os.path.join(DIR_BASE, "admin_dashboard.py"), run_name="__main__")

elif str_app.session_state["painel_escolhido"] == "corretor":
    if str_app.button("← Voltar à seleção de painéis"):
        str_app.session_state["painel_escolhido"] = None
        str_app.rerun()
    runpy.run_path(os.path.join(DIR_BASE, "corretor_dashboard.py"), run_name="__main__")

else:
    render_selecao()
