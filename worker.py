"""
worker.py — Processador assíncrono da fila de mensagens da Sofia.

Roda em loop contínuo, lendo as filas por cliente_id no Redis (uma fila
por corretor, criada pelo main.py) e processando cada mensagem através
de sofia_core.processar_mensagem_recebida — exceto quando o corretor já
atingiu o limite de mensagens por minuto, caso em que a mensagem volta
para o fim da própria fila e será tentada novamente no próximo ciclo.

Isso garante que um único corretor recebendo uma enxurrada de leads nunca
consome toda a cota da API do Gemini, protegendo os demais tenants.
"""

import os
import json
import time
import redis
from dotenv import load_dotenv

from sofia_core import processar_mensagem_recebida

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    print("[CRÍTICO] ❌ REDIS_URL não configurada! Worker não pode iniciar.", flush=True)

redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

NOME_FILA_PREFIXO = "sofia:fila:"
NOME_RATE_LIMIT_PREFIXO = "sofia:ratelimit:"

LIMITE_MENSAGENS_POR_MINUTO = 15
JANELA_RATE_LIMIT_SEGUNDOS = 60
INTERVALO_CICLO_SEGUNDOS = 1.5


def dentro_do_limite(cliente_id: str) -> bool:
    """
    Rate limiter de janela fixa por cliente_id, usando INCR + EXPIRE do Redis.
    Cada corretor tem sua própria chave, que expira sozinha após a janela —
    não precisa de limpeza manual.
    """
    chave = f"{NOME_RATE_LIMIT_PREFIXO}{cliente_id}"
    try:
        contagem_atual = redis_client.incr(chave)
        if contagem_atual == 1:
            redis_client.expire(chave, JANELA_RATE_LIMIT_SEGUNDOS)
        return contagem_atual <= LIMITE_MENSAGENS_POR_MINUTO
    except Exception as e:
        print(f"[RATE LIMIT] ⚠️ Erro ao verificar limite (permitindo por segurança): {e}", flush=True)
        return True


def listar_filas_ativas() -> list:
    try:
        return redis_client.keys(f"{NOME_FILA_PREFIXO}*")
    except Exception as e:
        print(f"[WORKER] ❌ Erro ao listar filas: {e}", flush=True)
        return []


def processar_um_ciclo():
    filas = listar_filas_ativas()

    for nome_fila in filas:
        cliente_id = nome_fila.replace(NOME_FILA_PREFIXO, "")

        if not dentro_do_limite(cliente_id):
            print(f"[RATE LIMIT] ⏸️ Cliente {cliente_id} atingiu o limite de {LIMITE_MENSAGENS_POR_MINUTO}/min — aguardando.", flush=True)
            continue

        try:
            item_bruto = redis_client.lpop(nome_fila)
        except Exception as e:
            print(f"[WORKER] ❌ Erro ao ler fila '{nome_fila}': {e}", flush=True)
            continue

        if not item_bruto:
            continue

        try:
            dados = json.loads(item_bruto)
        except Exception as e:
            print(f"[WORKER] ❌ Mensagem corrompida na fila, descartando: {e}", flush=True)
            continue

        print(f"[WORKER] ▶️ Processando mensagem de {dados.get('nome')} ({dados.get('numero')}) — cliente {cliente_id}", flush=True)

        try:
            resultado = processar_mensagem_recebida(dados)
            print(f"[WORKER] ✅ Resultado: {resultado}", flush=True)
        except Exception as e:
            print(f"[WORKER] ❌ Erro inesperado ao processar mensagem: {e}", flush=True)


def main():
    print("=================================================", flush=True)
    print("  SOFIA IA — WORKER DE PROCESSAMENTO DA FILA", flush=True)
    print(f"  Limite: {LIMITE_MENSAGENS_POR_MINUTO} mensagens/minuto por corretor", flush=True)
    print("=================================================", flush=True)

    if not redis_client:
        print("[CRÍTICO] ❌ Worker não pode operar sem Redis. Encerrando.", flush=True)
        return

    while True:
        try:
            processar_um_ciclo()
        except Exception as e:
            print(f"[WORKER] ❌ Erro no ciclo principal: {e}", flush=True)

        time.sleep(INTERVALO_CICLO_SEGUNDOS)


if __name__ == '__main__':
    main()