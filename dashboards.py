"""
dashboards.py — Ponto de entrada único hospedando a Landing Page pública,
o painel do Corretor (login/cadastro) e o Admin Dashboard (acesso discreto
via link), todos dentro do mesmo serviço Streamlit — economia de recursos
no Railway durante a fase de validação do projeto.

IMPORTANTE sobre a landing page: ela é renderizada via components.html,
que coloca o conteúdo dentro de um <iframe> sandboxed pelo próprio
Streamlit. Esse sandbox bloqueia explicitamente a navegação de nível
superior (não existe "allow-top-navigation" nas políticas padrão), então
botões em JavaScript dentro do HTML da landing NUNCA conseguem redirecionar
a aba real do navegador — apenas a página de cima (fora do iframe) pode
fazer isso. Por isso os botões "Entrar" / "Criar conta" ficam como
st.link_button do Streamlit, renderizados ACIMA do iframe, nunca dentro
do HTML da landing.

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


# =============================================================================
# LANDING PAGE
# =============================================================================
def render_landing_page():
    """Renderiza o HTML estático da landing dentro de um iframe, com uma
    barra real do Streamlit por cima contendo os botões de navegação
    (único jeito de sair do iframe — veja nota no topo do arquivo)."""

    # Esconde a barra de ferramentas padrão do Streamlit (menu, "Deploy",
    # rodapé) e remove o padding do container para a landing ocupar a tela
    # cheia, sem moldura ao redor do iframe.
    str_app.markdown("""
        <style>
            [data-testid="stToolbar"], [data-testid="stDecoration"],
            #MainMenu, footer, [data-testid="stHeader"], .stAppHeader {
                display: none !important;
                height: 0 !important;
                visibility: hidden !important;
            }
            [data-testid="stAppViewContainer"] {
                background-color: #09090b !important;
            }
            [data-testid="stAppViewContainer"] > .main {
                padding-top: 0 !important;
            }
            [data-testid="stMain"] {
                background-color: #09090b !important;
            }
            .block-container, .stMainBlockContainer,
            div[class*="block-container"] {
                padding-top: 0 !important;
                padding-bottom: 0 !important;
                padding-left: 0 !important;
                padding-right: 0 !important;
                margin-top: 0 !important;
                max-width: 100% !important;
            }
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                background-color: #09090b !important;
            }
            div[class*="st-key-barra_nav_landing"] {
                background: #0d0d10;
                border-bottom: 1px solid #1f1f24;
                padding: 0.7rem 1.5rem;
                margin-top: 0 !important;
            }
            div[class*="st-key-barra_nav_landing"] [data-testid="stVerticalBlock"] {
                gap: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    with str_app.container(key="barra_nav_landing"):
        col_logo, col_espaco, col_entrar, col_cadastro = str_app.columns([2, 5, 1, 1.6])
        with col_logo:
            str_app.markdown(
                "<p style='margin:0; color:#fafafa; font-weight:700; font-size:1.05rem; line-height:2.4rem;'>⚡ Sofia IA</p>",
                unsafe_allow_html=True
            )
        with col_entrar:
            if str_app.button("Entrar", key="btn_entrar_landing", use_container_width=True):
                str_app.session_state["painel_escolhido"] = "corretor"
                str_app.rerun()
        with col_cadastro:
            if str_app.button("Testar gratuito", key="btn_cadastro_landing", use_container_width=True, type="primary"):
                str_app.session_state["painel_escolhido"] = "corretor"
                str_app.rerun()

    caminho_html = os.path.join(DIR_BASE, "landing_page.html")
    with open(caminho_html, "r", encoding="utf-8") as f:
        html_bruto = f.read()

    # A landing tem sua própria <nav> fixa e botões de CTA com IDs
    # específicos (ver landing_page.html) que tentam navegar via
    # JavaScript — isso é bloqueado pelo sandbox do iframe, então
    # neutralizamos esses cliques aqui (os botões reais já estão na barra
    # do Streamlit acima). Os links de âncora (#como-funciona, #precos
    # etc.) continuam funcionando normalmente, pois são apenas rolagem
    # dentro do próprio iframe.
    html_ajustado = html_bruto.replace(
        """  ['btn-login-nav','btn-login-footer','btn-cadastro-precos','btn-cadastro-final'].forEach(id => {
    const el = document.getElementById(id);
    if(el){
      el.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = URL_PAINEL_LOGIN;
      });
    }
  });""",
        """  // Botões de login/cadastro reais ficam na barra do Streamlit, fora
  // deste iframe (o sandbox do Streamlit bloqueia navegação de topo a
  // partir de dentro do iframe). Aqui dentro, apenas escondemos a nav
  // fixa própria da landing para não duplicar com a barra do Streamlit.
  const navOriginal = document.querySelector('nav');
  if (navOriginal) navOriginal.style.display = 'none';"""
    )

    components.html(html_ajustado, height=6400, scrolling=True)
    str_app.stop()


# =============================================================================
# ADMIN — LINK DE ACESSO DISCRETO
# =============================================================================
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