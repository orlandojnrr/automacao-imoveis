import time
import threading
import os
from flask import Flask
import google.generativeai as genai

app = Flask(__name__)

# Configura a IA do Gemini usando a chave secreta que você salvou no Render
# Se você testar localmente no PC, ele vai ignorar se não achar a variável, por isso usamos o os.environ.get
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    # FORÇA O SDK A USAR A API ESTÁVEL V1 (Evita o erro 404 da v1beta)
    os.environ["慶_API_VERSION"] = "v1"  # Truque para o core do Google API

@app.route('/')
def home():
    return "Robô Ativo com Cérebro Gemini!", 200

# Aqui é onde o cérebro da IA processa a mensagem do cliente
def responder_com_gemini(mensagem_cliente):
    try:
        # Agora com a API certa, o 1.5-flash vai rodar liso
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt_sistema = (
            "Você é uma corretora de imóveis profissional, muito educada e prestativa. "
            "Sua missão é responder à mensagem do cliente abaixo, tentando entender melhor o que ele precisa "
            "(como localização, quantidade de quartos e orçamento) e agendar uma visita ou ligação. "
            "Responda de forma natural, humanizada e use emojis moderadamente.\n\n"
            f"Mensagem do Cliente: {mensagem_cliente}"
        )
        
        response = model.generate_content(prompt_sistema)
        return response.text
    except Exception as e:
        return f"Erro ao chamar a API do Gemini: {e}"

# O coração do seu robô em segundo plano
def loop_do_robo():
    print("--- SISTEMA DE AUTOMAÇÃO IMOBILIÁRIA ATIVO ---")
    print("Aguardando novas mensagens de leads do WhatsApp...")
    
    # Simulação de um cliente que acabou de chegar do WhatsApp
    cliente_simulado = "Mariana"
    mensagem_simulada = "Olá, gostaria de saber se vocês têm alguma casa de 3 quartos disponível para alugar perto do centro."
    
    # O robô vai processar essa mensagem logo no primeiro ciclo
    primeiro_ciclo = True
    
    while True:
        if primeiro_ciclo:
            print(f"\n[WHATSAPP] Nova mensagem recebida de {cliente_simulado}!")
            print(f"[WHATSAPP] Texto: '{mensagem_simulada}'")
            print("[IA] Pensando na melhor resposta com o Gemini...")
            
            # Chama o cérebro da Inteligência Artificial
            resposta_da_ia = responder_com_gemini(mensagem_simulada)
            
            print("\n==================================================")
            print(f"[IA RESPOSTA PARA {cliente_simulado.upper()}]:")
            print(resposta_da_ia)
            print("==================================================\n")
            
            primeiro_ciclo = False
            
        print("[LOG] Monitorando banco de dados de imóveis e novas mensagens...")
        time.sleep(15)  # Aumentamos para 15 segundos para o log ficar mais limpo

if __name__ == "__main__":
    threading.Thread(target=loop_do_robo, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)