import streamlit as str_app
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega chaves de ambiente
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    str_app.error("❌ Variáveis de ambiente do Supabase não configuradas!")
    str_app.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuração da página do Streamlit
str_app.set_page_config(page_title="Sofia IA - Central Admin", layout="wide", page_icon="⚡")

str_app.title("⚡ Central de Comando SaaS — Sofia IA Core v3.0")
str_app.markdown("---")

# =============================================================================
# ENGINE DE CARREGAMENTO E SINCRO DE DADOS
# =============================================================================
@str_app.cache_data(ttl=15)  # Cache curto (15s) para monitoramento dinâmico
def carregar_dados_sistema():
    # 1. Puxa Tenants cadastrados
    tenants_res = supabase.table("configuracoes_whatsapp").select("*").execute()
    df_tenants = pd.DataFrame(tenants_res.data) if tenants_res.data else pd.DataFrame()
    
    # 2. Puxa Leads coletando todos os metadados novos
    leads_res = supabase.table("leads").select("*").execute()
    df_leads = pd.DataFrame(leads_res.data) if leads_res.data else pd.DataFrame()
    
    # 3. Puxa Histórico de Mensagens Recentes (Amostragem de auditoria)
    msg_res = supabase.table("historico_mensagens").select("*").order("criado_em", desc=True).limit(400).execute()
    df_msgs = pd.DataFrame(msg_res.data) if msg_res.data else pd.DataFrame()
    
    return df_tenants, df_leads, df_msgs

df_tenants, df_leads, df_msgs = carregar_dados_sistema()

if df_tenants.empty:
    str_app.warning("⚠️ Base de dados limpa ou sem instâncias ativas no Supabase.")
    str_app.stop()

# Converte datas para datetime nativo do pandas para cálculos temporais consistentes
if not df_leads.empty and 'ultima_interacao' in df_leads.columns:
    df_leads['ultima_interacao'] = pd.to_datetime(df_leads['ultima_interacao'], errors='coerce')
if not df_msgs.empty and 'criado_em' in df_msgs.columns:
    df_msgs['criado_em'] = pd.to_datetime(df_msgs['criado_em'], errors='coerce')

# =============================================================================
# BLOCO 1: TELEMETRIA EXECUTIVA (CARDS)
# =============================================================================
str_app.subheader("📊 Saúde da Operação SaaS")
m1, m2, m3, m4 = str_app.columns(4)

with m1:
    total_t = len(df_tenants)
    ativos = len(df_tenants[df_tenants['status_financeiro'].str.lower().isin(['ativo', 'conectado'])]) if 'status_financeiro' in df_tenants.columns else 0
    str_app.metric("Tenants Operacionais", f"{ativos} / {total_t}", help="Instâncias que não caíram no bloco de inadimplência.")

with m2:
    total_leads = len(df_leads) if not df_leads.empty else 0
    str_app.metric("Leads Totais Capturados", total_leads)

with m3:
    if not df_leads.empty and 'status_qualificacao' in df_leads.columns:
        qualificados = len(df_leads[df_leads['status_qualificacao'] == 'Qualificado'])
        taxa = (qualificados / total_leads * 100) if total_leads > 0 else 0
        str_app.metric("Leads Quentes (Handoff)", qualificados, f"{taxa:.1f}% Conversão")
    else:
        str_app.metric("Leads Quentes (Handoff)", 0)

with m4:
    # Captura oscilações mapeando as respostas tratadas no main.py
    erros_ia = 0
    if not df_msgs.empty:
        # Conta frases de fallback injetadas pelo main.py quando a API estoura ou cai
        erros_ia = df_msgs['texto_mensagem'].str.contains("muitas solicitações|oscilação na conexão", case=False, na=False).sum()
    str_app.metric("Alertas / Estouro API Gemini", f"{erros_ia} eventos", delta="- Crítico" if erros_ia > 5 else "Estável", delta_color="inverse")

str_app.markdown("---")

# =============================================================================
# BLOCO 2: ENGENHARIA DE PROMPT E RAIO-X RECIPIENTE
# =============================================================================
str_app.subheader("🛠️ Engenharia de Conversão e Carga")
col_graf_1, col_graf_2 = str_app.columns(2)

with col_graf_1:
    str_app.markdown("#### 🔍 Funil Clínico de Coleta (Onde os leads desistem?)")
    if not df_leads.empty:
        # Mapeia as exatas chaves injetadas e parseadas por Regex no seu main.py
        mapeamento_campos = {
            "1. Intenção": df_leads['intencao'].notna().sum() if 'intencao' in df_leads.columns else 0,
            "2. Bairro": df_leads['bairro_preferido'].notna().sum() if 'bairro_preferido' in df_leads.columns else 0,
            "3. Quartos": df_leads['quartos'].notna().sum() if 'quartos' in df_leads.columns else 0,
            "4. Orçamento": df_leads['orcamento'].notna().sum() if 'orcamento' in df_leads.columns else 0,
            "5. Renda": df_leads['renda_mensal'].notna().sum() if 'renda_mensal' in df_leads.columns else 0,
            "6. CPF (Sem Restrição)": (df_leads['restricao_cpf'] == False).sum() if 'restricao_cpf' in df_leads.columns else 0,
            "7. CPF (Com Restrição)": (df_leads['restricao_cpf'] == True).sum() if 'restricao_cpf' in df_leads.columns else 0,
        }
        
        df_funil_dados = pd.DataFrame(list(mapeamento_campos.items()), columns=['Etapa do Perfil', 'Volume Coletado'])
        df_funil_dados = df_funil_dados.sort_values(by='Volume Coletado', ascending=False)
        
        fig_f = px.funnel(df_funil_dados, x='Volume Coletado', y='Etapa do Perfil', color_discrete_sequence=px.colors.sequential.YlOrRd_r)
        str_app.plotly_chart(fig_f, use_container_width=True)
    else:
        str_app.info("Insira dados de leads para projetar o funil.")

with col_graf_2:
    str_app.markdown("#### ⚡ Carga Ativa por Imobiliária (Consumo do Free Tier)")
    if not df_leads.empty and 'cliente_id' in df_leads.columns:
        ranking_tenant = df_leads.groupby('cliente_id').size().reset_index(name='Volume de Leads')
        fig_b = px.bar(ranking_tenant, x='cliente_id', y='Volume de Leads', color='Volume de Leads',
                       title="Controle de Ingestão de Leads por Client ID", color_continuous_scale='Turbo')
        str_app.plotly_chart(fig_b, use_container_width=True)
    else:
        str_app.info("Sem tráfego de leads mapeado para geração do ranking.")

str_app.markdown("---")

# =============================================================================
# BLOCO 3: GESTÃO MULTI-TENANT E AUDITORIA DE RESPOSTAS
# =============================================================================
str_app.subheader("👁️ Monitoramento Tático e Logs")

t_mensagens, t_tenants, t_leads = str_app.tabs(["💬 Linha do Tempo das Conversas", "🏢 Hub de Tenants (Controle SaaS)", "📋 Inventário Base de Leads"])

with t_mensagens:
    str_app.markdown("#### Últimas Interações (Auditoria da Persona e Cooldown)")
    if not df_msgs.empty:
        # Une ou exibe logs crus das conversas para fiscalizar o cooldown de 12 segundos e o parser das tags
        df_log_msgs = df_msgs[['lead_id', 'remetente', 'texto_mensagem', 'criado_em']].head(20)
        
        for idx, r in df_log_msgs.iterrows():
            avatar = "👤" if r['remetente'] == 'lead' else "🤖"
            autor = "Lead do Cliente" if r['remetente'] == 'lead' else "Sofia IA"
            timestamp = r['criado_em'].strftime('%d/%m/%m %H:%M:%S') if pd.notna(r['criado_em']) else "Sem data"
            
            str_app.markdown(f"**{avatar} {autor}** (ID Lead: `{r['lead_id']}`) — *{timestamp}*")
            str_app.blockquote(r['texto_mensagem'])
    else:
        str_app.info("Histórico de mensagens vazio no banco.")

with t_tenants:
    str_app.markdown("#### Configuração de Instâncias e Chaves de Destino do Handoff")
    colunas_validas_tenant = [c for c in ['id', 'instance_name', 'cliente_id', 'status_financeiro', 'nome_corretor_handoff', 'numero_corretor_handoff'] if c in df_tenants.columns]
    str_app.dataframe(df_tenants[colunas_validas_tenant], use_container_width=True, hide_index=True)

with t_leads:
    str_app.markdown("#### Base Bruta Isolada de Leads Capturados")
    if not df_leads.empty:
        colunas_validas_leads = [c for c in ['id', 'cliente_id', 'nome_lead', 'telefone_lead', 'status_qualificacao', 'intencao', 'bairro_preferido', 'orcamento', 'imovel_origem', 'notificado', 'ultima_interacao'] if c in df_leads.columns]
        str_app.dataframe(df_leads[colunas_validas_leads].sort_values(by='id', ascending=False), use_container_width=True, hide_index=True)
    else:
        str_app.info("Nenhum lead registrado.")

# Rodapé estático do sistema
str_app.markdown("---")
str_app.caption(f"Central de Monitoramento Sofia Core v3.0 • Status do SaaS: Online • Data de Consulta: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC")