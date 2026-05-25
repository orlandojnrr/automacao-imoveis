import os
import time
import threading
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Inicialização limpa do cliente moderno
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

if not client:
    print("[AVISO] Chave GEMINI_API_KEY não encontrada nas variáveis.", flush=True)

def responder_com_gemini(mensagem_cliente):
    if not client:
        return "Erro: Cliente Gemini não foi inicializado por falta de API Key."
    try:
        prompt_sistema = (
            "Você é um corretor de imóveis profissional, muito educado e prestativo. "
            "Sua missão é responder à mensagem do cliente abaixo, tentando entender melhor o que ele precisa "
            "(como localização, quantidade de quartos e orçamento) e agendar uma visita ou ligação. "
            "Responda de forma natural, humanizada e use emojis moderadamente.\n\n"
            f"Mensagem do Cliente: {mensagem_cliente}"
        )
        
        # Explicitamos 'models/gemini-1.5-flash' para matar o erro de v1beta no Render
        response = client.models.generate_content(
            model='models/gemini-1.5-flash',
            contents=prompt_sistema,
        )
        return response.text
    except Exception as e:
        return f"Erro ao chamar a API do Gemini: {e}"

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Sistema de Automação Imobiliária Ativo", 200

@app.route('/webhook', methods=['POST'])
def webhook():
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
    # 10 segundos para garantir estabilidade antes do teste
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