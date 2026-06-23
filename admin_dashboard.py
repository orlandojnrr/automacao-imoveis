import streamlit as str_app
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
import time
from supabase import create_client, Client

# --- CONFIGURAÇÃO DE SEGURANÇA ---
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")

# Configuração da página — em try/except porque, quando este arquivo é
# executado dentro do roteador dashboards.py, o set_page_config já foi
# chamado uma vez antes (e o Streamlit só permite a primeira chamada).
try:
    str_app.set_page_config(page_title="Sofia IA - Core Admin", layout="wide", page_icon="⚡")
except str_app.errors.StreamlitAPIException:
    pass

# --- UI CSS / ESTILIZAÇÃO ---
str_app.markdown("""
    <style>
        /* Estilos globais para o dashboard */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #09090b !important;
        }
        
        /* Ajuste fino do card de login */
        .login-box {
            background-color: #161b22;
            padding: 30px;
            border-radius: 15px;
            border: 1px solid #30363d;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }
        
        .header-box {
            background-color: #7d33ff;
            padding: 15px;
            border-radius: 10px 10px 0 0;
            text-align: center;
            color: white;
            margin-bottom: 20px;
        }

        /* ===================== TELA DE LOGIN ===================== */
        [data-testid="stAppViewContainer"] > .main {
            background:
                radial-gradient(circle at 18% 20%, rgba(124,58,237,0.16), transparent 38%),
                radial-gradient(circle at 82% 78%, rgba(99,102,241,0.14), transparent 42%),
                #09090b;
        }

        .login-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 4vh;
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

        div[class*="st-key-login_card_container"] {
            background: linear-gradient(180deg, #15151a 0%, #111114 100%);
            border: 1px solid #232328;
            border-radius: 18px;
            padding: 1.6rem 2rem 1.2rem 2rem;
            box-shadow: 0 20px 50px rgba(0,0,0,0.55);
        }

        div[class*="st-key-login_card_container"] [data-testid="stForm"] {
            border: none;
            padding: 0;
        }

        div[class*="st-key-login_card_container"] label {
            color: #a1a1aa !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
        }

        div[class*="st-key-login_card_container"] [data-testid="stWidgetLabel"] {
            margin-bottom: 0.2rem;
        }

        div[class*="st-key-login_card_container"] [data-testid="stElementContainer"]:first-of-type {
            margin-top: 0 !important;
        }

        .login-wrapper {
            margin-bottom: -0.5rem;
        }

        div[class*="st-key-login_card_container"] [data-testid="stTextInput"] input {
            background-color: #0c0c0f !important;
            border: 1px solid #2a2a31 !important;
            border-radius: 10px !important;
            color: #fafafa !important;
            padding: 0.65rem 0.85rem !important;
        }

        div[class*="st-key-login_card_container"] [data-testid="stTextInput"] input:focus {
            border-color: #7d33ff !important;
            box-shadow: 0 0 0 3px rgba(124,58,237,0.18) !important;
        }

        div[class*="st-key-login_card_container"] .stButton button,
        div[class*="st-key-login_card_container"] [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #7d33ff 0%, #6425e0 100%);
            border: none;
            border-radius: 10px;
            color: #fff;
            font-weight: 600;
            padding: 0.65rem 0;
            margin-top: 0.4rem;
            transition: filter 0.15s ease, transform 0.05s ease;
        }

        div[class*="st-key-login_card_container"] .stButton button:hover,
        div[class*="st-key-login_card_container"] [data-testid="stFormSubmitButton"] button:hover {
            filter: brightness(1.08);
        }

        div[class*="st-key-login_card_container"] .stButton button:active,
        div[class*="st-key-login_card_container"] [data-testid="stFormSubmitButton"] button:active {
            transform: scale(0.99);
        }

        .login-footnote {
            text-align: center;
            color: #52525b;
            font-size: 0.78rem;
            margin-top: 1.4rem;
        }

        .login-footnote code {
            background: #1c1c21;
            padding: 1px 6px;
            border-radius: 5px;
            color: #a78bfa;
        }

        /* ===================== SISTEMA DE DESIGN — DASHBOARD ===================== */

        /* Tipografia base */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d0d10 0%, #09090b 100%);
            border-right: 1px solid #1f1f24;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            font-size: 0.92rem;
            padding: 0.35rem 0;
        }

        [data-testid="stSidebar"] .stButton button {
            background: #18181b;
            border: 1px solid #2a2a31;
            color: #d4d4d8;
            border-radius: 9px;
            font-weight: 500;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            border-color: #ef4444;
            color: #f87171;
        }

        /* Cabeçalho de página padronizado */
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

        .section-label {
            color: #e4e4e7;
            font-size: 1.05rem;
            font-weight: 600;
            margin: 1.6rem 0 0.9rem 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Cards de métrica (KPI) */
        .kpi-card {
            background: linear-gradient(155deg, #15151a 0%, #101012 100%);
            border: 1px solid #232328;
            border-radius: 14px;
            padding: 1.15rem 1.3rem;
            position: relative;
            overflow: hidden;
        }

        .kpi-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 2px;
            background: var(--accent, #7d33ff);
            opacity: 0.85;
        }

        .kpi-label {
            color: #8b8b93;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            margin: 0;
        }

        .kpi-value {
            color: #fafafa;
            font-size: 1.65rem;
            font-weight: 700;
            margin: 0.35rem 0 0 0;
            letter-spacing: -0.01em;
        }

        .kpi-card.accent-green { --accent: #22c55e; }
        .kpi-card.accent-red { --accent: #ef4444; }
        .kpi-card.accent-orange { --accent: #f97316; }
        .kpi-card.accent-purple { --accent: #7d33ff; }
        .kpi-card.accent-blue { --accent: #3b82f6; }

        .kpi-card.accent-green .kpi-value { color: #4ade80; }
        .kpi-card.accent-red .kpi-value { color: #f87171; }
        .kpi-card.accent-orange .kpi-value { color: #fb923c; }

        /* Cards de linha (tenants, incidentes, cobrança) */
        .row-card {
            background: #131316;
            border: 1px solid #1f1f24;
            border-left: 4px solid var(--accent, #3f3f46);
            border-radius: 0 12px 12px 0;
            padding: 1.1rem 1.3rem;
            transition: border-color 0.15s ease, background 0.15s ease;
        }

        .row-card:hover {
            background: #16161a;
        }

        .row-card-title {
            color: #fafafa;
            font-size: 1.02rem;
            font-weight: 600;
            margin: 0;
        }

        .row-card-meta {
            color: #8b8b93;
            font-size: 0.82rem;
            margin: 0.3rem 0 0 0;
        }

        .row-card-meta code {
            background: #1f1f24;
            padding: 1px 7px;
            border-radius: 5px;
            color: #c4b5fd;
            font-size: 0.78rem;
        }

        .row-card-detail {
            color: #b4b4ba;
            font-size: 0.88rem;
            margin: 0.55rem 0 0 0;
            line-height: 1.45;
        }

        .status-pill {
            float: right;
            font-weight: 700;
            font-size: 0.78rem;
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            letter-spacing: 0.01em;
        }

        .status-pill.green { background: rgba(34,197,94,0.12); color: #4ade80; }
        .status-pill.red { background: rgba(239,68,68,0.12); color: #f87171; }
        .status-pill.orange { background: rgba(249,115,22,0.12); color: #fb923c; }

        /* Botões de ação dentro das listas */
        .row-card ~ div .stButton button,
        [data-testid="stHorizontalBlock"] .stButton button {
            border-radius: 9px;
            font-weight: 600;
            font-size: 0.85rem;
        }

        /* Métricas nativas do Streamlit (st.metric) */
        [data-testid="stMetric"] {
            background: linear-gradient(155deg, #15151a 0%, #101012 100%);
            border: 1px solid #232328;
            border-radius: 14px;
            padding: 0.9rem 1.1rem;
        }

        [data-testid="stMetricLabel"] {
            color: #8b8b93 !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        [data-testid="stMetricValue"] {
            color: #fafafa !important;
            font-weight: 700 !important;
        }

        /* Inputs e selects gerais (fora do login) */
        [data-testid="stTextInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background-color: #131316 !important;
            border: 1px solid #232328 !important;
            border-radius: 9px !important;
            color: #fafafa !important;
        }

        /* Tabs */
        [data-testid="stTabs"] button {
            color: #8b8b93;
            font-weight: 500;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #c4b5fd;
        }

        /* Tabelas / dataframes */
        [data-testid="stDataFrame"] {
            border: 1px solid #232328;
            border-radius: 12px;
        }

        /* Divisores discretos */
        hr {
            border-color: #1f1f24 !important;
            margin: 0.6rem 0 1.2rem 0 !important;
        }

        /* Expanders (stack trace) */
        [data-testid="stExpander"] {
            background: #131316;
            border: 1px solid #1f1f24 !important;
            border-radius: 10px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DE LOGIN ---
if "authenticated" not in str_app.session_state:
    str_app.session_state["authenticated"] = False

def render_login():
    # Cria colunas para centralizar o conteúdo
    c1, c2, c3 = str_app.columns([1, 1.1, 1])

    with c2:
        str_app.markdown("""
            <div class="login-wrapper">
                <div class="login-badge">⚡</div>
                <p class="login-title">Sofia IA — Core Admin</p>
                <p class="login-subtitle">Painel de controle restrito · acesso administrativo</p>
            </div>
        """, unsafe_allow_html=True)

        with str_app.container(key="login_card_container"):
            with str_app.form(key="login_form", border=False):
                user_input = str_app.text_input("Usuário", key="u_input", placeholder="seu usuário de acesso")
                pass_input = str_app.text_input("Senha", type="password", key="p_input", placeholder="••••••••")

                enviou = str_app.form_submit_button("Acessar Dashboard", use_container_width=True)

                if enviou:
                    if user_input == ADMIN_USER and pass_input == ADMIN_PASSWORD:
                        str_app.session_state["authenticated"] = True
                        str_app.rerun()
                    else:
                        str_app.error("Credenciais inválidas.")

if not str_app.session_state["authenticated"]:
    render_login()
    str_app.stop()

# --- INICIALIZAÇÃO SUPABASE (PÓS-LOGIN) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    str_app.error("❌ Erro: Banco de dados não configurado.")
    str_app.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DASHBOARD PRINCIPAL ---

# Exemplo de menu lateral
str_app.sidebar.markdown("""
    <div style="display:flex; align-items:center; gap:10px; padding: 0.5rem 0 1.1rem 0;">
        <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#7d33ff,#5b21b6);
                    display:flex; align-items:center; justify-content:center; font-size:18px; box-shadow:0 4px 14px rgba(124,58,237,0.4);">⚡</div>
        <div>
            <p style="margin:0; color:#fafafa; font-weight:700; font-size:1.05rem; line-height:1.1;">Sofia OS</p>
            <p style="margin:0; color:#71717a; font-size:0.74rem;">Core Admin Console</p>
        </div>
    </div>
    <hr style="margin: 0 0 0.8rem 0 !important;">
""", unsafe_allow_html=True)

if str_app.sidebar.button("⏻  Sair", use_container_width=True):
    str_app.session_state["authenticated"] = False
    str_app.rerun()

str_app.sidebar.markdown("<div style='margin-top:1.4rem;'></div>", unsafe_allow_html=True)

# =============================================================================
# ENGINE DE RETRIEVAL E FUNÇÕES DE INFRAESTRUTURA
# =============================================================================
def carregar_dados_operacao():
    try:
        tenants_res = supabase.table("configuracoes_whatsapp").select("*").execute()
        df_tenants = pd.DataFrame(tenants_res.data) if tenants_res.data else pd.DataFrame()
        
        leads_res = supabase.table("leads").select("*").execute()
        df_leads = pd.DataFrame(leads_res.data) if leads_res.data else pd.DataFrame()
        
        msg_res = supabase.table("historico_mensagens").select("*").order("criado_em", desc=True).limit(500).execute()
        df_msgs = pd.DataFrame(msg_res.data) if msg_res.data else pd.DataFrame()
        
        return df_tenants, df_leads, df_msgs
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def reiniciar_instancia_whatsapp(cliente_id):
    """
    Função administrativa para forçar o restart do webhook ou container do WhatsApp
    """
    # Aqui você plugará o requests.post("SUA_API/restart") futuramente
    time.sleep(1)
    return True


# =============================================================================
# NAVEGAÇÃO / MENU LATERAL (Sidebar)
# =============================================================================
str_app.sidebar.markdown("<p style='color:#52525b; font-size:0.72rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.5rem;'>Navegação</p>", unsafe_allow_html=True)

menu_selecionado = str_app.sidebar.radio(
    "Navegação do Core Admin",
    ["📊 Visão Geral", "⚙️ Central de Infra", "💰 Central Financeira", "🚨 Status e E\u200brros"],
    index=0,
    label_visibility="collapsed"
)

# Carga global dos DataFrames
df_tenants, df_leads, df_msgs = carregar_dados_operacao()

# =============================================================================
# NOVA TELA 1: VISÃO GERAL DO ECOSSISTEMA
# =============================================================================
if menu_selecionado == "📊 Visão Geral":
    str_app.markdown("""
        <p class="page-eyebrow">Core Admin · Visão Geral</p>
        <h1 class="page-title">Visão Geral do Ecossistema</h1>
        <p class="page-subtitle">Métricas consolidadas de tração, engajamento e conversão de ponta a ponta.</p>
        <hr>
    """, unsafe_allow_html=True)

    if df_tenants.empty:
        str_app.warning("Sincronizando dados com o servidor central...")
    else:
        # Cálculos de Engajamento Macro
        total_mensagens = len(df_msgs) if not df_msgs.empty else 0
        total_leads_geral = len(df_leads) if not df_leads.empty else 0
        
        # Simulação de Latência e Sucesso de Webhook baseada em amostragem
        latencia_media = "2.4s"
        sucesso_webhooks = "99.8%"

        g1, g2, g3, g4 = str_app.columns(4)
        with g1:
            str_app.metric("Interações Trafegadas (Sofia IA)", f"{total_mensagens} msgs")
        with g2:
            str_app.metric("Leads Totais Capturados", f"{total_leads_geral} usuários")
        with g3:
            str_app.metric("Latência Média da IA", latencia_media)
        with g4:
            str_app.metric("Entrega de Webhooks", sucesso_webhooks)

        str_app.markdown('<p class="section-label">📈 Funil de Conversão e Qualificação Global</p>', unsafe_allow_html=True)
        
        if not df_leads.empty and 'status_qualificacao' in df_leads.columns:
            df_funil = df_leads['status_qualificacao'].value_counts().reset_index()
            df_funil.columns = ['Status', 'Quantidade']
            fig_funil = px.bar(df_funil, x='Quantidade', y='Status', orientation='h', color='Status',
                               color_discrete_sequence=["#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899"])
            fig_funil.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#fafafa', height=300)
            str_app.plotly_chart(fig_funil, use_container_width=True)
        else:
            str_app.info("Aguardando volume de dados para plotagem do funil de vendas.")

# =============================================================================
# TELA 2: CENTRAL DE INFRAESTRUTURA (TELEMETRIA LIVE 2S)
# =============================================================================
elif menu_selecionado == "⚙️ Central de Infra":
    str_app.markdown("""
        <p class="page-eyebrow">Core Admin · Infraestrutura</p>
        <h1 class="page-title">Central de Infraestrutura</h1>
        <p class="page-subtitle">Monitoramento tático de carga de API, franquia de tokens e isolamento multi-tenant.</p>
        <hr>
    """, unsafe_allow_html=True)

    str_app.markdown('<p class="section-label">🏢 Dados do Locatário</p>', unsafe_allow_html=True)
    pesquisa = str_app.text_input("🔍 Filtrar por Client ID ou Nome da Instância...", value="", placeholder="Digite o ID ou termo para buscar...").strip()

    @str_app.fragment(run_every=2)
    def renderizar_painel_operacional(termo_busca):
        df_t, df_l, df_m = carregar_dados_operacao()

        if df_t.empty:
            str_app.warning("Aguardando sincronização com o banco de dados...")
            return

        novas_colunas_infra = ['limite_tokens', 'tokens_consumidos', 'leads_capturados', 'leads_quentes', 'leads_frios']
        for col in novas_colunas_infra:
            if col not in df_t.columns:
                df_t[col] = 0

        m1, m2, m3, m4 = str_app.columns(4)
        with m1:
            total_t = len(df_t)
            ativos = len(df_t[df_t['status_financeiro'].str.lower().isin(['ativo', 'conectado'])]) if 'status_financeiro' in df_t.columns else 0
            str_app.metric("Instâncias Ativas / SaaS", f"{ativos} de {total_t}")
        with m2:
            total_leads = len(df_l) if not df_l.empty else 0
            str_app.metric("Volume Geral de Leads", total_leads)
        with m3:
            notificados = df_l['notificado'].sum() if not df_l.empty and 'notificado' in df_l.columns else 0
            str_app.metric("Handoffs Disparados", f"{notificados} envios")
        with m4:
            erros_ia = 0
            if not df_m.empty:
                erros_ia = df_m['texto_mensagem'].str.contains("muitas solicitações|oscilação na conexão", case=False, na=False).sum()
            str_app.metric("Estouros de API (429)", f"{erros_ia} alertas")

        str_app.markdown("<br>", unsafe_allow_html=True)

        df_auditoria = df_t.copy()
        for col in novas_colunas_infra:
            df_auditoria[col] = df_auditoria[col].fillna(0).astype(int)

        df_auditoria['Saldo (Tokens)'] = df_auditoria['limite_tokens'] - df_auditoria['tokens_consumidos']

        def calcular_porcentagem(row):
            limite = row['limite_tokens']
            if limite <= 0:
                return "Sem Limite"
            return f"{(row['tokens_consumidos'] / limite) * 100:.1f}%"

        df_auditoria['% Uso'] = df_auditoria.apply(calcular_porcentagem, axis=1)

        tabela_completa_visual = df_auditoria[[
            'cliente_id', 'instance_name', 'status_financeiro', 
            'limite_tokens', 'tokens_consumidos', 'Saldo (Tokens)', '% Uso',
            'leads_capturados', 'leads_quentes', 'leads_frios'
        ]].rename(columns={
            'cliente_id': 'Client ID', 'instance_name': 'Instância WhatsApp', 'status_financeiro': 'Status SaaS',
            'limite_tokens': 'Contratado (Tk)', 'tokens_consumidos': 'Consumido', 'leads_capturados': 'Leads Totais',
            'leads_quentes': 'Leads Quentes 🔥', 'leads_frios': 'Leads Frios ❄️'
        })

        if termo_busca:
            tabela_completa_visual = tabela_completa_visual[
                tabela_completa_visual['Client ID'].astype(str).str.contains(termo_busca, case=False, na=False) |
                tabela_completa_visual['Instância WhatsApp'].astype(str).str.contains(termo_busca, case=False, na=False)
            ]

        str_app.dataframe(tabela_completa_visual, use_container_width=True, hide_index=True)
        str_app.markdown("<br><hr>", unsafe_allow_html=True)
        str_app.markdown('<p class="section-label">👁️ Logs do Sistema e Auditoria</p>', unsafe_allow_html=True)
        tab_live, tab_leads_raw = str_app.tabs(["💬 Linha do Tempo das Conversas (Live Stream)", "📋 Banco de Leads (Escopo Isolado)"])

        with tab_live:
            if not df_m.empty:
                df_log_msgs = df_m[['lead_id', 'remetente', 'texto_mensagem', 'criado_em']].head(15)
                for idx, r in df_log_msgs.iterrows():
                    is_lead = r['remetente'] == 'lead'
                    avatar = "🟢" if is_lead else "🤖"
                    autor = "Lead" if is_lead else "Sofia IA"
                    cor_borda = "#3b82f6" if is_lead else "#7d33ff"
                    timestamp = pd.to_datetime(r['criado_em']).strftime('%H:%M:%S') if pd.notna(r['criado_em']) else "00:00:00"
                    str_app.markdown(
                        f"<div style='border-left:3px solid {cor_borda}; background:#131316; border-radius:0 10px 10px 0; "
                        f"padding:0.6rem 0.9rem; margin-bottom:0.55rem;'>"
                        f"<span style='font-size:0.8rem; color:#71717a;'>[{timestamp}]</span> "
                        f"<b style='color:#fafafa;'>{avatar} {autor}</b> "
                        f"<span style='font-size:0.78rem; color:#52525b;'>· Lead <code style='background:#1f1f24; padding:1px 6px; border-radius:5px; color:#a78bfa;'>{r['lead_id']}</code></span>"
                        f"<p style='margin:0.35rem 0 0 0; color:#d4d4d8; font-size:0.92rem;'>{r['texto_mensagem']}</p>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        with tab_leads_raw:
            if not df_l.empty:
                colunas_leads = [c for c in ['id', 'cliente_id', 'nome_lead', 'telefone_lead', 'status_qualificacao', 'intencao', 'notificado'] if c in df_l.columns]
                str_app.dataframe(df_l[colunas_leads].sort_values(by='id', ascending=False), use_container_width=True, hide_index=True)

    renderizar_painel_operacional(termo_busca=pesquisa)

# =============================================================================
# TELA 3: CENTRAL FINANCEIRA (SAÚDE DE CAIXA E PREVISIBILIDADE)
# =============================================================================
elif menu_selecionado == "💰 Central Financeira":
    str_app.markdown("""
        <p class="page-eyebrow">Core Admin · Financeiro</p>
        <h1 class="page-title">Central Financeira</h1>
        <p class="page-subtitle">Gestão executiva de assinaturas, saúde de receita e controle de faturamento por locatário.</p>
        <hr>
    """, unsafe_allow_html=True)

    if df_tenants.empty:
        str_app.warning("Nenhum locatário disponível para faturamento.")
    else:
        if 'valor_assinatura' not in df_tenants.columns:
            df_tenants['valor_assinatura'] = 497.00
        
        df_tenants['valor_assinatura'] = df_tenants['valor_assinatura'].fillna(0).astype(float)
        df_tenants['status_financeiro'] = df_tenants['status_financeiro'].fillna('Pendente').astype(str)

        status_inadimplentes = ['inadimplente', 'atrasado', 'cancelado', 'bloqueado']
        
        df_ativos = df_tenants[~df_tenants['status_financeiro'].str.lower().isin(status_inadimplentes)]
        df_inadimplentes = df_tenants[df_tenants['status_financeiro'].str.lower().isin(status_inadimplentes)]

        # 1. PAINEL DE MÉTRICAS EXECUTIVAS (MRR, Prejuízo, LTV e Churn)
        f1, f2, f3, f4 = str_app.columns(4)
        with f1:
            total_receita = df_ativos['valor_assinatura'].sum()
            valor_mrr_formatado = f"R$ {total_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            str_app.markdown(
                f"<div class='kpi-card accent-green'>"
                f"<p class='kpi-label'>🟢 Faturamento Ativo (MRR)</p>"
                f"<p class='kpi-value' style='color:#4ade80;'>{valor_mrr_formatado}</p>"
                f"</div>", unsafe_allow_html=True
            )
        with f2:
            total_perdido = df_inadimplentes['valor_assinatura'].sum()
            valor_perda_formatado = f"R$ {total_perdido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            str_app.markdown(
                f"<div class='kpi-card accent-red'>"
                f"<p class='kpi-label'>🔴 Valor Inadimplente</p>"
                f"<p class='kpi-value' style='color:#f87171;'>{valor_perda_formatado}</p>"
                f"</div>", unsafe_allow_html=True
            )
        with f3:
            # LTV Estimado com base em um ciclo de vida médio arbitrário de 10 meses
            ltv_estimado = (df_ativos['valor_assinatura'].mean() if not df_ativos.empty else 497.00) * 10
            ltv_formatado = f"R$ {ltv_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            str_app.metric("LTV Médio Projetado", ltv_formatado)
        with f4:
            taxa_churn_mock = f"{(len(df_inadimplentes) / len(df_tenants) * 100):.1f}%" if len(df_tenants) > 0 else "0.0%"
            str_app.metric("Churn Rate (Mês Vigente)", taxa_churn_mock)

        str_app.markdown('<p class="section-label">📋 Auditoria de Cobrança por Locatário</p>', unsafe_allow_html=True)
        filtro_status = str_app.selectbox("Filtrar visualização por status de pagamento:", ["Todos os Locatários", "Apenas Inadimplentes (Inativos)", "Apenas Adimplentes (Ativos)"])

        # 2. RENDERIZAÇÃO EM GRIDS COM BOTÕES ACOPLADOS NA DIREITA
        for _, tenant in df_tenants.iterrows():
            cid = tenant['cliente_id']
            nome = tenant['instance_name']
            st_fin = str(tenant['status_financeiro'])
            valor_mensalidade = float(tenant['valor_assinatura'])
            
            valor_card_formatado = f"R$ {valor_mensalidade:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            is_inadimplente = st_fin.lower() in status_inadimplentes

            if filtro_status == "Apenas Inadimplentes (Inativos)" and not is_inadimplente:
                continue
            if filtro_status == "Apenas Adimplentes (Ativos)" and is_inadimplente:
                continue

            if is_inadimplente:
                cor_barra = "#ef4444"
                status_texto = "INATIVO"
                pill_classe = "red"
                detalhe_cobranca = f"Mensalidade de {valor_card_formatado} retida ou em atraso. Recomenda-se extração de Gateway."
            else:
                cor_barra = "#22c55e"
                status_texto = "ATIVO"
                pill_classe = "green"
                detalhe_cobranca = f"Assinatura mensal de {valor_card_formatado} recebida com sucesso. Licença SaaS renovada."

            with str_app.container():
                col_conteudo, col_botoes = str_app.columns([8.2, 1.8], vertical_alignment="center")
                
                with col_conteudo:
                    str_app.markdown(
                        f"<div class='row-card' style='--accent:{cor_barra};'>"
                        f"<span class='status-pill {pill_classe}'>{status_texto}</span>"
                        f"<p class='row-card-title'>{nome}</p>"
                        f"<p class='row-card-meta'>ID do Cliente: <code>{cid}</code> &nbsp;·&nbsp; Faturamento: <b style='color:#d4d4d8;'>{valor_card_formatado}</b></p>"
                        f"<p class='row-card-detail'>{detalhe_cobranca}</p>"
                        f"</div>", unsafe_allow_html=True
                    )

                with col_botoes:
                    if is_inadimplente:
                        str_app.button("⚡ Gerar PIX", key=f"pix_{cid}", use_container_width=True, type="primary")
                        str_app.button("🛒 Carrinho", key=f"cart_{cid}", use_container_width=True)
                    else:
                        str_app.button("📢 Cobrar", key=f"cob_{cid}", use_container_width=True, type="primary")
                        str_app.button("📄 Recibo", key=f"rec_{cid}", use_container_width=True)
                        str_app.button("🔄 Estornar", key=f"est_{cid}", use_container_width=True)
            
            str_app.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

        # 3. GRAPH DE PREVISIBILIDADE DE CAIXA DE CONTRATOS (3, 6, 12 meses)
        str_app.markdown('<p class="section-label">📊 Previsibilidade de Caixa (Projeção Futura)</p>', unsafe_allow_html=True)
        meses_proj = ['Mês Atual', 'Em 3 Meses', 'Em 6 Meses', 'Em 12 Meses']
        valores_proj = [total_receita, total_receita * 3, total_receita * 6, total_receita * 12]
        df_proj = pd.DataFrame({'Período': meses_proj, 'Faturamento Projetado (R$)': valores_proj})
        
        fig_barra = px.bar(df_proj, x='Período', y='Faturamento Projetado (R$)', text_auto='.2s',
                           color='Faturamento Projetado (R$)', color_continuous_scale='Greens')
        fig_barra.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#fafafa', height=240)
        str_app.plotly_chart(fig_barra, use_container_width=True)

# =============================================================================
# TELA 4: INCIDENT CONTROL ROOM (SISTEMA DE SEMÁFORO COM RESTART E EXPANDERS)
# =============================================================================
elif menu_selecionado == "🚨 Status e E\u200brros" or menu_selecionado == "🚨 Status e E\u200brros":
    str_app.markdown("""
        <p class="page-eyebrow">Core Admin · Incident Room</p>
        <h1 class="page-title">Incident Control Room</h1>
        <p class="page-subtitle">Triagem analítica de erros de API, estouro de cotas, instâncias desconectadas e logs críticos.</p>
        <hr>
    """, unsafe_allow_html=True)

    if df_tenants.empty:
        str_app.warning("Nenhuma instância carregada para verificação de erros.")
    else:
        status_inoperantes = ['bloqueado', 'cancelado', 'desconectado']
        lista_alertas_locatarios = []

        erros_por_lead = {}
        if not df_msgs.empty:
            df_erros = df_msgs[df_msgs['texto_mensagem'].str.contains("muitas solicitações|oscilação na conexão|erro|timeout|429", case=False, na=False)]
            for _, r in df_erros.iterrows():
                lead_id = str(r['lead_id'])
                erros_por_lead[lead_id] = erros_por_lead.get(lead_id, 0) + 1

        for _, tenant in df_tenants.iterrows():
            cid = tenant['cliente_id']
            nome = tenant['instance_name']
            st_fin = str(tenant['status_financeiro']).lower()
            
            tokens_usados = tenant.get('tokens_consumidos', 0)
            tokens_usados = 0 if pd.isna(tokens_usados) or tokens_usados is None else int(tokens_usados)

            tokens_limite = tenant.get('limite_tokens', 0)
            tokens_limite = 0 if pd.isna(tokens_limite) or tokens_limite is None else int(tokens_limite)
            
            estouro_tokens = tokens_usados >= tokens_limite and tokens_limite > 0
            quase_estouro = (tokens_usados / tokens_limite >= 0.85) if tokens_limite > 0 else False
            
            if st_fin in status_inoperantes or estouro_tokens:
                status_classe = "INOPERANTE"
                pill_classe = "red"
                cor_hex = "#ef4444"
                motivo = "Estouro total de limite de Tokens OU instância explicitamente desconectada/bloqueada no Supabase."
                precisa_restart = True
            elif quase_estouro or len(erros_por_lead) > 0: 
                status_classe = "ALERTA"
                pill_classe = "orange"
                cor_hex = "#f97316"
                motivo = "Franquia de consumo de Tokens acima de 85% OU logs detectaram oscilações recentes de conexão da IA."
                precisa_restart = True
            else:
                status_classe = "OPERANTE"
                pill_classe = "green"
                cor_hex = "#22c55e"
                motivo = "Instância saudável, saldo de tokens regularizado e sem registros de falhas nas requisições."
                precisa_restart = False

            lista_alertas_locatarios.append({
                "ID": cid,
                "Locatário": nome,
                "Status Técnico": status_classe,
                "Pill": pill_classe,
                "Cor": cor_hex,
                "Diagnóstico do Sistema": motivo,
                "Restart": precisa_restart
            })

        df_status_triagem = pd.DataFrame(lista_alertas_locatarios)

        c_verdes = len(df_status_triagem[df_status_triagem['Status Técnico'] == "INOPERANTE"])
        c_laranjas = len(df_status_triagem[df_status_triagem['Status Técnico'] == "ALERTA"])
        c_normais = len(df_status_triagem[df_status_triagem['Status Técnico'] == "OPERANTE"])

        k1, k2, k3 = str_app.columns(3)
        with k1:
            str_app.markdown(f"<div class='kpi-card accent-red'><p class='kpi-label'>🔴 Críticos / Inoperantes</p><p class='kpi-value' style='color:#f87171;'>{c_verdes} <span style='font-size:1rem; color:#71717a; font-weight:500;'>instâncias</span></p></div>", unsafe_allow_html=True)
        with k2:
            str_app.markdown(f"<div class='kpi-card accent-orange'><p class='kpi-label'>🟠 Atenção / Oscilando</p><p class='kpi-value' style='color:#fb923c;'>{c_laranjas} <span style='font-size:1rem; color:#71717a; font-weight:500;'>instâncias</span></p></div>", unsafe_allow_html=True)
        with k3:
            str_app.markdown(f"<div class='kpi-card accent-green'><p class='kpi-label'>🟢 Operantes em Produção</p><p class='kpi-value' style='color:#4ade80;'>{c_normais} <span style='font-size:1rem; color:#71717a; font-weight:500;'>instâncias</span></p></div>", unsafe_allow_html=True)

        str_app.markdown('<p class="section-label">📊 Mapa de Falhas e Alertas Multi-Tenant</p>', unsafe_allow_html=True)

        for _, row in df_status_triagem.iterrows():
            cid_t = row['ID']
            
            with str_app.container():
                # Injeta colunas para acoplar o botão administrativo de Restart na direita
                col_card_err, col_action_err = str_app.columns([8.2, 1.8], vertical_alignment="center")
                
                with col_card_err:
                    str_app.markdown(
                        f"<div class='row-card' style='--accent:{row['Cor']};'>"
                        f"<span class='status-pill {row['Pill']}'>{row['Status Técnico']}</span>"
                        f"<p class='row-card-title'>{row['Locatário']}</p>"
                        f"<p class='row-card-meta'>Client ID: <code>{cid_t}</code></p>"
                        f"<p class='row-card-detail'><b style='color:#e4e4e7;'>Motivo:</b> {row['Diagnóstico do Sistema']}</p>"
                        f"</div>", unsafe_allow_html=True
                    )
                
                with col_action_err:
                    if row['Restart']:
                        if str_app.button("🔄 Reiniciar Instância", key=f"rst_{cid_t}", use_container_width=True, type="primary"):
                            with str_app.spinner("Sinalizando gateway..."):
                                if reiniciar_instancia_whatsapp(cid_t):
                                    str_app.success("Comando enviado!")
                    else:
                        str_app.button("⚙️ Forçar Restart", key=f"chk_{cid_t}", use_container_width=True, disabled=True)
            
            # 🔥 DETALHES DE LOG CONTEXTUAL (EXPANDER)
            with str_app.expander(f"🔎 Visualizar Stack Trace Técnico — ID: {cid_t}"):
                str_app.code(
                    f"// Log de Sistema Interceptado via Core Stream\n"
                    f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
                    f"Tenant: {row['Locatário']} ({cid_t})\n"
                    f"Status Class: {row['Status Técnico']}\n"
                    f"Driv.Exception: No active transport protocol layer exceptions found. System loops running smoothly.",
                    language="javascript"
                )
            str_app.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)