import os
import time
import base64
import secrets
import requests
import urllib.parse
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
# CONFIGURAÇÃO DA EVOLUTION API
# =============================================================================
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "").rstrip("/")
WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN", "")

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

        #MainMenu, footer { visibility: hidden; }

        /* Mantemos o header visível (ele contém o botão de reabrir o
           sidebar quando colapsado), mas removemos seu fundo/sombra para
           que pareça transparente e não quebre o visual. */
        header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
        }

        /* =================== SIDEBAR — VISUAL REFINADO =================== */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d0d10 0%, #09090b 100%);
            border-right: 1px solid #1f1f24;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] > label {
            display: none;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] > div {
            gap: 0.3rem;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            background: transparent;
            border-radius: 10px;
            padding: 0.55rem 0.7rem;
            margin: 0;
            transition: background 0.15s ease;
            cursor: pointer;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: #16161a;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label span {
            color: #d4d4d8 !important;
            font-size: 0.92rem !important;
            font-weight: 500 !important;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: linear-gradient(135deg, rgba(124,58,237,0.18), rgba(124,58,237,0.05));
            border-left: 2px solid #7d33ff;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span {
            color: #c4b5fd !important;
            font-weight: 600 !important;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
            display: none;
        }

        [data-testid="stSidebar"] .stButton button {
            background: #18181b;
            border: 1px solid #2a2a31;
            color: #d4d4d8;
            border-radius: 9px;
            font-weight: 500;
            transition: border-color 0.15s ease, color 0.15s ease;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            border-color: #ef4444;
            color: #f87171;
        }

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
# FUNÇÕES — INTEGRAÇÃO COM A EVOLUTION API (CONEXÃO WHATSAPP)
# =============================================================================
def gerar_instance_name(cliente_id: str) -> str:
    """Gera o nome único e estável da instância a partir do cliente_id."""
    return f"cliente_{cliente_id.replace('-', '')[:8]}"


def buscar_configuracao_whatsapp(cliente_id: str):
    """Busca a linha de configuração do WhatsApp deste corretor, se existir."""
    try:
        res = supabase.table("configuracoes_whatsapp") \
            .select("*") \
            .eq("cliente_id", cliente_id) \
            .execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao buscar configuração do WhatsApp: {e}", flush=True)
        return None


def criar_instancia_evolution(instance_name: str):
    """Cria a instância na Evolution API e retorna o QR Code em base64."""
    try:
        url = f"{WHATSAPP_API_URL}/instance/create"
        headers = {"Content-Type": "application/json", "apikey": WHATSAPP_API_TOKEN}
        payload = {
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": True,
        }
        resposta = requests.post(url, json=payload, headers=headers, timeout=20)

        if resposta.status_code in [200, 201]:
            dados = resposta.json()
            qrcode_base64 = dados.get("qrcode", {}).get("base64")
            return True, qrcode_base64, None
        else:
            return False, None, f"Status {resposta.status_code}: {resposta.text[:200]}"

    except Exception as e:
        return False, None, str(e)


def obter_qrcode_evolution(instance_name: str):
    """Solicita um novo QR Code para uma instância já existente."""
    try:
        url = f"{WHATSAPP_API_URL}/instance/connect/{instance_name}"
        headers = {"apikey": WHATSAPP_API_TOKEN}
        resposta = requests.get(url, headers=headers, timeout=20)

        if resposta.status_code == 200:
            dados = resposta.json()
            qrcode_base64 = dados.get("base64") or dados.get("qrcode", {}).get("base64")
            return True, qrcode_base64, None
        else:
            return False, None, f"Status {resposta.status_code}: {resposta.text[:200]}"

    except Exception as e:
        return False, None, str(e)


def verificar_status_evolution(instance_name: str):
    """Consulta o status atual da conexão ('open', 'close' ou 'connecting')."""
    try:
        url = f"{WHATSAPP_API_URL}/instance/connectionState/{instance_name}"
        headers = {"apikey": WHATSAPP_API_TOKEN}
        resposta = requests.get(url, headers=headers, timeout=15)

        if resposta.status_code == 200:
            dados = resposta.json()
            estado = dados.get("instance", {}).get("state", "close")
            return estado
        return "close"

    except Exception as e:
        print(f"[EVOLUTION] ❌ Erro ao verificar status: {e}", flush=True)
        return "close"


def salvar_configuracao_whatsapp(cliente_id: str, instance_name: str, status_conexao: str,
                                   numero_handoff: str = None, nome_handoff: str = None):
    """Cria ou atualiza a linha de configuração do WhatsApp deste corretor."""
    try:
        existente = buscar_configuracao_whatsapp(cliente_id)
        dados = {
            "cliente_id": cliente_id,
            "instance_name": instance_name,
            "status_conexao": status_conexao,
        }
        if numero_handoff:
            dados["numero_corretor_handoff"] = numero_handoff
        if nome_handoff:
            dados["nome_corretor_handoff"] = nome_handoff

        if existente:
            supabase.table("configuracoes_whatsapp").update(dados).eq("cliente_id", cliente_id).execute()
        else:
            # api_token e numero_corretor_handoff são obrigatórios na tabela —
            # api_token é só um identificador interno (não é a chave global
            # da Evolution API, essa fica só na variável de ambiente).
            dados["api_token"] = secrets.token_hex(16)
            dados["status_financeiro"] = "Ativo"
            supabase.table("configuracoes_whatsapp").insert(dados).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao salvar configuração do WhatsApp: {e}", flush=True)
        return False


# =============================================================================
# TELA — CONECTAR WHATSAPP
# =============================================================================
def render_conectar_whatsapp(cliente: dict):
    cliente_id = cliente["id"]
    instance_name = gerar_instance_name(cliente_id)

    config_atual = buscar_configuracao_whatsapp(cliente_id)
    status_salvo = config_atual.get("status_conexao") if config_atual else None

    str_app.markdown("""
        <p class="page-eyebrow">Painel do Corretor</p>
        <h1 class="page-title">Conectar WhatsApp</h1>
        <p class="page-subtitle">Conecte o número que vai atender seus leads através da Sofia.</p>
        <hr>
    """, unsafe_allow_html=True)

    if status_salvo == "CONECTADO":
        str_app.success("✅ Seu WhatsApp está conectado e a Sofia já está ativa para qualificar leads.")
        if str_app.button("🔄 Verificar conexão novamente"):
            estado = verificar_status_evolution(instance_name)
            if estado != "open":
                salvar_configuracao_whatsapp(cliente_id, instance_name, "DESCONECTADO")
                str_app.warning("Conexão perdida. Recarregando a página para gerar um novo QR Code...")
                time.sleep(1.2)
                str_app.rerun()
            else:
                str_app.success("Tudo certo, conexão confirmada!")

    elif config_atual is None:
        # Primeiro acesso: precisamos do número de handoff antes de criar a instância.
        str_app.markdown("##### 📞 Antes de conectar, precisamos do seu número de WhatsApp pessoal")
        str_app.caption("É para esse número que a Sofia vai te avisar quando um lead estiver qualificado.")

        with str_app.form(key="form_handoff"):
            nome_handoff_input = str_app.text_input("Seu nome (como aparece para a Sofia)", value=cliente.get("nome_corretor", ""))
            numero_handoff_input = str_app.text_input("Seu WhatsApp com DDI e DDD", placeholder="Ex: 5584999998888")
            str_app.caption("Atenção: este número não será utilizado para conectar o QR Code. Ele serve exclusivamente para que a Sofia envie a você o aviso de lead qualificado.")
            confirmou = str_app.form_submit_button("Continuar para o QR Code", type="primary")

            if confirmou:
                numero_limpo = "".join(filter(str.isdigit, numero_handoff_input))
                if len(numero_limpo) < 12:
                    str_app.error("Informe o número completo com DDI (55) + DDD + número. Ex: 5584999998888")
                else:
                    with str_app.spinner("Preparando sua conexão..."):
                        sucesso, qrcode, erro = criar_instancia_evolution(instance_name)
                        if sucesso and qrcode:
                            salvar_configuracao_whatsapp(
                                cliente_id, instance_name, "AGUARDANDO_QR",
                                numero_handoff=numero_limpo, nome_handoff=nome_handoff_input
                            )
                            str_app.session_state["qrcode_atual"] = qrcode
                            str_app.rerun()
                        else:
                            str_app.error(f"Não foi possível gerar o QR Code: {erro}")

    else:
        if "qrcode_atual" not in str_app.session_state:
            str_app.session_state["qrcode_atual"] = None

        if str_app.session_state["qrcode_atual"] is None and status_salvo != "CONECTADO":
            with str_app.spinner("Preparando sua conexão..."):
                sucesso, qrcode, erro = obter_qrcode_evolution(instance_name)

                if sucesso and qrcode:
                    str_app.session_state["qrcode_atual"] = qrcode
                elif not sucesso:
                    str_app.error(f"Não foi possível gerar o QR Code: {erro}")

        if str_app.session_state["qrcode_atual"]:
            qr_data = str_app.session_state["qrcode_atual"]
            if not qr_data.startswith("data:image"):
                qr_data = f"data:image/png;base64,{qr_data}"

            col_qr, col_info = str_app.columns([1, 1.3])
            with col_qr:
                str_app.image(qr_data, width=260)

            with col_info:
                str_app.markdown("##### 📱 Como conectar:")
                str_app.markdown("""
                1. Abra o WhatsApp no celular que vai atender os leads
                2. Vá em **Configurações → Dispositivos conectados**
                3. Toque em **Conectar um dispositivo**
                4. Aponte a câmera para o QR Code ao lado
                """)

                if str_app.button("✅ Já escaneei — Verificar conexão", type="primary"):
                    with str_app.spinner("Verificando..."):
                        estado = verificar_status_evolution(instance_name)
                    if estado == "open":
                        salvar_configuracao_whatsapp(cliente_id, instance_name, "CONECTADO")
                        str_app.session_state["qrcode_atual"] = None
                        str_app.success("🎉 Conectado com sucesso!")
                        time.sleep(1.2)
                        str_app.rerun()
                    else:
                        str_app.warning("Ainda não detectamos a conexão. Tente escanear novamente ou aguarde alguns segundos.")

                if str_app.button("🔄 Gerar novo QR Code"):
                    str_app.session_state["qrcode_atual"] = None
                    str_app.rerun()

    str_app.markdown("<hr>", unsafe_allow_html=True)
    str_app.markdown(
        f"<p style='color:#52525b; font-size:0.82rem;'>Seu código de cliente (informe ao suporte se precisar de ajuda): "
        f"<code style='background:#1f1f24; padding:2px 8px; border-radius:5px; color:#a78bfa;'>{instance_name}</code></p>",
        unsafe_allow_html=True
    )


# =============================================================================
# FUNÇÕES — CATÁLOGO DE IMÓVEIS
# =============================================================================
TIPOS_IMOVEL = ["Casa", "Apartamento", "Terreno", "Sala Comercial"]
STATUS_IMOVEL = ["Disponível", "Reservado", "Vendido"]
FINALIDADES_IMOVEL = ["Venda", "Aluguel", "Venda ou Aluguel"]


def listar_imoveis(cliente_id: str):
    """Retorna todos os imóveis cadastrados por este corretor, mais recentes primeiro."""
    try:
        res = supabase.table("imoveis") \
            .select("*") \
            .eq("cliente_id", cliente_id) \
            .order("criado_em", desc=True) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao listar imóveis: {e}", flush=True)
        return []


def fazer_upload_fotos(auth_user_id: str, arquivos: list):
    """Sobe cada arquivo de imagem para o bucket fotos-imoveis e retorna as URLs públicas.

    O caminho usa o auth_user_id (não o cliente_id da tabela clientes_saas)
    porque a policy RLS do bucket checa storage.foldername(name)[1] contra
    auth.uid() — são UUIDs diferentes.

    Reaplicamos a sessão no client antes do upload porque o Streamlit
    reroda o script a cada interação, e o client supabase perde o token
    de autenticação em memória entre as reruns — sem isso, a chamada ao
    Storage vai como anônima e a policy RLS bloqueia com 403.
    """
    sessao = str_app.session_state.get("auth_session")
    if sessao:
        try:
            supabase.auth.set_session(sessao.access_token, sessao.refresh_token)
        except Exception as e:
            print(f"[AUTH] ⚠️ Não foi possível restaurar a sessão: {e}", flush=True)

    urls = []
    for arquivo in arquivos:
        try:
            extensao = arquivo.name.split(".")[-1].lower()
            nome_unico = f"{auth_user_id}/{secrets.token_hex(8)}.{extensao}"
            conteudo = arquivo.getvalue()

            supabase.storage.from_("fotos-imoveis").upload(
                nome_unico, conteudo,
                file_options={"content-type": arquivo.type}
            )
            url_publica = supabase.storage.from_("fotos-imoveis").get_public_url(nome_unico)
            urls.append(url_publica)
        except Exception as e:
            print(f"[STORAGE] ❌ Erro ao subir foto {arquivo.name}: {e}", flush=True)
    return urls


def criar_imovel(cliente_id: str, auth_user_id: str, dados: dict, fotos_arquivos: list):
    """Cria um novo imóvel, fazendo upload das fotos antes de salvar a linha."""
    try:
        urls_fotos = fazer_upload_fotos(auth_user_id, fotos_arquivos) if fotos_arquivos else []
        dados["cliente_id"] = cliente_id
        dados["fotos_urls"] = urls_fotos
        supabase.table("imoveis").insert(dados).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def excluir_imovel(imovel_id: str):
    try:
        supabase.table("imoveis").delete().eq("id", imovel_id).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao excluir imóvel: {e}", flush=True)
        return False


def atualizar_status_imovel(imovel_id: str, novo_status: str):
    try:
        supabase.table("imoveis").update({"status": novo_status}).eq("id", imovel_id).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao atualizar status do imóvel: {e}", flush=True)
        return False


def atualizar_imovel(imovel_id: str, dados: dict, auth_user_id: str, novas_fotos: list = None, manter_fotos_atuais: list = None):
    """Atualiza os dados de um imóvel existente, opcionalmente enviando novas fotos."""
    try:
        urls_fotos = list(manter_fotos_atuais or [])
        if novas_fotos:
            urls_fotos += fazer_upload_fotos(auth_user_id, novas_fotos)
        dados["fotos_urls"] = urls_fotos
        supabase.table("imoveis").update(dados).eq("id", imovel_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def montar_texto_compartilhamento(dados_imovel: dict) -> str:
    """Monta um texto-resumo do imóvel, pronto para compartilhar em redes sociais."""
    endereco_completo = f"{dados_imovel.get('endereco', '')}, {dados_imovel.get('numero', '')} - {dados_imovel.get('bairro', '')}, {dados_imovel.get('cidade', '')}/{dados_imovel.get('estado', '')}"

    partes_ambientes = []
    if dados_imovel.get("quartos"):
        partes_ambientes.append(f"{dados_imovel['quartos']} quarto(s)")
    if dados_imovel.get("qtd_suites"):
        partes_ambientes.append(f"{dados_imovel['qtd_suites']} suíte(s)")
    if dados_imovel.get("qtd_banheiros"):
        partes_ambientes.append(f"{dados_imovel['qtd_banheiros']} banheiro(s)")
    if dados_imovel.get("vagas_garagem"):
        partes_ambientes.append(f"{dados_imovel['vagas_garagem']} vaga(s) de garagem")

    resumo_ambientes = " · ".join(partes_ambientes) if partes_ambientes else ""

    rotulo_finalidade = {
        "Venda": "à venda",
        "Aluguel": "para aluguel",
        "Venda ou Aluguel": "à venda ou para aluguel"
    }.get(dados_imovel.get("finalidade"), "à venda")

    texto = (
        f"🏡 {dados_imovel.get('tipo_imovel', 'Imóvel')} {rotulo_finalidade} em {dados_imovel.get('bairro', '')}\n\n"
        f"📍 {endereco_completo}\n"
    )
    if resumo_ambientes:
        texto += f"🛏️ {resumo_ambientes}\n"
    if dados_imovel.get("metragem"):
        texto += f"📐 {dados_imovel['metragem']}m²\n"
    texto += f"💰 {formatar_preco(dados_imovel.get('preco'))}\n"
    if dados_imovel.get("descricao"):
        texto += f"\n{dados_imovel['descricao']}\n"
    texto += "\n📲 Fale comigo para mais informações!"
    return texto


def render_botoes_compartilhar(texto: str):
    texto_codificado = urllib.parse.quote(texto)

    link_whatsapp = f"https://wa.me/?text={texto_codificado}"
    link_facebook = f"https://www.facebook.com/sharer/sharer.php?u=https://sofia-ia.app&quote={texto_codificado}"
    link_telegram = f"https://t.me/share/url?url=https://sofia-ia.app&text={texto_codificado}"

    str_app.markdown("##### 📣 Compartilhar este imóvel")
    str_app.caption("O Instagram não permite compartilhamento direto por link — copie o texto abaixo e cole na publicação ou nos stories.")

    c1, c2, c3 = str_app.columns(3)
    with c1:
        str_app.link_button("💬 WhatsApp", link_whatsapp, use_container_width=True)
    with c2:
        str_app.link_button("📘 Facebook", link_facebook, use_container_width=True)
    with c3:
        str_app.link_button("✈️ Telegram", link_telegram, use_container_width=True)

    with str_app.expander("📋 Copiar texto para Instagram ou outras redes"):
        str_app.code(texto, language=None)


@str_app.dialog("✏️ Editar imóvel", width="large")
def modal_editar_imovel(imovel: dict, auth_user_id: str):
    imovel_id = imovel["id"]

    str_app.markdown("##### 📍 Localização")
    col_end1, col_end2 = str_app.columns([3, 1])
    with col_end1:
        endereco = str_app.text_input("Endereço", value=imovel.get("endereco") or "")
    with col_end2:
        numero = str_app.text_input("Número", value=imovel.get("numero") or "")

    col_loc1, col_loc2, col_loc3 = str_app.columns(3)
    with col_loc1:
        bairro = str_app.text_input("Bairro", value=imovel.get("bairro") or "")
    with col_loc2:
        cidade = str_app.text_input("Cidade", value=imovel.get("cidade") or "")
    with col_loc3:
        estado = str_app.text_input("Estado (UF)", value=imovel.get("estado") or "", max_chars=2)

    cep = str_app.text_input("Código postal (CEP)", value=imovel.get("cep") or "")

    str_app.markdown("<hr>", unsafe_allow_html=True)
    str_app.markdown("##### 🏷️ Dados do imóvel")

    col1, col2 = str_app.columns(2)
    with col1:
        tipo = str_app.selectbox("Tipo de imóvel", TIPOS_IMOVEL, index=TIPOS_IMOVEL.index(imovel["tipo_imovel"]) if imovel.get("tipo_imovel") in TIPOS_IMOVEL else 0)
        finalidade = str_app.selectbox("Finalidade", FINALIDADES_IMOVEL, index=FINALIDADES_IMOVEL.index(imovel["finalidade"]) if imovel.get("finalidade") in FINALIDADES_IMOVEL else 0)
        preco = str_app.number_input("Preço (R$)", min_value=0.0, step=1000.0, format="%.2f", value=float(imovel.get("preco") or 0))
    with col2:
        status = str_app.selectbox("Status", STATUS_IMOVEL, index=STATUS_IMOVEL.index(imovel["status"]) if imovel.get("status") in STATUS_IMOVEL else 0)
        metragem = str_app.number_input("Metragem (m²)", min_value=0.0, step=1.0, value=float(imovel.get("metragem") or 0))

    str_app.markdown("<hr>", unsafe_allow_html=True)
    str_app.markdown("##### ✅ Ambientes (informe a quantidade de cada um)")

    col_a1, col_a2, col_a3, col_a4 = str_app.columns(4)
    with col_a1:
        quartos = str_app.number_input("🛏️ Quartos", min_value=0, step=1, value=int(imovel.get("quartos") or 0))
        qtd_suites = str_app.number_input("🛌 Suítes", min_value=0, step=1, value=int(imovel.get("qtd_suites") or 0))
    with col_a2:
        qtd_banheiros = str_app.number_input("🚿 Banheiros", min_value=0, step=1, value=int(imovel.get("qtd_banheiros") or 0))
        vagas = str_app.number_input("🚗 Vagas de garagem", min_value=0, step=1, value=int(imovel.get("vagas_garagem") or 0))
    with col_a3:
        qtd_cozinha = str_app.number_input("🍳 Cozinha", min_value=0, step=1, value=int(imovel.get("qtd_cozinha") or 0))
        qtd_sala_estar = str_app.number_input("🛋️ Sala de estar", min_value=0, step=1, value=int(imovel.get("qtd_sala_estar") or 0))
    with col_a4:
        qtd_area = str_app.number_input("🌿 Área", min_value=0, step=1, value=int(imovel.get("qtd_area") or 0))
        qtd_quintal = str_app.number_input("🏡 Quintal", min_value=0, step=1, value=int(imovel.get("qtd_quintal") or 0))

    qtd_lavanderia = str_app.number_input("🧺 Lavanderia", min_value=0, step=1, value=int(imovel.get("qtd_lavanderia") or 0))

    str_app.markdown("<hr>", unsafe_allow_html=True)
    descricao = str_app.text_area("Descrição do imóvel", value=imovel.get("descricao") or "")

    fotos_atuais = imovel.get("fotos_urls") or []
    if fotos_atuais:
        str_app.markdown("**Fotos atuais:**")
        str_app.image(fotos_atuais, width=90)
        manter_fotos = str_app.multiselect(
            "Desmarque para remover alguma foto atual",
            options=fotos_atuais, default=fotos_atuais,
            label_visibility="collapsed"
        )
    else:
        manter_fotos = []

    espacos_restantes = 6 - len(manter_fotos)
    novas_fotos = []
    if espacos_restantes > 0:
        novas_fotos = str_app.file_uploader(
            f"Adicionar novas fotos (até {espacos_restantes})",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True
        )
        if novas_fotos and len(novas_fotos) > espacos_restantes:
            str_app.warning(f"Limite de 6 fotos no total — apenas as {espacos_restantes} primeiras novas serão enviadas.")
            novas_fotos = novas_fotos[:espacos_restantes]

    col_salvar, col_cancelar = str_app.columns(2)
    with col_salvar:
        if str_app.button("💾 Salvar alterações", type="primary", use_container_width=True):
            if not bairro or not endereco or preco <= 0:
                str_app.error("Preencha ao menos o endereço, o bairro e o preço.")
            else:
                with str_app.spinner("Salvando alterações..."):
                    dados_imovel = {
                        "tipo_imovel": tipo,
                        "finalidade": finalidade,
                        "endereco": endereco,
                        "numero": numero,
                        "bairro": bairro,
                        "cidade": cidade,
                        "estado": estado.upper() if estado else None,
                        "cep": cep,
                        "quartos": int(quartos),
                        "vagas_garagem": int(vagas),
                        "metragem": float(metragem) if metragem else None,
                        "preco": float(preco),
                        "status": status,
                        "descricao": descricao,
                        "qtd_cozinha": int(qtd_cozinha),
                        "qtd_sala_estar": int(qtd_sala_estar),
                        "qtd_area": int(qtd_area),
                        "qtd_quintal": int(qtd_quintal),
                        "qtd_banheiros": int(qtd_banheiros),
                        "qtd_suites": int(qtd_suites),
                        "qtd_lavanderia": int(qtd_lavanderia),
                    }
                    sucesso, erro = atualizar_imovel(imovel_id, dados_imovel, auth_user_id, novas_fotos, manter_fotos)

                if sucesso:
                    str_app.success("Imóvel atualizado com sucesso!")
                    time.sleep(1)
                    str_app.rerun()
                else:
                    str_app.error(f"Erro ao salvar: {erro}")
    with col_cancelar:
        if str_app.button("Cancelar", use_container_width=True, key="cancelar_edicao"):
            str_app.rerun()


@str_app.dialog("➕ Adicionar novo imóvel", width="large")
def modal_novo_imovel(cliente_id: str, auth_user_id: str):
    if "imovel_recem_salvo" not in str_app.session_state:
        str_app.session_state["imovel_recem_salvo"] = None

    # --- ETAPA 2: imóvel já salvo — mostra confirmação + compartilhamento ---
    if str_app.session_state["imovel_recem_salvo"] is not None:
        str_app.success("✅ Imóvel cadastrado com sucesso!")
        texto_compartilhar = montar_texto_compartilhamento(str_app.session_state["imovel_recem_salvo"])
        render_botoes_compartilhar(texto_compartilhar)

        str_app.markdown("<br>", unsafe_allow_html=True)
        if str_app.button("Fechar", use_container_width=True, type="primary"):
            str_app.session_state["imovel_recem_salvo"] = None
            str_app.rerun()
        return

    # --- ETAPA 1: formulário de cadastro ---
    str_app.markdown("##### 📍 Localização")
    col_end1, col_end2 = str_app.columns([3, 1])
    with col_end1:
        endereco = str_app.text_input("Endereço", placeholder="Ex: Rua das Flores")
    with col_end2:
        numero = str_app.text_input("Número", placeholder="Ex: 123")

    col_loc1, col_loc2, col_loc3 = str_app.columns(3)
    with col_loc1:
        bairro = str_app.text_input("Bairro", placeholder="Ex: Jardim Planalto")
    with col_loc2:
        cidade = str_app.text_input("Cidade", placeholder="Ex: Parnamirim")
    with col_loc3:
        estado = str_app.text_input("Estado (UF)", placeholder="Ex: RN", max_chars=2)

    col_cep, col_pais = str_app.columns(2)
    with col_cep:
        cep = str_app.text_input("Código postal (CEP)", placeholder="Ex: 59140-000")
    with col_pais:
        str_app.text_input("País", value="Brasil", disabled=True)

    str_app.markdown("<hr>", unsafe_allow_html=True)
    str_app.markdown("##### 🏷️ Dados do imóvel")

    col1, col2 = str_app.columns(2)
    with col1:
        tipo = str_app.selectbox("Tipo de imóvel", TIPOS_IMOVEL)
        finalidade = str_app.selectbox("Finalidade", FINALIDADES_IMOVEL)
        preco = str_app.number_input("Preço (R$)", min_value=0.0, step=1000.0, format="%.2f")
    with col2:
        status = str_app.selectbox("Status", STATUS_IMOVEL)
        metragem = str_app.number_input("Metragem (m²)", min_value=0.0, step=1.0)

    str_app.markdown("<hr>", unsafe_allow_html=True)
    str_app.markdown("##### ✅ Ambientes (informe a quantidade de cada um)")

    col_a1, col_a2, col_a3, col_a4 = str_app.columns(4)
    with col_a1:
        quartos = str_app.number_input("🛏️ Quartos", min_value=0, step=1)
        qtd_suites = str_app.number_input("🛌 Suítes", min_value=0, step=1)
    with col_a2:
        qtd_banheiros = str_app.number_input("🚿 Banheiros", min_value=0, step=1)
        vagas = str_app.number_input("🚗 Vagas de garagem", min_value=0, step=1)
    with col_a3:
        qtd_cozinha = str_app.number_input("🍳 Cozinha", min_value=0, step=1)
        qtd_sala_estar = str_app.number_input("🛋️ Sala de estar", min_value=0, step=1)
    with col_a4:
        qtd_area = str_app.number_input("🌿 Área", min_value=0, step=1)
        qtd_quintal = str_app.number_input("🏡 Quintal", min_value=0, step=1)

    qtd_lavanderia = str_app.number_input("🧺 Lavanderia", min_value=0, step=1)

    str_app.markdown("<hr>", unsafe_allow_html=True)
    descricao = str_app.text_area("Descrição do imóvel", placeholder="Detalhes, diferenciais, condições...")

    fotos = str_app.file_uploader(
        "Fotos do imóvel (até 6)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True
    )
    if fotos and len(fotos) > 6:
        str_app.warning("Você selecionou mais de 6 fotos — apenas as 6 primeiras serão enviadas.")
        fotos = fotos[:6]

    if fotos:
        str_app.image([f.getvalue() for f in fotos], width=90)

    col_salvar, col_cancelar = str_app.columns(2)
    with col_salvar:
        if str_app.button("💾 Salvar imóvel", type="primary", use_container_width=True):
            if not bairro or not endereco or preco <= 0:
                str_app.error("Preencha ao menos o endereço, o bairro e o preço.")
            else:
                with str_app.spinner("Salvando imóvel e enviando fotos..."):
                    dados_imovel = {
                        "tipo_imovel": tipo,
                        "finalidade": finalidade,
                        "endereco": endereco,
                        "numero": numero,
                        "bairro": bairro,
                        "cidade": cidade,
                        "estado": estado.upper() if estado else None,
                        "pais": "Brasil",
                        "cep": cep,
                        "quartos": int(quartos) if quartos else None,
                        "vagas_garagem": int(vagas) if vagas else None,
                        "metragem": float(metragem) if metragem else None,
                        "preco": float(preco),
                        "status": status,
                        "descricao": descricao,
                        "qtd_cozinha": int(qtd_cozinha),
                        "qtd_sala_estar": int(qtd_sala_estar),
                        "qtd_area": int(qtd_area),
                        "qtd_quintal": int(qtd_quintal),
                        "qtd_banheiros": int(qtd_banheiros),
                        "qtd_suites": int(qtd_suites),
                        "qtd_lavanderia": int(qtd_lavanderia),
                    }
                    sucesso, erro = criar_imovel(cliente_id, auth_user_id, dados_imovel, fotos or [])

                if sucesso:
                    str_app.session_state["imovel_recem_salvo"] = dados_imovel
                    str_app.rerun()
                else:
                    str_app.error(f"Erro ao salvar: {erro}")
    with col_cancelar:
        if str_app.button("Cancelar", use_container_width=True):
            str_app.rerun()


def formatar_preco(valor) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def render_catalogo_imoveis(cliente: dict):
    cliente_id = cliente["id"]
    auth_user_id = cliente["auth_user_id"]

    str_app.markdown("""
        <p class="page-eyebrow">Painel do Corretor</p>
        <h1 class="page-title">Catálogo de Imóveis</h1>
        <p class="page-subtitle">Cadastre os imóveis que a Sofia vai sugerir aos seus leads.</p>
        <hr>
    """, unsafe_allow_html=True)

    if str_app.button("➕ Adicionar imóvel", type="primary"):
        modal_novo_imovel(cliente_id, auth_user_id)

    imoveis = listar_imoveis(cliente_id)

    if not imoveis:
        str_app.info("Nenhum imóvel cadastrado ainda. Clique em \"➕ Adicionar imóvel\" para começar.")
        return

    # --- BUSCA E FILTROS ---
    col_busca, col_ordenar = str_app.columns([2.5, 1.3])
    with col_busca:
        termo_busca = str_app.text_input(
            "Buscar", placeholder="🔍 Buscar por endereço, bairro, cidade ou descrição...",
            label_visibility="collapsed"
        )
    with col_ordenar:
        ordenar_por = str_app.selectbox(
            "Ordenar", ["Mais recente", "Menor preço", "Maior preço"],
            label_visibility="collapsed"
        )

    with str_app.expander("🔧 Mais filtros"):
        col_f1, col_f2, col_f3 = str_app.columns(3)
        with col_f1:
            opcoes_cidade = ["Todas"] + sorted({i["cidade"] for i in imoveis if i.get("cidade")})
            filtro_cidade = str_app.selectbox("Cidade", opcoes_cidade)
        with col_f2:
            opcoes_estado = ["Todos"] + sorted({i["estado"] for i in imoveis if i.get("estado")})
            filtro_estado = str_app.selectbox("Estado", opcoes_estado)
        with col_f3:
            opcoes_bairro = ["Todos"] + sorted({i["bairro"] for i in imoveis if i.get("bairro")})
            filtro_bairro = str_app.selectbox("Bairro", opcoes_bairro)

    # --- APLICA A BUSCA ---
    if termo_busca:
        termo_lower = termo_busca.lower()
        imoveis = [
            i for i in imoveis
            if termo_lower in (i.get("endereco") or "").lower()
            or termo_lower in (i.get("bairro") or "").lower()
            or termo_lower in (i.get("cidade") or "").lower()
            or termo_lower in (i.get("descricao") or "").lower()
        ]

    # --- APLICA OS FILTROS ---
    if filtro_cidade != "Todas":
        imoveis = [i for i in imoveis if i.get("cidade") == filtro_cidade]
    if filtro_estado != "Todos":
        imoveis = [i for i in imoveis if i.get("estado") == filtro_estado]
    if filtro_bairro != "Todos":
        imoveis = [i for i in imoveis if i.get("bairro") == filtro_bairro]

    # --- APLICA A ORDENAÇÃO ---
    if ordenar_por == "Menor preço":
        imoveis = sorted(imoveis, key=lambda i: i.get("preco") or 0)
    elif ordenar_por == "Maior preço":
        imoveis = sorted(imoveis, key=lambda i: i.get("preco") or 0, reverse=True)
    # "Mais recente" já é a ordem padrão retornada por listar_imoveis (criado_em desc)

    if not imoveis:
        str_app.warning("Nenhum imóvel encontrado com esses filtros.")
        return

    str_app.markdown("<br>", unsafe_allow_html=True)
    colunas = str_app.columns(3)

    for i, imovel in enumerate(imoveis):
        with colunas[i % 3]:
            with str_app.container(border=True):
                fotos_urls = imovel.get("fotos_urls") or []
                if fotos_urls:
                    str_app.image(fotos_urls[0], use_container_width=True)
                else:
                    str_app.markdown(
                        "<div style='background:#131316; border-radius:8px; height:140px; "
                        "display:flex; align-items:center; justify-content:center; color:#52525b;'>Sem foto</div>",
                        unsafe_allow_html=True
                    )

                cor_status = {"Disponível": "#4ade80", "Reservado": "#fb923c", "Vendido": "#f87171"}.get(imovel.get("status"), "#71717a")

                endereco_resumo = f"{imovel.get('endereco', '')}, {imovel.get('numero', '')}" if imovel.get("endereco") else ""
                cidade_estado = f"{imovel.get('cidade', '')}/{imovel.get('estado', '')}" if imovel.get("cidade") else ""

                str_app.markdown(
                    f"<p style='margin:0.6rem 0 0 0;'>"
                    f"<span style='font-weight:700; color:#fafafa;'>{imovel.get('tipo_imovel', '')} · {imovel.get('bairro', '')}</span> "
                    f"<span style='font-size:0.72rem; font-weight:700; color:#a78bfa; background:rgba(124,58,237,0.15); padding:1px 7px; border-radius:999px;'>{imovel.get('finalidade', 'Venda')}</span>"
                    f"</p>"
                    f"<p style='margin:0.1rem 0 0 0; font-size:0.78rem; color:#71717a;'>{endereco_resumo}{' · ' + cidade_estado if cidade_estado else ''}</p>"
                    f"<p style='margin:0.3rem 0 0 0; font-size:1.05rem; font-weight:700; color:#c4b5fd;'>{formatar_preco(imovel.get('preco'))}</p>"
                    f"<p style='margin:0.3rem 0 0 0; font-size:0.82rem; color:#a1a1aa;'>"
                    f"🛏️ {imovel.get('quartos') or 0} · 🛌 {imovel.get('qtd_suites') or 0} suíte(s) · 🚿 {imovel.get('qtd_banheiros') or 0} · "
                    f"🚗 {imovel.get('vagas_garagem') or 0} · 📐 {imovel.get('metragem') or '–'}m²</p>"
                    f"<p style='margin:0.4rem 0 0 0; font-size:0.78rem; font-weight:700; color:{cor_status};'>● {imovel.get('status', '')}</p>",
                    unsafe_allow_html=True
                )

                if imovel.get("descricao"):
                    with str_app.expander("Ver descrição"):
                        str_app.write(imovel["descricao"])

                novo_status = str_app.selectbox(
                    "Status", STATUS_IMOVEL,
                    index=STATUS_IMOVEL.index(imovel.get("status", "Disponível")) if imovel.get("status") in STATUS_IMOVEL else 0,
                    key=f"status_{imovel['id']}",
                    label_visibility="collapsed"
                )
                if novo_status != imovel.get("status"):
                    atualizar_status_imovel(imovel["id"], novo_status)
                    str_app.rerun()

                with str_app.popover("📣 Compartilhar", use_container_width=True):
                    render_botoes_compartilhar(montar_texto_compartilhamento(imovel))

                col_editar, col_excluir = str_app.columns(2)
                with col_editar:
                    if str_app.button("✏️ Editar", key=f"edit_{imovel['id']}", use_container_width=True):
                        modal_editar_imovel(imovel, auth_user_id)
                with col_excluir:
                    if str_app.button("🗑️ Excluir", key=f"del_{imovel['id']}", use_container_width=True):
                        excluir_imovel(imovel["id"])
                        str_app.rerun()


# =============================================================================
# FUNÇÕES — MEUS LEADS
# =============================================================================
def listar_leads(cliente_id: str):
    """Retorna todos os leads deste corretor, mais recentes primeiro."""
    try:
        res = supabase.table("leads") \
            .select("*") \
            .eq("cliente_id", cliente_id) \
            .order("id", desc=True) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao listar leads: {e}", flush=True)
        return []


def render_meus_leads(cliente: dict):
    cliente_id = cliente["id"]

    str_app.markdown("""
        <p class="page-eyebrow">Painel do Corretor</p>
        <h1 class="page-title">Meus Leads</h1>
        <p class="page-subtitle">Leads qualificados pela Sofia através do seu WhatsApp.</p>
        <hr>
    """, unsafe_allow_html=True)

    leads = listar_leads(cliente_id)

    if not leads:
        str_app.info("Nenhum lead recebido ainda. Quando alguém conversar com a Sofia pelo seu WhatsApp, aparecerá aqui.")
        return

    total = len(leads)
    qualificados = len([l for l in leads if l.get("status_qualificacao") == "Qualificado"])
    pendentes = total - qualificados

    c1, c2, c3 = str_app.columns(3)
    c1.metric("Total de leads", total)
    c2.metric("Qualificados", qualificados)
    c3.metric("Em andamento", pendentes)

    str_app.markdown("<br>", unsafe_allow_html=True)

    termo_busca_lead = str_app.text_input(
        "Buscar lead", placeholder="🔍 Buscar por nome, telefone ou bairro...",
        label_visibility="collapsed"
    )

    if termo_busca_lead:
        termo_l = termo_busca_lead.lower()
        leads = [
            l for l in leads
            if termo_l in (l.get("nome_lead") or "").lower()
            or termo_l in (l.get("telefone_lead") or "").lower()
            or termo_l in (l.get("bairro_preferido") or "").lower()
        ]

    if not leads:
        str_app.warning("Nenhum lead encontrado com esse termo.")
        return

    linhas_tabela = []
    for lead in leads:
        restricao = lead.get("restricao_cpf")
        restricao_txt = "Sim" if restricao is True else ("Não" if restricao is False else "–")

        linhas_tabela.append({
            "Nome": lead.get("nome_lead") or "Não informado",
            "Telefone": lead.get("telefone_lead") or "–",
            "Status": lead.get("status_qualificacao") or "Pendente",
            "Intenção": lead.get("intencao") or "–",
            "Bairro": lead.get("bairro_preferido") or "–",
            "Quartos": lead.get("quartos") or "–",
            "Orçamento": lead.get("orcamento") or "–",
            "Renda": lead.get("renda_mensal") or "–",
            "Restrição CPF": restricao_txt,
            "Notificado": "✅" if lead.get("notificado") else "—",
        })

    str_app.dataframe(linhas_tabela, use_container_width=True, hide_index=True)


# =============================================================================
# DASHBOARD PRINCIPAL
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

    secao = str_app.sidebar.radio(
        "Navegação",
        ["🔌 Conectar WhatsApp", "🏠 Catálogo de Imóveis", "👥 Meus Leads"],
        label_visibility="collapsed"
    )

    str_app.sidebar.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    if str_app.sidebar.button("⏻  Sair", use_container_width=True):
        fazer_logout()

    if secao == "🔌 Conectar WhatsApp":
        render_conectar_whatsapp(cliente)
    elif secao == "🏠 Catálogo de Imóveis":
        render_catalogo_imoveis(cliente)
    else:
        render_meus_leads(cliente)


# =============================================================================
# ROTEAMENTO PRINCIPAL
# =============================================================================
if str_app.session_state["cliente_atual"] is not None:
    render_dashboard()
elif str_app.session_state["tela_auth"] == "cadastro":
    render_cadastro()
else:
    render_login()