import os
import time
import threading
import requests
from flask import Flask, request, jsonify
from google import genai  # SDK Moderno oficial da Google

# Inicializa o aplicativo Flask para gerenciar os Webhooks
app = Flask(__name__)

# =========================================================================
# CONFIGURAÇÕES DA API DO WHATSAPP (EVOLUTION API)
# O código vai tentar buscar do Render. Se não existir lá, usa esses como padrão.
# =========================================================================
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "https://sua-api-evolution.com")
WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN", "SeuTokenGlobalAqui")
WHATSAPP_INSTANCE_NAME = os.environ.get("WHATSAPP_INSTANCE_NAME", "Imobiliaria_Corretor")

# Dicionário na memória para guardar o histórico de conversas por número de telefone
# Estrutura: { "5521988888888": ["Cliente: Oi", "Corretor: Olá!", "Cliente: Quero uma casa"] }
historico_conversas = {}

# Busca a chave de autenticação da API do Gemini nas variáveis de ambiente do Render
api_key = os.environ.get("GEMINI_API_KEY")

# Inicializa o cliente apontando explicitamente para a API de produção v1
if api_key:
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1'}
    )
else:
    client = None
    print("[AVISO] Chave GEMINI_API_KEY não encontrada nas variáveis.", flush=True)

def enviar_mensagem_whatsapp(numero_cliente, texto_resposta):
    """
    Função responsável por pegar o texto gerado pelo Gemini e fazer um disparo
    HTTP do tipo POST para a API do WhatsApp enviar a mensagem de fato para o cliente.
    """
    # Se ainda estiver usando a URL de exemplo, apenas simula no log
    if "sua-api-evolution" in WHATSAPP_API_URL:
        print(f"[WHATSAPP - SIMULAÇÃO] Enviando para {numero_cliente}: {texto_resposta[:50]}...", flush=True)
        return False

    # Monta a URL exata de disparo da Evolution API para envio de texto plano
    url_envio = f"{WHATSAPP_API_URL}/message/sendText/{WHATSAPP_INSTANCE_NAME}"
    
    # Monta o cabeçalho (Header) com a chave de segurança exigida pela Evolution API
    headers = {
        "Content-Type": "application/json",
        "apikey": WHATSAPP_API_TOKEN
    }
    
    # Monta o corpo da requisição (Payload) com o número do cliente e o texto da IA
    payload = {
        "number": numero_cliente,
        "options": {
            "delay": 1200,       # Simula um atraso de 1.2 segundos para parecer digitação humana
            "presence": "composing"  # Faz aparecer "Digitando..." no WhatsApp do cliente
        },
        "textMessage": {
            "text": texto_resposta
        }
    }

    try:
        # Faz o disparo real via internet para a API do WhatsApp
        resposta_api = requests.post(url_envio, json=payload, headers=headers)
        
        # Se o status for 200 ou 201, o envio foi aceito pela API com sucesso
        if resposta_api.status_code in [200, 201]:
            print(f"[WHATSAPP] Mensagem enviada com sucesso para o número {numero_cliente}!", flush=True)
            return True
        else:
            print(f"[ERRO WHATSAPP] Falha ao enviar. Status: {resposta_api.status_code} - Resposta: {resposta_api.text}", flush=True)
            return False
    except Exception as erro_conexao:
        print(f"[ERRO CRÍTICO] Não foi possível conectar na API do WhatsApp: {erro_conexao}", flush=True)
        return False

def responder_com_gemini(numero_cliente, mensagem_cliente):
    """
    Função que consulta a IA da Google levando em consideração o histórico do cliente.
    """
    if not client:
        return "Erro: Cliente Gemini não foi inicializado por falta de API Key."
        
    # Se o número não tiver histórico, inicializa uma lista vazia
    if numero_cliente not in historico_conversas:
        historico_conversas[numero_cliente] = []
        
    # Adiciona a nova mensagem do cliente ao histórico dele
    historico_conversas[numero_cliente].append(f"Cliente: {mensagem_cliente}")
    
    # Limita o histórico para as últimas 10 mensagens para não estourar ou gastar tokens à toa
    if len(historico_conversas[numero_cliente]) > 10:
        historico_conversas[numero_cliente] = historico_conversas[numero_cliente][-10:]
        
    # Junta todo o histórico acumulado em um único bloco de texto
    contexto_conversas = "\n".join(historico_conversas[numero_cliente])

    prompt_sistema = (
        "Você é um corretor de imóveis profissional, muito educado, empático e prestativo. "
        "Sua missão é responder à última mensagem do cliente com base no histórico da conversa abaixo. "
        "Tente entender melhor o que ele precisa (como localização, quantidade de quartos e orçamento) "
        "e conduza a conversa para agendar uma visita ou ligação.\n"
        "Responda de forma natural, humanizada, evite textos longos e use emojis moderadamente.\n\n"
        "--- HISTÓRICO DA CONVERSA ---\n"
        f"{contexto_conversas}\n"
        "------------------------------\n"
        "Resposta do Corretor:"
    )

    modelos_para_testar = ['gemini-2.5-flash', 'gemini-1.5-flash']
    ultimo_erro = None

    for modelo in modelos_para_testar:
        try:
            print(f"[IA] Tentando conectar usando o modelo: {modelo}...", flush=True)
            response = client.models.generate_content(
                model=modelo,
                contents=prompt_sistema,
            )
            
            resposta_texto = response.text
            
            # Salva a resposta da própria IA no histórico para ela lembrar do que disse antes
            historico_conversas[numero_cliente].append(f"Corretor: {resposta_texto}")
            
            return resposta_texto
        except Exception as e:
            ultimo_erro = e
            print(f"[AVISO] O modelo {modelo} não respondeu. Tentando o próximo...", flush=True)
            continue
            
    return f"Erro crítico: Nenhum modelo disponível respondeu na API v1. Detalhes: {ultimo_erro}"

@app.route('/', methods=['GET', 'HEAD'])
def home():
    """Rota de verificação de saúde do Render (Health Check)"""
    return "Sistema de Automação Imobiliária Ativo", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Rota principal que recebe as mensagens do Webhook.
    """
    dados = request.get_json()
    
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
        
    # Capturamos os dados enviados pelo webhook
    numero_remetente = dados.get('numero', '5511999999999')
    nome_cliente = dados.get('nome', 'Cliente')
    texto_mensagem = dados.get('mensagem', '')
    
    print(f"\n[WHATSAPP] Nova mensagem recebida de {nome_cliente} ({numero_remetente})!", flush=True)
    print(f"[WHATSAPP] Texto: '{texto_mensagem}'", flush=True)
    print("[IA] Iniciando chamada com os servidores da Google Gemini...", flush=True)
    
    # Gera a resposta inteligente usando o Gemini (passando o número para a memória)
    resposta_ia = responder_com_gemini(numero_remetente, texto_mensagem)
    
    print("\n==================================================", flush=True)
    print(f"[IA RESPOSTA PARA {nome_cliente.upper()}]:", flush=True)
    print(resposta_ia, flush=True)
    print("==================================================\n", flush=True)
    
    # Envia automaticamente para o WhatsApp do cliente (se configurado)
    enviar_mensagem_whatsapp(numero_remetente, resposta_ia)
    
    return jsonify({"status": "sucesso", "resposta": resposta_ia}), 200

def rotina_segundo_plano():
    """Thread paralela para simulações e logs de rotina"""
    time.sleep(10)
    
    print("[TESTE MULTI-MENSAGEM] Iniciando simulação da Mariana testando a nova memória...", flush=True)
    
    with app.test_client() as simulador:
        # Mensagem 1
        simulador.post('/webhook', json={
            "nome": "Mariana",
            "numero": "5521988888888",
            "mensagem": "Olá, gostaria de ver uma casa de 3 quartos."
        })
        
        time.sleep(3)
        
        # Mensagem 2 (Sem dizer quantos quartos ou o que quer, para testar se o bot lembra)
        simulador.post('/webhook', json={
            "nome": "Mariana",
            "numero": "5521988888888",
            "mensagem": "De preferência perto do centro. Quanto custa mais ou menos?"
        })
    
    while True:
        time.sleep(15)
        print("[LOG] Monitorando banco de dados de imóveis e novas mensagens...", flush=True)

if __name__ == '__main__':
    print("\n--- SISTEMA DE AUTOMAÇÃO IMOBILIÁRIA ATIVO ---", flush=True)
    print("Aguardando novas mensagens de leads do WhatsApp...\n", flush=True)
    
    threading.Thread(target=rotina_segundo_plano, daemon=True).start()
        
    porta = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta, debug=False, use_reloader=False)