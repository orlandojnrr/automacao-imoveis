import os
import time
import threading
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Busca a chave de API do Gemini das variáveis de ambiente do Render
api_key = os.environ.get("GEMINI_API_KEY")

# Inicializa o cliente moderno da Google GenAI usando a chave encontrada
# Se a chave não existir, o cliente fica como None (nulo)
client = genai.Client(api_key=api_key) if api_key else None

# Alerta no terminal caso você tenha esquecido de configurar a API Key no Render
if not client:
    print("[AVISO] Chave GEMINI_API_KEY não encontrada nas variáveis.", flush=True)

def responder_com_gemini(mensagem_cliente):
    """
    Função responsável por pegar a mensagem do WhatsApp, criar o contexto
    do corretor de imóveis e solicitar a resposta para a API do Gemini.
    """
    # Valida se o cliente da API foi inicializado corretamente
    if not client:
        return "Erro: Cliente Gemini não foi inicializado por falta de API Key."
        
    try:
        # Criamos as instruções de comportamento da Inteligência Artificial (System Prompt)
        # e injetamos a mensagem que a Mariana (ou outro cliente) enviou.
        prompt_sistema = (
            "Você é um corretor de imóveis profissional, muito educado e prestativo. "
            "Sua missão é responder à mensagem do cliente abaixo, tentando entender melhor o que ele precisa "
            "(como localização, quantidade de quartos e orçamento) e agendar uma visita ou ligação. "
            "Responda de forma natural, humanizada e use emojis moderadamente.\n\n"
            f"Mensagem do Cliente: {mensagem_cliente}"
        )
        
        # Chamada oficial ao SDK moderno da Google.
        # CORREÇÃO: Usamos apenas 'gemini-1.5-flash' sem o prefixo 'models/'
        response = client.models.generate_content(
            model=types.SupportedModels.GEMINI_1_5_FLASH,
            contents=prompt_sistema,
        )
        
        # Retorna o texto puro gerado pela IA
        return response.text
        
    except Exception as e:
        # Se a API da Google rejeitar ou der qualquer erro, captura e exibe aqui
        return f"Erro ao chamar a API do Gemini: {e}"

@app.route('/', methods=['GET', 'HEAD'])
def home():
    """
    Rota inicial (página que carrega ao acessar a URL principal).
    O Render usa isso para saber que o seu sistema está vivo e funcionando.
    """
    return "Sistema de Automação Imobiliária Ativo", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Esta é a rota principal que o WhatsApp (ou a nossa simulação) vai acionar.
    Ela recebe os dados do cliente, passa para a IA e devolve a resposta.
    """
    # Captura os dados em formato JSON que foram enviados na requisição
    dados = request.get_json()
    
    # Se não houver dados, retorna um erro 400 (Bad Request)
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
        
    # Logs informativos para você acompanhar a movimentação pelo painel do Render
    print(f"\n[WHATSAPP] Nova mensagem recebida de {dados.get('nome', 'Cliente')}!", flush=True)
    print(f"[WHATSAPP] Texto: '{dados.get('mensagem', '')}'", flush=True)
    print("[IA] Pensando na melhor resposta com o Gemini...", flush=True)
    
    # Chama a função que criamos ali em cima para obter a resposta do Gemini
    resposta_ia = responder_com_gemini(dados.get('mensagem', ''))
    
    # Exibe a resposta final da IA de forma organizada nos logs do Render
    print("\n==================================================", flush=True)
    print(f"[IA RESPOSTA PARA {dados.get('nome', 'CLIENTE').upper()}]:", flush=True)
    print(resposta_ia, flush=True)
    print("==================================================\n", flush=True)
    
    # Devolve a resposta estruturada para quem chamou o Webhook
    return jsonify({"status": "sucesso", "resposta": resposta_ia}), 200

def rotina_segundo_plano():
    """
    Uma função de segundo plano (Thread). Ela roda em paralelo ao servidor Flask
    para fazer testes automáticos e monitoramentos sem travar o sistema principal.
    """
    # Aguarda 10 segundos após o sistema iniciar para garantir que o Flask já subiu
    time.sleep(10)
    
    print("[TESTE] Disparando simulação interna da Mariana...", flush=True)
    
    # Cria um cliente de teste interno para simular uma requisição real vinda do WhatsApp
    with app.test_client() as simulador:
        simulador.post('/webhook', json={
            "nome": "Mariana",
            "mensagem": "Olá, gostaria de saber se vocês têm alguma casa de 3 quartos disponível para alugar perto do centro."
        })
    
    # Loop infinito simulando um monitoramento contínuo a cada 15 segundos
    while True:
        time.sleep(15)
        print("[LOG] Monitorando banco de dados de imóveis e novas mensagens...", flush=True)

if __name__ == '__main__':
    # Mensagens iniciais de inicialização do script
    print("\n--- SISTEMA DE AUTOMAÇÃO IMOBILIÁRIA ATIVO ---", flush=True)
    print("Aguardando novas mensagens de leads do WhatsApp...\n", flush=True)
    
    # Inicia a função 'rotina_segundo_plano' em uma Thread separada (daemon=True)
    # Isso impede que o loop infinito do 'while True' trave a inicialização do Flask
    threading.Thread(target=rotina_segundo_plano, daemon=True).start()
        
    # Define a porta do servidor. O Render define isso automaticamente na variável PORT.
    # Caso não encontre (rodando local, por exemplo), ele usa a porta 10000 por padrão.
    porta = int(os.environ.get("PORT", 10000))
    
    # Inicia o servidor web Flask de forma pública ('0.0.0.0') na porta correta
    app.run(host='0.0.0.0', port=porta, debug=False, use_reloader=False)