import os
import time
import threading
import requests  # Nova biblioteca importada para fazer os disparos de mensagens para o WhatsApp
from flask import Flask, request, jsonify
from google import genai  # SDK Moderno oficial da Google

# Inicializa o aplicativo Flask para gerenciar os Webhooks
app = Flask(__name__)

# =========================================================================
# CONFIGURAÇÕES DA API DO WHATSAPP (EVOLUTION API)
# Deixamos essas variáveis prontas. Quando você configurar sua API do WhatsApp,
# basta preencher os valores aqui. Por enquanto, ficam como exemplo.
# =========================================================================
WHATSAPP_API_URL = "https://sua-api-evolution.com"  # O endereço onde sua API estará rodando
WHATSAPP_API_TOKEN = "SeuTokenGlobalAqui"            # A senha de segurança da sua API
WHATSAPP_INSTANCE_NAME = "Imobiliaria_Corretor"     # O nome da instância que você criou na API

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
    # Se você ainda não configurou os dados reais da API, a função apenas avisa no log e não trava o código
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

def responder_com_gemini(mensagem_cliente):
    """
    Função com sistema de contingência (Fallback) que consulta a IA da Google.
    """
    if not client:
        return "Erro: Cliente Gemini não foi inicializado por falta de API Key."
        
    prompt_sistema = (
        "Você é um corretor de imóveis profissional, muito educado e prestativo. "
        "Sua missão é responder à mensagem do cliente abaixo, tentando entender melhor o que ele precisa "
        "(como localização, quantidade de quartos e orçamento) e agendar uma visita ou ligação. "
        "Responda de forma natural, humanizada e use emojis moderadamente.\n\n"
        f"Mensagem do Cliente: {mensagem_cliente}"
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
            return response.text
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
    Rota principal que recebe as mensagens. Agora ela captura o número
    de quem enviou para podermos responder de volta!
    """
    dados = request.get_json()
    
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
        
    # Capturamos o número ou id do remetente (caso não exista, usamos um padrão para testes)
    numero_remetente = dados.get('numero', '5511999999999')
    nome_cliente = dados.get('nome', 'Cliente')
    texto_mensagem = dados.get('mensagem', '')
    
    print(f"\n[WHATSAPP] Nova mensagem recebida de {nome_cliente} ({numero_remetente})!", flush=True)
    print(f"[WHATSAPP] Texto: '{texto_mensagem}'", flush=True)
    print("[IA] Iniciando chamada com os servidores da Google Gemini...", flush=True)
    
    # Gera a resposta inteligente usando o Gemini
    resposta_ia = responder_com_gemini(texto_mensagem)
    
    print("\n==================================================", flush=True)
    print(f"[IA RESPOSTA PARA {nome_cliente.upper()}]:", flush=True)
    print(resposta_ia, flush=True)
    print("==================================================\n", flush=True)
    
    # NOVA LOGICA: Pega o texto da IA e envia automaticamente para o WhatsApp do cliente!
    enviar_mensagem_whatsapp(numero_remetente, resposta_ia)
    
    return jsonify({"status": "sucesso", "resposta": resposta_ia}), 200

def rotina_segundo_plano():
    """Thread paralela para simulações e logs de rotina"""
    time.sleep(10)
    
    print("[TESTE] Disparando simulação interna da Mariana com campo de número...", flush=True)
    
    # Atualizamos o teste da Mariana incluindo o campo 'numero' para testar a nova função
    with app.test_client() as simulador:
        simulador.post('/webhook', json={
            "nome": "Mariana",
            "numero": "5521988888888",
            "mensagem": "Olá, gostaria de saber se vocês têm alguma casa de 3 quartos disponível para alugar perto do centro."
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