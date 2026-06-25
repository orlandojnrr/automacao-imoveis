"""
dashboards.py — Ponto de entrada único hospedando a Landing Page pública,
o painel do Corretor (login/cadastro) e o Admin Dashboard (acesso discreto
via link), todos dentro do mesmo serviço Streamlit — economia de recursos
no Railway durante a fase de validação do projeto.

Quando o negócio crescer e justificar, basta voltar a apontar o Railway
direto para arquivos/serviços separados — nenhum deles precisa ser
alterado para isso.
"""

import os
import runpy
import streamlit as str_app
import streamlit.components.v1 as components

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
    # "landing" é a porta de entrada padrão — visitantes veem a página de
    # apresentação antes de qualquer tela de login.
    str_app.session_state["painel_escolhido"] = "landing"

DIR_BASE = os.path.dirname(os.path.abspath(__file__))


def render_landing_page():
    """Renderiza o HTML estático da landing page dentro do app Streamlit.

    Usamos components.html (não st.markdown) porque a landing tem <style>,
    <script> e uma estrutura de documento completa — coisas que
    st.markdown não executa de forma confiável. O parâmetro height define
    quanto espaço vertical o iframe ocupa; como a página é longa e tem
    rolagem própria, usamos um valor alto e scrolling habilitado.
    """
    # Remove o padding/margem padrão do container principal do Streamlit e
    # zera a cor de fundo dele para igualar ao fundo da landing — sem isso,
    # sobra uma moldura escura/clara ao redor do iframe.
    str_app.markdown("""
        <style>
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding: 0 !important;
                max-width: 100% !important;
            }
            [data-testid="stAppViewContainer"], [data-testid="stMain"] {
                background-color: #09090b !important;
            }
            iframe {
                display: block;
            }
        </style>
    """, unsafe_allow_html=True)

    caminho_html = os.path.join(DIR_BASE, "landing_page.html")
    with open(caminho_html, "r", encoding="utf-8") as f:
        html_bruto = f.read()

    # Os botões de "Entrar"/"Criar conta" da landing usam window.location.href
    # para navegar — mas aqui a landing roda dentro de um <iframe> (efeito do
    # components.html), então precisamos redirecionar a janela PAI
    # (window.parent), senão só o conteúdo do iframe mudaria, deixando o
    # resto da página Streamlit em volta visível e a navegação confusa.
    html_ajustado = html_bruto.replace(
        'window.location.href = URL_PAINEL_LOGIN;',
        'window.parent.location.href = URL_PAINEL_LOGIN;'
    )
    html_ajustado = html_ajustado.replace(
        'const URL_PAINEL_LOGIN = "https://SEU-DOMINIO-DASHBOARDS.up.railway.app";',
        'const URL_PAINEL_LOGIN = window.parent.location.origin + window.parent.location.pathname + "?ir=painel";'
    )

    # Altura generosa (a página real é mais curta que isso) — sobra de
    # iframe vazio é preferível a cortar conteúdo, e o fundo do iframe já
    # está com a mesma cor de base da landing (#09090b), então a sobra
    # não chama atenção como "vácuo".
    components.html(html_ajustado, height=6200, scrolling=True)
    str_app.stop()


# =============================================================================
# ROTEAMENTO PRINCIPAL
# =============================================================================
query_params = str_app.query_params
if query_params.get("ir") == "painel" and str_app.session_state["painel_escolhido"] == "landing":
    str_app.session_state["painel_escolhido"] = "corretor"
    str_app.query_params.clear()

if str_app.session_state["painel_escolhido"] == "landing":
    render_landing_page()

elif str_app.session_state["painel_escolhido"] == "admin":
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