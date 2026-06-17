import os
import re
import requests
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from supabase import create_client, Client
from typing import Optional, Dict, Any
from google.api_core.exceptions import ResourceExhausted

# ⚡ ISSO PRECISA FICAR AQUI, ANTES DE QUALQUER LEITURA DE OS.ENVIRON!
from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# INICIALIZAÇÃO DO FLASK E SUPABASE (SaaS Stateless)
# =============================================================================
app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[CRÍTICO] ❌ SUPABASE_URL ou SUPABASE_KEY não configuradas!", flush=True)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# =============================================================================
# CONFIGURAÇÕES DA EVOLUTION API (WhatsApp) & GEMINI
# =============================================================================
WHATSAPP_API_URL   = os.environ.get("WHATSAPP_API_URL")
WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")

if not WHATSAPP_API_URL or not WHATSAPP_API_TOKEN:
    print("[CRÍTICO] ❌ WHATSAPP_API_URL ou WHATSAPP_API_TOKEN não configuradas!", flush=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[CRÍTICO] ❌ GEMINI_API_KEY não encontrada no ambiente!", flush=True)

client = genai.Client(api_key=api_key) if api_key else None

# =============================================================================
# CAMADA DE PERSISTÊNCIA E LOGICA MULTI-TENANT (SUPABASE)
# =============================================================================

def verificar_tenant(instance_name: str) -> Optional[dict]:
    """
    Regra Comercial: Checa o status financeiro no banco.
    Se estiver inadimplente ou não existir, retorna None para não gastar API.
    """

    try:

        response = (
            supabase
            .table("configuracoes_whatsapp")
            .select(
                "id",
                "cliente_id",
                "status_financeiro",
                "numero_corretor_handoff",
                "nome_corretor_handoff"
            )
            .eq("instance_name", instance_name)
            .execute()
        )

        if response.data:

            tenant = response.data[0]

            # Evita quebra se vier nulo
            status = str(
                tenant.get("status_financeiro") or "Ativo"
            ).lower()

            if status in ["ativo", "conectado"]:
                return tenant

            else:
                print(
                    f"[SaaS] 🚫 Tenant '{instance_name}' bloqueado "
                    f"por inadimplência/status inativo.",
                    flush=True
                )

        return None

    except Exception as e:

        print(
            f"[SUPABASE] ❌ Erro ao verificar tenant: {e}",
            flush=True
        )

        return None

def obter_ou_criar_lead(cliente_id: str, telefone: str, nome: str = None, imovel_origem: str = None) -> Optional[dict]:
    """
    Busca o lead pelo telefone dentro do escopo isolado do cliente_id.
    Se não existir, cria dinamicamente salvando o nome e imóvel de origem (apenas números se aplicável).
    """
    try:
        # Se sua coluna 'imovel_origem' no banco for INT, limpamos para pegar apenas números do ID do anúncio.
        # Se for TEXT no banco, pode remover a linha abaixo.
        imovel_limpo = "".join(filter(str.isdigit, str(imovel_origem))) if imovel_origem else None
        
        response = supabase.table("leads").select("*").eq("cliente_id", cliente_id).eq("telefone_lead", telefone).execute()
        
        if response.data:
            lead = response.data[0]
            dados_update = {}
    
            if nome and (not lead.get("nome_lead") or lead["nome_lead"] == "Lead") and nome != "Lead":
                dados_update["nome_lead"] = nome
            if imovel_limpo and lead.get("imovel_origem") != imovel_limpo:
                dados_update["imovel_origem"] = imovel_limpo
        
            if dados_update:
                supabase.table("leads").update(dados_update).eq("id", lead["id"]).execute()
                lead.update(dados_update)
            return lead
        
        novo_lead = {
            "cliente_id": cliente_id,
            "telefone_lead": telefone,
            "nome_lead": nome or "Lead",
            "imovel_origem": imovel_limpo,
            "intencao": None, "bairro_preferido": None, "quartos": None,
            "orcamento": None, "renda_mensal": None, "restricao_cpf": None,
            "status_qualificacao": "Pendente", "notificado": False
        }
        insert_response = supabase.table("leads").insert(novo_lead).execute()
        return insert_response.data[0] if insert_response.data else None
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao gerenciar lead: {e}", flush=True)
        return None

def atualizar_perfil_lead(lead_id: str, dados_perfil: dict):
    """Atualiza os dados de qualificação coletados pela Sofia no Supabase."""
    try:
        supabase.table("leads").update(dados_perfil).eq("id", lead_id).execute()
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao atualizar perfil do lead: {e}", flush=True)

def salvar_mensagem(lead_id: str, remetente: str, texto: str):
    """Registra a interação na tabela de histórico."""
    try:
        supabase.table("historico_mensagens").insert({
            "lead_id": lead_id,
            "remetente": remetente,
            "texto_mensagem": texto
        }).execute()
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao salvar mensagem: {e}", flush=True)

def buscar_contexto_conversa(lead_id: str, limite: int = 6) -> list:
    """Resgata o histórico do banco estruturado exatamente para o padrão nativo do Gemini API."""
    try:
        response = supabase.table("historico_mensagens")\
            .select("remetente", "texto_mensagem")\
            .eq("lead_id", lead_id)\
            .order("criado_em", desc=True)\
            .limit(limite).execute()
        
        historico = []
        for msg in reversed(response.data):
            role = "user" if msg["remetente"] == "lead" else "model"
            historico.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["texto_mensagem"])]
                )
            )
        return historico
    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao buscar histórico: {e}", flush=True)
        return []

# =============================================================================
# REGRAS DE NEGÓCIO E MOTOR DE MENSAGENS
# =============================================================================

def verificar_qualificacao_dados(lead: dict) -> bool:
    """Valida se todos os critérios do lead salvos no banco estão preenchidos."""
    criticos = [
        lead.get("intencao"),
        lead.get("bairro_preferido"),
        lead.get("quartos"),
        lead.get("orcamento"),
        lead.get("renda_mensal")
    ]
    if all(x and str(x).strip() for x in criticos) and lead.get("restricao_cpf") is not None:
        return True
    return False

def montar_resumo_lead(lead: dict, corretor_nome: str) -> str:
    nome = lead.get("nome_lead") or "Não informado"
    restricao = lead.get("restricao_cpf")
    restricao_texto = "✅ Sem restrição" if restricao is False else "⚠️ Possui restrição" if restricao is True else "Não informado"
    imovel_texto = f"\n📸 *Imóvel de Origem ID:* {lead['imovel_origem']}" if lead.get("imovel_origem") else ""

    return (
        f"🔥 *LEAD QUENTE QUALIFICADO!*\n"
        f"Olá {corretor_nome}, Sofia capturou um cliente:\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Nome:* {nome}\n"
        f"📱 *Número:* {lead['telefone_lead']}\n"
        f"🎯 *Intenção:* {lead['intencao']}\n"
        f"📍 *Bairro:* {lead['bairro_preferido']}\n"
        f"🛏️ *Quartos:* {lead['quartos']}\n"
        f"💰 *Orçamento:* {lead['orcamento']}\n"
        f"💼 *Renda:* {lead['renda_mensal']}\n"
        f"📋 *Restrição CPF:* {restricao_texto}"
        f"{imovel_texto}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Pronto para você assumir o atendimento!"
    )

def enviar_mensagem_whatsapp(instance_name: str, destino: str, texto: str) -> bool:
    url = f"{WHATSAPP_API_URL}/message/sendText/{instance_name}"
    headers = {
        "Content-Type": "application/json",
        "apikey": WHATSAPP_API_TOKEN
    }

    payload = {
        "number": destino,  # manda o @lid direto
        "text": texto,
        "delay": 1200
    }

    try:
        resposta = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"[WHATSAPP] Status HTTP: {resposta.status_code} | Body: {resposta.text[:200]}", flush=True)
        return resposta.status_code in [200, 201]
    except Exception as e:
        print(f"[WHATSAPP] ❌ Erro: {e}", flush=True)
        return False

# =============================================================================
# PARSER EXCLUSIVO E MOTOR DA IA
# =============================================================================

def parser_evolution(payload: dict) -> Optional[dict]:

    """Parser robusto para o formato real da Evolution API."""
    try:
        event = payload.get("event", "")
        if event not in ["messages.upsert", "messages.update"]:
            return None

        data = payload.get("data", {})
        key = data.get("key", {})

        print(f"[DEBUG] KEY COMPLETA: {key}", flush=True)

        # Ignora mensagens enviadas pelo próprio bot
        if key.get("fromMe"):
            return None

        jid_bruto = key.get("remoteJid") or ""
        print(f"[DEBUG] JID BRUTO EXTRAÍDO: {jid_bruto}", flush=True)

        # Ignora grupos
        if "@g.us" in jid_bruto:
            return None

        # Extrai o número limpo (sem @lid, @s.whatsapp.net etc.)
        numero_limpo = jid_bruto.split("@")[0]

        # Extrai a mensagem de texto (tenta os campos mais comuns)
        message = data.get("message", {})
        mensagem = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or message.get("imageMessage", {}).get("caption")
            or ""
        )

        if not mensagem:
            return None

        # Nome do contato (pushName)
        nome = data.get("pushName") or "Lead"

        return {
            "instance_name": payload.get("instance"),
            "numero": numero_limpo,
            "jid": jid_bruto,
            "nome": nome,
            "mensagem": mensagem
        }
    except Exception as e:
        print(f"[PARSER] ❌ Erro: {e}", flush=True)
        return None

def responder_com_gemini(tenant: dict, lead: dict, mensagem_nova: str) -> str:
    if not client:
        return "Desculpe, nosso sistema está em manutenção."

    # 1. Salva a nova mensagem recebida do usuário no banco
    salvar_mensagem(lead["id"], "lead", mensagem_nova)

    # 2. Resgata o histórico atualizado convertendo para o formato da API
    historico_completo = buscar_contexto_conversa(lead["id"], limite=6)
    
    contexto_imovel = f"\n⚠️ CONTEXTO DO IMÓVEL DE ORIGEM INTERESSE ID: {lead['imovel_origem']}\n" if lead.get("imovel_origem") else ""
    
    perfil_texto = (
        f"\n📋 PERFIL COLETADO ATÉ AGORA NO BANCO:\n"
        f"- Intenção: {lead.get('intencao') or 'Não coletado'}\n"
        f"- Bairro: {lead.get('bairro_preferido') or 'Não coletado'}\n"
        f"- Quartos: {lead.get('quartos') or 'Não coletado'}\n"
        f"- Orçamento: {lead.get('orcamento') or 'Não coletado'}\n"
        f"- Renda: {lead.get('renda_mensal') or 'Não coletado'}\n"
        f"- Restrição CPF: {lead.get('restricao_cpf') if lead.get('restricao_cpf') is not None else 'Não coletado'}\n"
    )

    instrucao_sistema = (
        "Você é Sofia, corretora virtual empática e direta de uma imobiliária parceira. Conversa humanizada via WhatsApp.\n"
        "Sua missão é coletar 6 dados cruciais (um por vez, de forma fluida na conversa, sem parecer um questionário técnico):\n"
        "1. Intenção (comprar/alugar) | 2. Bairro preferido | 3. Qtd quartos | 4. Orçamento máximo | 5. Renda mensal | 6. Restrição CPF (pergunte de forma sutil).\n\n"
        "REGRAS CRÍTICAS:\n"
        "- Faça apenas UMA pergunta por mensagem.\n"
        "- Dê respostas curtas, acolhedoras, direto ao ponto e use emojis discretos.\n"
        f"{contexto_imovel}"
        f"{perfil_texto}\n"
        "QUANDO COLETAR OS 6 CRITÉRIOS COMPLETOS:\n"
        "Informe cordialmente ao cliente que o especialista humano vai dar continuidade por ali. "
        "E inclua OBRIGATORIAMENTE no final da mensagem o bloco de dados estruturado exatamente neste formato para o sistema ler:\n"
        "[PERFIL]\n"
        "intencao: <comprar ou alugar>\n"
        "bairro: <nome do bairro>\n"
        "quartos: <quantidade>\n"
        "orcamento: <valor>\n"
        "renda: <valor>\n"
        "restricao: <True se tiver restrição / False se não tiver>\n"
        "[/PERFIL]"
    )

    try:

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=historico_completo,
            config=types.GenerateContentConfig(
                system_instruction=instrucao_sistema,
                temperature=0.7
            )
        )

        resposta_completa = getattr(response, "text", None)

    except ResourceExhausted:

        print("[IA] ⚠️ Limite Gemini atingido (429)", flush=True)

        return (
        "Estou recebendo muitas solicitações agora 😅 "
        "Pode tentar novamente em alguns instantes?"
    )

    except Exception as e:

        print(f"[IA] ❌ Gemini falhou na geração: {e}", flush=True)

        return (
        "Tive uma pequena oscilação na conexão. "
        "Pode repetir por favor? 🙏"
    )

    if not resposta_completa or not str(resposta_completa).strip():
        return "Tive uma pequena oscilação na conexão. Pode repetir por favor? 🙏"

    # 3. Processamento e Extração de Tags da IA
    match_perfil = re.search(r"\[PERFIL\](.*?)\[/PERFIL\]", resposta_completa, re.DOTALL | re.IGNORECASE)
    dados_atualizacao = {}
    
    if match_perfil:
        bloco = match_perfil.group(1).strip()
        for linha in bloco.splitlines():
            if ":" in linha:
                chave, valor = linha.split(":", 1)
                chave = chave.strip().lower()
                valor = valor.strip()

                if chave == "intencao":   dados_atualizacao["intencao"] = valor
                if chave == "bairro":     dados_atualizacao["bairro_preferido"] = valor
                if chave == "quartos":    dados_atualizacao["quartos"] = valor
                if chave == "orcamento":  dados_atualizacao["orcamento"] = valor
                if chave == "renda":      dados_atualizacao["renda_mensal"] = valor
                if chave == "restricao":

                    texto = valor.lower().strip()

                    positivos = [
                        "true",
                        "sim",
                        "possui",
                        "tenho"
                    ]

                    negativos = [
                        "false",
                        "não",
                        "nao",
                        "não possui",
                        "nao possui",
                        "não tenho",
                        "nao tenho",
                        "não possuo",
                        "nao possuo",
                        "não que eu saiba",
                        "nao que eu saiba",
                        "sem restrição",
                        "sem restricao"
                    ]

                    if texto in positivos:
                        dados_atualizacao["restricao_cpf"] = True

                    elif texto in negativos:
                        dados_atualizacao["restricao_cpf"] = False

        if dados_atualizacao:

            lead_temp = {**lead, **dados_atualizacao}

            if verificar_qualificacao_dados(lead_temp):
                dados_atualizacao["status_qualificacao"] = "Qualificado"
                
            atualizar_perfil_lead(lead["id"], dados_perfil=dados_atualizacao)
            lead.update(dados_atualizacao)

    # 4. Verificação de Handoff direto com dados atualizados do banco
    if verificar_qualificacao_dados(lead) and not lead.get("notificado"):
        if tenant.get("numero_corretor_handoff"):
            resumo_corretor = montar_resumo_lead(lead, tenant.get("nome_corretor_handoff", "Corretor"))
            if enviar_mensagem_whatsapp(tenant["instance_name"], tenant["numero_corretor_handoff"], resumo_corretor):
                atualizar_perfil_lead(lead["id"], {"notificado": True})
                lead["notificado"] = True

    # Limpeza da Resposta técnica para o cliente final não ver as tags
    resposta_limpa = re.sub(r"\[PERFIL\].*?\[/PERFIL\]", "", resposta_completa, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # 5. Salva a resposta limpa gerada pela Sofia no histórico do banco
    if (
        "oscilação" not in resposta_limpa.lower()
        and "muitas solicitações" not in resposta_limpa.lower()
    ):
        salvar_mensagem(lead["id"], "sofia", resposta_limpa)

    return resposta_limpa

# =============================================================================
# ROTA PRINCIPAL DO WEBHOOK (SAAS ORQUESTRADOR)
# =============================================================================
@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Sofia IA — SaaS Core Ativo ✅", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "erro", "mensagem": "Sem JSON"}), 400

    # 🔍 PRINT DIAGNÓSTICO: Mostra resumidamente o que está chegando para sabermos as chaves exatas
    print(f"\n[DEBUG PAYLOAD] Evento recebido: {payload.get('event')} | Instance: {payload.get('instance')}", flush=True)
    if "data" in payload and "message" in payload["data"]:
        print(f"[DEBUG MSG] Chaves dentro de message: {list(payload['data']['message'].keys())}", flush=True)

    # 🚀 PASSO 0: Decodificação e extração segura do Payload
    dados_processados = parser_evolution(payload)
    if not dados_processados:
        return jsonify({"status": "ignorado", "mensagem": "Mensagem gerada pelo bot ou inválida"}), 200

    instance_name = dados_processados["instance_name"]
    numero        = dados_processados["numero"]
    jid_origem    = dados_processados["jid"]
    nome          = dados_processados["nome"]
    mensagem      = dados_processados["mensagem"]

    if not mensagem:
        return jsonify({"status": "sucesso", "mensagem": "Sem conteúdo textual"}), 200

    imovel_id = payload.get("data", {}).get("message", {}).get("extendedTextMessage", {}).get("contextInfo", {}).get("externalAdReply", {}).get("title", None)

    tenant = verificar_tenant(instance_name)
    if not tenant:
        return jsonify({"status": "bloqueado", "mensagem": "Instância inativa ou inadimplente. Execução interrompida."}), 200

    print(f"\n[SaaS Webhook] Cliente ativo: {instance_name} | Mensagem de {nome} ({numero})", flush=True)

    lead = obter_ou_criar_lead(tenant["cliente_id"], telefone=numero, nome=nome, imovel_origem=imovel_id)
    if not lead:
        print("❌ [RASTREAMENTO] Falhou ao obter ou criar o lead no Supabase!", flush=True)
        return jsonify({"status": "erro", "mensagem": "Falha na persistência dos dados."}), 500

    print("👉 [RASTREAMENTO] Passo 2 Concluído. Chamando o Gemini...", flush=True)

    resposta = responder_com_gemini(tenant, lead, mensagem)
    
    print(f"👉 [RASTREAMENTO] Gemini respondeu: {resposta}", flush=True)

    enviou = enviar_mensagem_whatsapp(instance_name, jid_origem, resposta)
    print(f"👉 [RASTREAMENTO] Status do envio na API: {enviou}", flush=True)

    return jsonify({
        "status": "sucesso",
        "tenant_id": tenant["id"],
        "lead_id": lead["id"],
        "qualificado": lead.get("status_qualificacao") == "Qualificado"
    }), 200

# =============================================================================
# INICIALIZAÇÃO DA APLICAÇÃO
# =============================================================================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  SOFIA IA — ARQUITETURA SAAS MULTI-TENANT (V3.0) — ATUALIZADO")
    print("="*50 + "\n", flush=True)

    porta = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta, debug=False)