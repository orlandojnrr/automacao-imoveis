"""
main.py — Webhook fino da Sofia.

Responsabilidade única: receber o POST da Evolution API, fazer o parse
básico, e enfileirar a mensagem no Redis (uma fila por cliente_id) para
o worker.py processar de forma assíncrona e respeitando o limite de
mensagens por minuto de cada corretor.

Isso responde rápido para a Evolution API (evitando re-tentativas e
mensagens duplicadas) e desacopla o processamento pesado (Gemini +
Supabase) do ciclo de requisição HTTP.
"""

import os
import json
import redis
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from sofia_core import parser_evolution, verificar_tenant

load_dotenv()

app = Flask(__name__)

REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    print("[CRÍTICO] ❌ REDIS_URL não configurada!", flush=True)

redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

NOME_FILA_PREFIXO = "sofia:fila:"


@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Sofia IA — SaaS Core Ativo ✅ (webhook + fila)", 200


@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_json(silent=True) or {}

    dados = parser_evolution(payload)
    if not dados:
        # Evento irrelevante (grupo, mensagem própria, sem texto, etc) — ignora silenciosamente.
        return jsonify({"status": "ignorado"}), 200

    # Validação leve do tenant aqui evita enfileirar mensagens de instâncias
    # bloqueadas/inadimplentes — falha rápido sem gastar Gemini depois.
    tenant = verificar_tenant(dados["instance_name"])
    if not tenant:
        print(f"[Webhook] 🚫 Tenant '{dados['instance_name']}' inativo — mensagem descartada.", flush=True)
        return jsonify({"status": "tenant_inativo"}), 200

    if not redis_client:
        print("[CRÍTICO] ❌ Redis indisponível — não foi possível enfileirar a mensagem!", flush=True)
        return jsonify({"status": "erro", "mensagem": "Fila indisponível"}), 503

    nome_fila = f"{NOME_FILA_PREFIXO}{tenant['cliente_id']}"
    try:
        redis_client.rpush(nome_fila, json.dumps(dados))
        print(f"[Webhook] ✅ Mensagem de {dados['nome']} ({dados['numero']}) enfileirada em '{nome_fila}'", flush=True)
    except Exception as e:
        print(f"[Webhook] ❌ Erro ao enfileirar no Redis: {e}", flush=True)
        return jsonify({"status": "erro", "mensagem": "Falha ao enfileirar"}), 503

    return jsonify({"status": "enfileirado"}), 200


if __name__ == '__main__':
    porta = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=porta, debug=False)