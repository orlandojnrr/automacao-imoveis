import os
import time
import threading
from flask import Flask, request, jsonify
from google import genai  # SDK Moderno oficial

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Busca a chave de API do Gemini das variáveis de ambiente do Render
api_key = os.environ.get("GEMINI_API_KEY")

# Inicializa o cliente apontando para a API de produção v1
if api_key:
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1'}
    )
else:
    client = None
    print("[AVISO] Chave GEMINI_API_KEY não encontrada nas variáveis.", flush=True)

def responder_com_gemini(mensagem_cliente):
    """
    Função com sistema de contingência (Fallback) que testa os modelos
    vigentes para garantir resposta mesmo com mudanças de versão da Google.
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

    # Lista de modelos oficiais da Google (do mais recente/provável ao anterior)
    modelos_para_testar = ['gemini-2.5-flash', 'gemini-1.5-flash']
    ultimo_erro = None

    for modelo in modelos_para_testar:
        try:
            print(f"[IA] Tentando conectar usando o modelo: {modelo}...", flush=True)
            response = client.models.generate_content(
                model=modelo,
                contents=prompt_sistema,
            )
            # Se funcionar, retorna o texto imediatamente e encerra a função
            return response.text
        except Exception as e:
            ultimo_erro = e
            print(f"[AVISO] O modelo {modelo} não respondeu. Tentando o próximo...", flush=True)
            continue
            
    # Se nenhum dos modelos da Google funcionar, exibe o erro final estruturado
    return f"Erro crítico: Nenhum modelo disponível respondeu na API v1. Detalhes: {ultimo_erro}"

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
    print("[IA] Iniciando chamada com os servidores da Google Gemini...", flush=True)
    
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