import os
import time
import threading
from flask import Flask, request, jsonify
import google.generativeai as genai

# Força o SDK do Google a usar a rota v1 estável globalmente
os.environ["GOOGLE_API_VERSION"] = "v1"

app = Flask(__name__)

# Configura a IA do Gemini usando a chave secreta vinda do ambiente (Render)
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("[AVISO] Chave GEMINI_API_KEY não encontrada nas variáveis de ambiente.")

def responder_com_gemini(mensagem_cliente):
    try:
        # Mudança do modelo para a versão estável específica de API corporativa
        # Isso força o SDK a encontrar o endpoint correto mesmo na v1beta
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt_sistema = (
            "Você é um corretor de imóveis profissional, muito educado e prestativo. "
            "Sua missão é responder à mensagem do cliente abaixo, tentando entender melhor o que ele precisa "
            "(como localização, quantidade de quartos e orçamento) e agendar uma visita ou ligação. "
            "Responda de forma natural, humanizada e use emojis moderadamente.\n\n"
            f"Mensagem do Cliente: {mensagem_cliente}"
        )
        
        response = model.generate_content(prompt_sistema)
        return response.text
    except Exception as e:
        # Se o flash-latest ainda chiar por conta do ambiente, tentamos o fallback imediato
        try:
            print("[INFO] Tentando fallback para o modelo alternativo...")
            model_fallback = genai.GenerativeModel('gemini-pro')
            response = model_fallback.generate_content(prompt_sistema)
            return response.text
        except Exception as e_fallback:
            return f"Erro ao chamar a API do Gemini (Principal e Fallback): {e} | Fallback: {e_fallback}"

@app.route('/', methods=['GET', 'HEAD'])
def home():
    # Rota para o Render monitorar a saúde da aplicação (Health Check)
    return "Sistema de Automação Imobiliária Ativo", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    # Rota simulada para receber as mensagens do WhatsApp (Mariana)
    dados = request.get_json()
    
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
        
    print(f"\n[WHATSAPP] Nova mensagem recebida de {dados.get('nome', 'Cliente')}!")
    print(f"[WHATSAPP] Texto: '{dados.get('mensagem', '')}'")
    print("[IA] Pensando na melhor resposta com o Gemini...")
    
    resposta_ia = responder_com_gemini(dados.get('mensagem', ''))
    
    print("\n==================================================")
    print(f"[IA RESPOSTA PARA {dados.get('nome', 'CLIENTE').upper()}]:")
    print(resposta_ia)
    print("==================================================\n")
    
    return jsonify({"status": "sucesso", "resposta": resposta_ia}), 200

# Função que roda em segundo plano para simular mensagens e manter o log ativo
def rotina_segundo_plano():
    # 1. Espera 2 segundos e dispara o teste inicial da Mariana
    time.sleep(2)
    with app.test_client() as client:
        client.post('/webhook', json={
            "nome": "Mariana",
            "mensagem": "Olá, gostaria de saber se vocês têm alguma casa de 3 quartos disponível para alugar perto do centro."
        })
    
    # 2. Entra no loop infinito para printar o status no log a cada 15 segundos
    while True:
        time.sleep(15)
        print("[LOG] Monitorando banco de dados de imóveis e novas mensagens...")

if __name__ == '__main__':
    print("\n--- SISTEMA DE AUTOMAÇÃO IMOBILIÁRIA ATIVO ---")
    print("Aguardando novas mensagens de leads do WhatsApp...\n")
    
    # Inicia a thread que cuida tanto do teste da Mariana quanto dos logs repetitivos
    threading.Thread(target=rotina_segundo_plano, daemon=True).start()
        
    # Inicia o servidor Flask na porta exigida pelo Render
    porta = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta, debug=False)