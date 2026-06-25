"""
sofia_core.py — Módulo compartilhado com toda a lógica de negócio da Sofia:
persistência no Supabase, parser da Evolution API, motor de resposta via
Gemini, e envio de mensagens pelo WhatsApp.

Tanto o main.py (webhook fino, só recebe e enfileira) quanto o worker.py
(processa a fila respeitando o limite por corretor) importam este módulo,
evitando duplicar a lógica de negócio em dois lugares.
"""

import os
import re
import requests
from google import genai
from google.genai import types
from supabase import create_client, Client
from typing import Optional
from google.api_core.exceptions import ResourceExhausted
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIG GLOBAIS
# =============================================================================
COOLDOWN_SECONDS = 12

# =============================================================================
# CONEXÕES (SUPABASE, EVOLUTION API, GEMINI)
# =============================================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[CRÍTICO] ❌ SUPABASE_URL ou SUPABASE_KEY não configuradas!", flush=True)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL")
WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")

if not WHATSAPP_API_URL or not WHATSAPP_API_TOKEN:
    print("[CRÍTICO] ❌ WHATSAPP_API_URL ou WHATSAPP_API_TOKEN não configuradas!", flush=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[CRÍTICO] ❌ GEMINI_API_KEY não encontrada no ambiente!", flush=True)

client = genai.Client(api_key=api_key) if api_key else None


# =============================================================================
# CAMADA DE PERSISTÊNCIA E LÓGICA MULTI-TENANT (SUPABASE)
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
                "instance_name",
                "status_financeiro",
                "numero_corretor_handoff",
                "nome_corretor_handoff",
                "prompt_personalizado"
            )
            .eq("instance_name", instance_name)
            .execute()
        )

        if response.data:
            tenant = response.data[0]
            status = str(tenant.get("status_financeiro") or "Ativo").lower()

            if status in ["ativo", "conectado"]:
                return tenant
            else:
                print(f"[SaaS] 🚫 Tenant '{instance_name}' bloqueado por inadimplência/status inativo.", flush=True)

        return None

    except Exception as e:
        print(f"[SUPABASE] ❌ Erro ao verificar tenant: {e}", flush=True)
        return None


def obter_ou_criar_lead(cliente_id: str, telefone: str, nome: str = None, imovel_origem: str = None) -> Optional[dict]:
    """
    Busca o lead pelo telefone dentro do escopo isolado do cliente_id.
    Se não existir, cria dinamicamente salvando o nome e imóvel de origem.
    """
    try:
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
    """Resgata o histórico do banco estruturado no padrão nativo do Gemini API."""
    try:
        response = supabase.table("historico_mensagens") \
            .select("remetente", "texto_mensagem") \
            .eq("lead_id", lead_id) \
            .order("criado_em", desc=True) \
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
# REGRAS DE NEGÓCIO
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


def verificar_cooldown(lead: dict) -> bool:
    try:
        ultima = lead.get("ultima_interacao")
        if not ultima:
            return True

        ultimo_dt = datetime.fromisoformat(ultima.replace("Z", "+00:00"))
        agora = datetime.now(timezone.utc)
        diff = (agora - ultimo_dt).total_seconds()
        return diff >= COOLDOWN_SECONDS

    except Exception as e:
        print(f"[COOLDOWN] erro: {e}", flush=True)
        return True


def atualizar_cooldown(lead_id: str):
    try:
        supabase.table("leads").update({
            "ultima_interacao": datetime.now(timezone.utc).isoformat()
        }).eq("id", lead_id).execute()
    except Exception as e:
        print(f"[COOLDOWN] erro update: {e}", flush=True)


def enviar_mensagem_whatsapp(instance_name: str, destino: str, texto: str) -> bool:
    url = f"{WHATSAPP_API_URL}/message/sendText/{instance_name}"
    headers = {
        "Content-Type": "application/json",
        "apikey": WHATSAPP_API_TOKEN
    }
    payload = {
        "number": destino,
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
# PARSER DA EVOLUTION API
# =============================================================================
def parser_evolution(payload: dict) -> Optional[dict]:
    """Parser robusto para o formato real da Evolution API."""
    try:
        event = payload.get("event", "")
        if event not in ["messages.upsert", "messages.update"]:
            return None

        data = payload.get("data", {})
        key = data.get("key", {})

        if key.get("fromMe"):
            return None

        jid_bruto = key.get("remoteJid") or ""

        if "@g.us" in jid_bruto:
            return None

        numero_limpo = jid_bruto.split("@")[0]

        message = data.get("message", {})
        mensagem = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or message.get("imageMessage", {}).get("caption")
            or ""
        )

        if not mensagem:
            return None

        nome = data.get("pushName") or "Lead"

        imovel_id = (
            data.get("message", {})
            .get("extendedTextMessage", {})
            .get("contextInfo", {})
            .get("externalAdReply", {})
            .get("title", None)
        )

        return {
            "instance_name": payload.get("instance"),
            "numero": numero_limpo,
            "jid": jid_bruto,
            "nome": nome,
            "mensagem": mensagem,
            "imovel_id": imovel_id,
        }
    except Exception as e:
        print(f"[PARSER] ❌ Erro: {e}", flush=True)
        return None


# =============================================================================
# MOTOR DA IA (GEMINI)
# =============================================================================
def responder_com_gemini(tenant: dict, lead: dict, mensagem_nova: str) -> str:
    if not client:
        return "Desculpe, nosso sistema está em manutenção."

    # 🧊 COOLDOWN CHECK
    if not verificar_cooldown(lead):
        print("[COOLDOWN] bloqueando Gemini (spam)", flush=True)
        salvar_mensagem(lead["id"], "lead", mensagem_nova)
        return ""

    atualizar_cooldown(lead["id"])
    salvar_mensagem(lead["id"], "lead", mensagem_nova)

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

    prompt_extra = (tenant.get("prompt_personalizado") or "").strip()
    bloco_personalizacao = ""
    if prompt_extra:
        bloco_personalizacao = (
            "\nPERSONALIZAÇÃO DEFINIDA PELO CORRETOR (tom, personalidade e frases — siga isso "
            "sem nunca contrariar as REGRAS CRÍTICAS abaixo, que têm prioridade absoluta):\n"
            f"{prompt_extra}\n"
        )

    instrucao_sistema = (
        "Você é Sofia, corretora virtual empática e direta de uma imobiliária parceira. Conversa humanizada via WhatsApp.\n"
        "Sua missão é coletar 6 dados cruciais (um por vez, de forma fluida na conversa, sem parecer um questionário técnico):\n"
        "1. Intenção (comprar/alugar) | 2. Bairro preferido | 3. Qtd quartos | 4. Orçamento máximo | 5. Renda mensal | 6. Restrição CPF (pergunte de forma sutil).\n\n"
        "REGRAS CRÍTICAS:\n"
        "- Faça apenas UMA pergunta por mensagem.\n"
        "- Dê respostas curtas, acolhedoras, direto ao ponto e use emojis discretos.\n"
        f"{contexto_imovel}"
        f"{perfil_texto}"
        f"{bloco_personalizacao}\n"
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
        return "Estou recebendo muitas solicitações agora 😅 Pode tentar novamente em alguns instantes?"

    except Exception as e:
        print(f"[IA] ❌ Gemini falhou na geração: {e}", flush=True)
        return "Tive uma pequena oscilação na conexão. Pode repetir por favor? 🙏"

    if not resposta_completa or not str(resposta_completa).strip():
        return "Tive uma pequena oscilação na conexão. Pode repetir por favor? 🙏"

    # Extração do bloco [PERFIL]
    match_perfil = re.search(r"\[PERFIL\](.*?)\[/PERFIL\]", resposta_completa, re.DOTALL | re.IGNORECASE)
    dados_atualizacao = {}

    if match_perfil:
        bloco = match_perfil.group(1).strip()
        for linha in bloco.splitlines():
            if ":" in linha:
                chave, valor = linha.split(":", 1)
                chave = chave.strip().lower()
                valor = valor.strip()

                if chave == "intencao":
                    dados_atualizacao["intencao"] = valor
                if chave == "bairro":
                    dados_atualizacao["bairro_preferido"] = valor
                if chave == "quartos":
                    dados_atualizacao["quartos"] = valor
                if chave == "orcamento":
                    dados_atualizacao["orcamento"] = valor
                if chave == "renda":
                    dados_atualizacao["renda_mensal"] = valor
                if chave == "restricao":
                    texto = valor.lower().strip()
                    positivos = ["true", "sim", "possui", "tenho"]
                    negativos = [
                        "false", "não", "nao", "não possui", "nao possui",
                        "não tenho", "nao tenho", "não possuo", "nao possuo",
                        "não que eu saiba", "nao que eu saiba", "sem restrição", "sem restricao"
                    ]
                    if texto in positivos:
                        dados_atualizacao["restricao_cpf"] = True
                    elif texto in negativos:
                        dados_atualizacao["restricao_cpf"] = False

        if dados_atualizacao:
            lead_temp = {**lead, **dados_atualizacao}

            if verificar_qualificacao_dados(lead_temp):
                dados_atualizacao["status_qualificacao"] = "Qualificado"

            # Salva SEMPRE que houver dado novo, completo ou não.
            atualizar_perfil_lead(lead["id"], dados_perfil=dados_atualizacao)
            lead.update(dados_atualizacao)

    # Verificação de Handoff direto com dados atualizados do banco
    if verificar_qualificacao_dados(lead) and not lead.get("notificado"):
        if tenant.get("numero_corretor_handoff"):
            resumo_corretor = montar_resumo_lead(lead, tenant.get("nome_corretor_handoff", "Corretor"))
            if enviar_mensagem_whatsapp(tenant["instance_name"], tenant["numero_corretor_handoff"], resumo_corretor):
                atualizar_perfil_lead(lead["id"], {"notificado": True})
                lead["notificado"] = True

    resposta_limpa = re.sub(r"\[PERFIL\].*?\[/PERFIL\]", "", resposta_completa, flags=re.DOTALL | re.IGNORECASE).strip()

    if "oscilação" not in resposta_limpa.lower() and "muitas solicitações" not in resposta_limpa.lower():
        salvar_mensagem(lead["id"], "sofia", resposta_limpa)

    return resposta_limpa


def processar_mensagem_recebida(dados: dict) -> dict:
    """
    Orquestra o processamento completo de uma mensagem já parseada:
    valida o tenant, obtém/cria o lead, chama a Gemini, e envia a resposta
    pelo WhatsApp. Usado pelo worker.py ao consumir a fila do Redis.
    """
    instance_name = dados["instance_name"]
    numero = dados["numero"]
    jid_origem = dados["jid"]
    nome = dados["nome"]
    mensagem = dados["mensagem"]
    imovel_id = dados.get("imovel_id")

    tenant = verificar_tenant(instance_name)
    if not tenant:
        return {"status": "bloqueado", "mensagem": "Instância inativa ou inadimplente"}

    print(f"\n[SaaS] Cliente ativo: {instance_name} | Lead: {nome} ({numero})", flush=True)

    lead = obter_ou_criar_lead(tenant["cliente_id"], telefone=numero, nome=nome, imovel_origem=imovel_id)
    if not lead:
        print("❌ Falha ao obter/criar lead", flush=True)
        return {"status": "erro", "mensagem": "Falha no Supabase"}

    resposta = responder_com_gemini(tenant, lead, mensagem)
    print(f"👉 Gemini respondeu: {resposta}", flush=True)

    if not resposta or not resposta.strip():
        return {
            "status": "sucesso",
            "tenant_id": tenant["id"],
            "lead_id": lead["id"],
            "qualificado": lead.get("status_qualificacao") == "Qualificado"
        }

    enviou = enviar_mensagem_whatsapp(instance_name, jid_origem, resposta)
    print(f"[WHATSAPP] Envio status: {enviou}", flush=True)

    return {
        "status": "sucesso",
        "tenant_id": tenant["id"],
        "lead_id": lead["id"],
        "qualificado": lead.get("status_qualificacao") == "Qualificado"
    }