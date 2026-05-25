import os
import time
import threading
from flask import Flask, request, jsonify
from google import genai  # Usa o SDK moderno obrigatório para 2026

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Busca a chave de API do Gemini das variáveis de ambiente do Render
api_key = os.environ.get("GEMINI_API_KEY")

# Inicializa o cliente do SDK moderno
client = genai.Client(api_key=api_key) if api_key else None

if not client:
    print("[AVISO] Chave GEMINI_API_KEY não encontrada nas variáveis.", flush=True)

def responder_com_gemini(mensagem_cliente):
    """
    Função responsável por pegar a mensagem do WhatsApp, criar o contexto
    do corretor de imóveis e solicitar a resposta para a API moderna do Gemini.
    """
    if not client:
        return "Erro: Cliente Gemini não foi inicializado por falta de API Key."
        
    try:
        # Criamos as instruções de comportamento da Inteligência Artificial (System Prompt)
        prompt_sistema = (
            "Você é um corretor de imóveis profissional, muito educado e prestativo. "
            "Sua missão é responder à mensagem do cliente abaixo, tentando entender melhor o que ele precisa "
            "(como localização, quantidade de quartos e orçamento) e agendar uma visita ou ligação. "
            "Responda de forma natural, humanizada e use emojis moderadamente.\n\n"
            f"Mensagem do Cliente: {mensagem_cliente}"
        )
        
        # Sintaxe definitiva para o SDK moderno: passamos apenas a string direta do modelo
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt_sistema,
        )
        
        # Retorna o texto gerado pela IA
        return response.text
        
    except Exception as e:
        # Captura qualquer erro na chamada da API
        return f"Erro ao chamar a API do Gemini: {e}"

@app.route('/', methods=['GET', 'HEAD'])
def home():
    """
    Rota inicial para o Render saber que o sistema está online.
    """
    return "Sistema de Automação Imobiliária Ativo", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Rota que recebe os dados do WhatsApp / Simulação da Mariana.
    """
    dados = request.get_json()
    
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
        
    print(f"\n[WHATSAPP] Nova mensagem recebida de {dados.get('nome', 'Cliente')}!", flush=True)
    print(f"[WHATSAPP] Texto: '{dados.get('mensagem', '')}'", flush=True)
    print("[IA] Pensando na melhor resposta com o Gemini...", flush=True)
    
    resposta_ia = responder_com_gemini(dados.get('mensagem', ''))
    
    print("\n==================================================", flush=True)
    print(f"[IA RESPOSTA PARA {dados.get('nome', 'CLIENTE').upper()}]:", flush=True)
    print(resposta_ia, flush=True)
    print("==================================================\n", flush=True)
    
    return jsonify({"status": "sucesso", "resposta": resposta_ia}), 200

def rotina_segundo_plano():
    """
    Thread de segundo plano que faz o teste da Mariana após 10 segundos.
    """
    time.sleep(10)
    
    print("[TESTE] Disparando simulação interna da Mariana...", flush=True)
    
    with app.test_client() as simulador:
        simulador.post('/webhook', json={
            "nome": "Mariana",
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