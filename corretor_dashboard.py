import os
import streamlit as str_app
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================
# Em try/except porque, ao rodar dentro do roteador dashboards.py, o
# set_page_config já foi chamado uma vez antes (o Streamlit só permite a
# primeira chamada de cada execução).
try:
    str_app.set_page_config(
        page_title="Sofia IA — Painel do Corretor",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except str_app.errors.StreamlitAPIException:
    pass

# =============================================================================
# CONEXÃO COM SUPABASE
# =============================================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    str_app.error("Configuração do Supabase ausente. Verifique as variáveis de ambiente.")
    str_app.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================================================================
# ESTADO DE SESSÃO
# =============================================================================
if "auth_session" not in str_app.session_state:
    str_app.session_state["auth_session"] = None

if "cliente_atual" not in str_app.session_state:
    str_app.session_state["cliente_atual"] = None

if "tela_auth" not in str_app.session_state:
    str_app.session_state["tela_auth"] = "login"  # "login" ou "cadastro"

# =============================================================================
# UI CSS / ESTILIZAÇÃO (mesmo design system do admin_dashboard.py)
# =============================================================================
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

        .login-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 4vh;
            margin-bottom: -0.5rem;
        }

        .login-badge {
            width: 56px;
            height: 56px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            margin-bottom: 18px;
            background: linear-gradient(135deg, #7d33ff 0%, #5b21b6 100%);
            box-shadow: 0 8px 24px rgba(124,58,237,0.45);
        }

        .login-title {
            color: #fafafa;
            font-size: 1.6rem;
            font-weight: 700;
            margin: 0;
            text-align: center;
            letter-spacing: -0.01em;
        }

        .login-subtitle {
            color: #71717a;
            font-size: 0.9rem;
            margin: 0.35rem 0 1.8rem 0;
            text-align: center;
        }

        div[class*="st-key-auth_card_container"] {
            background: linear-gradient(180deg, #15151a 0%, #111114 100%);
            border: 1px solid #232328;
            border-radius: 18px;
            padding: 1.6rem 2rem 1.2rem 2rem;
            box-shadow: 0 20px 50px rgba(0,0,0,0.55);
        }

        div[class*="st-key-auth_card_container"] [data-testid="stForm"] {
            border: none;
            padding: 0;
        }

        div[class*="st-key-auth_card_container"] label {
            color: #a1a1aa !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
        }

        div[class*="st-key-auth_card_container"] [data-testid="stTextInput"] input {
            background-color: #0c0c0f !important;
            border: 1px solid #2a2a31 !important;
            border-radius: 10px !important;
            color: #fafafa !important;
            padding: 0.65rem 0.85rem !important;
        }

        div[class*="st-key-auth_card_container"] [data-testid="stTextInput"] input:focus {
            border-color: #7d33ff !important;
            box-shadow: 0 0 0 3px rgba(124,58,237,0.18) !important;
        }

        div[class*="st-key-auth_card_container"] [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #7d33ff 0%, #6425e0 100%);
            border: none;
            border-radius: 10px;
            color: #fff;
            font-weight: 600;
            padding: 0.65rem 0;
            margin-top: 0.4rem;
            transition: filter 0.15s ease, transform 0.05s ease;
        }

        div[class*="st-key-auth_card_container"] [data-testid="stFormSubmitButton"] button:hover {
            filter: brightness(1.08);
        }

        .auth-switch-text {
            text-align: center;
            color: #71717a;
            font-size: 0.85rem;
            margin-top: 1.1rem;
        }

        .stButton button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            color: #a78bfa !important;
            font-weight: 600 !important;
            text-decoration: underline;
        }

        .page-eyebrow {
            color: #a78bfa;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin: 0 0 0.3rem 0;
        }

        .page-title {
            color: #fafafa;
            font-size: 1.9rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            margin: 0;
        }

        .page-subtitle {
            color: #71717a;
            font-size: 0.95rem;
            margin: 0.4rem 0 1.6rem 0;
        }

        hr {
            border-color: #1f1f24 !important;
            margin: 0.6rem 0 1.2rem 0 !important;
        }
    </style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNÇÕES DE AUTENTICAÇÃO
# =============================================================================
def fazer_login(email: str, senha: str):
    """Autentica o corretor via Supabase Auth e carrega o cliente_saas vinculado."""
    try:
        resultado = supabase.auth.sign_in_with_password({"email": email, "password": senha})

        if resultado.user:
            str_app.session_state["auth_session"] = resultado.session

            cliente_res = supabase.table("clientes_saas") \
                .select("*") \
                .eq("auth_user_id", resultado.user.id) \
                .execute()

            if cliente_res.data:
                str_app.session_state["cliente_atual"] = cliente_res.data[0]
                return True, None
            else:
                return False, "Login válido, mas nenhum cadastro de corretor vinculado a esta conta."

        return False, "Não foi possível autenticar."

    except Exception as e:
        mensagem = str(e)
        if "Invalid login credentials" in mensagem:
            return False, "E-mail ou senha incorretos."
        return False, f"Erro ao fazer login: {mensagem}"


def fazer_cadastro(nome: str, nome_empresa: str, email: str, senha: str):
    """Cria o usuário no Supabase Auth e a linha correspondente em clientes_saas."""
    try:
        resultado = supabase.auth.sign_up({"email": email, "password": senha})

        if not resultado.user:
            return False, "Não foi possível criar a conta."

        novo_cliente = {
            "auth_user_id": resultado.user.id,
            "nome_corretor": nome,
            "nome_empresa": nome_empresa,
            "email": email,
        }
        supabase.table("clientes_saas").insert(novo_cliente).execute()

        return True, None

    except Exception as e:
        mensagem = str(e)
        if "already registered" in mensagem.lower() or "already exists" in mensagem.lower():
            return False, "Este e-mail já está cadastrado. Tente fazer login."
        return False, f"Erro ao criar conta: {mensagem}"


def fazer_logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    str_app.session_state["auth_session"] = None
    str_app.session_state["cliente_atual"] = None
    str_app.rerun()


# =============================================================================
# TELA DE LOGIN
# =============================================================================
def render_login():
    c1, c2, c3 = str_app.columns([1, 1.1, 1])

    with c2:
        str_app.markdown("""
            <div class="login-wrapper">
                <div class="login-badge">⚡</div>
                <p class="login-title">Sofia IA — Painel do Corretor</p>
                <p class="login-subtitle">Acesse sua conta para gerenciar seu WhatsApp e catálogo</p>
            </div>
        """, unsafe_allow_html=True)

        with str_app.container(key="auth_card_container"):
            with str_app.form(key="login_form", border=False):
                email_input = str_app.text_input("E-mail", placeholder="seu@email.com")
                senha_input = str_app.text_input("Senha", type="password", placeholder="••••••••")

                enviou = str_app.form_submit_button("Entrar", use_container_width=True)

                if enviou:
                    if not email_input or not senha_input:
                        str_app.error("Preencha e-mail e senha.")
                    else:
                        with str_app.spinner("Verificando credenciais..."):
                            sucesso, erro = fazer_login(email_input, senha_input)
                        if sucesso:
                            str_app.rerun()
                        else:
                            str_app.error(erro)

            str_app.markdown('<p class="auth-switch-text">Ainda não tem uma conta?</p>', unsafe_allow_html=True)
            if str_app.button("Criar conta gratuita", use_container_width=True, type="secondary", key="ir_cadastro"):
                str_app.session_state["tela_auth"] = "cadastro"
                str_app.rerun()


# =============================================================================
# TELA DE CADASTRO
# =============================================================================
def render_cadastro():
    c1, c2, c3 = str_app.columns([1, 1.1, 1])

    with c2:
        str_app.markdown("""
            <div class="login-wrapper">
                <div class="login-badge">⚡</div>
                <p class="login-title">Criar sua conta</p>
                <p class="login-subtitle">Comece a usar a Sofia IA no seu WhatsApp</p>
            </div>
        """, unsafe_allow_html=True)

        with str_app.container(key="auth_card_container"):
            with str_app.form(key="cadastro_form", border=False):
                nome_input = str_app.text_input("Nome completo", placeholder="Seu nome")
                nome_empresa_input = str_app.text_input("Nome da imobiliária/empresa", placeholder="Ex: Imobiliária Silva")
                email_input = str_app.text_input("E-mail", placeholder="seu@email.com")
                senha_input = str_app.text_input("Senha", type="password", placeholder="mínimo 6 caracteres")
                senha_confirma = str_app.text_input("Confirme a senha", type="password", placeholder="repita a senha")

                enviou = str_app.form_submit_button("Criar conta", use_container_width=True)

                if enviou:
                    if not nome_input or not nome_empresa_input or not email_input or not senha_input:
                        str_app.error("Preencha todos os campos.")
                    elif senha_input != senha_confirma:
                        str_app.error("As senhas não coincidem.")
                    elif len(senha_input) < 6:
                        str_app.error("A senha precisa ter no mínimo 6 caracteres.")
                    else:
                        with str_app.spinner("Criando sua conta..."):
                            sucesso, erro = fazer_cadastro(nome_input, nome_empresa_input, email_input, senha_input)
                        if sucesso:
                            str_app.success("Conta criada com sucesso! Faça login para continuar.")
                            str_app.session_state["tela_auth"] = "login"
                            str_app.rerun()
                        else:
                            str_app.error(erro)

            str_app.markdown('<p class="auth-switch-text">Já tem uma conta?</p>', unsafe_allow_html=True)
            if str_app.button("Fazer login", use_container_width=True, type="secondary", key="ir_login"):
                str_app.session_state["tela_auth"] = "login"
                str_app.rerun()


# =============================================================================
# DASHBOARD PRINCIPAL (placeholder — próximas etapas: WhatsApp + Catálogo)
# =============================================================================
def render_dashboard():
    cliente = str_app.session_state["cliente_atual"]

    str_app.sidebar.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; padding: 0.5rem 0 1.1rem 0;">
            <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#7d33ff,#5b21b6);
                        display:flex; align-items:center; justify-content:center; font-size:18px;">⚡</div>
            <div>
                <p style="margin:0; color:#fafafa; font-weight:700; font-size:1.0rem; line-height:1.1;">{cliente.get('nome_corretor', 'Corretor')}</p>
                <p style="margin:0; color:#71717a; font-size:0.74rem;">Painel do Corretor</p>
            </div>
        </div>
        <hr style="margin: 0 0 0.8rem 0 !important;">
    """, unsafe_allow_html=True)

    if str_app.sidebar.button("⏻  Sair", use_container_width=True):
        fazer_logout()

    str_app.markdown("""
        <p class="page-eyebrow">Painel do Corretor</p>
        <h1 class="page-title">Bem-vindo de volta 👋</h1>
        <p class="page-subtitle">Em breve: conexão do WhatsApp e gerenciamento do catálogo de imóveis aqui.</p>
        <hr>
    """, unsafe_allow_html=True)

    str_app.info("Próximas etapas: tela de conexão do WhatsApp (QR Code) e catálogo de imóveis.")


# =============================================================================
# ROTEAMENTO PRINCIPAL
# =============================================================================
if str_app.session_state["cliente_atual"] is not None:
    render_dashboard()
elif str_app.session_state["tela_auth"] == "cadastro":
    render_cadastro()
else:
    render_login()