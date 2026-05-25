import os
import time
import threading
from flask import Flask, request, jsonify
from google import genai  # Importa o SDK moderno oficial da Google para 2026

# Inicializa o aplicativo Flask para gerenciar as rotas HTTP (Webhooks)
app = Flask(__name__)

# Busca a chave de autenticação da API do Gemini configurada nas variáveis de ambiente do Render
api_key = os.environ.get("GEMINI_API_KEY")

# Inicializa o cliente de conexão apontando explicitamente para a API de produção v1.
# Isso evita que a biblioteca use a rota 'v1beta' por padrão, onde modelos antigos foram desativados.
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
    Função com sistema de contingência (Fallback). Ela testa uma lista de modelos
    vigentes para garantir a estabilidade caso a Google mude as versões suportadas.
    """
    if not client:
        return "Erro: Cliente Gemini não foi inicializado por falta de API Key."
        
    # Define as instruções de persona (System Prompt) ditando como a IA deve agir e falar
    prompt_sistema = (
        "Você é um corretor de imóveis profissional, muito educado e prestativo. "
        "Sua missão é responder à mensagem do cliente abaixo, tentando entender melhor o que ele precisa "
        "(como localização, quantidade de quartos e orçamento) e agendar uma visita ou ligação. "
        "Responda de forma natural, humanizada e use emojis moderadamente.\n\n"
        f"Mensagem do Cliente: {mensagem_cliente}"
    )

    # Lista ordenada de modelos (priorizando o modelo mais atual em 2026)
    modelos_para_testar = ['gemini-2.5-flash', 'gemini-1.5-flash']
    ultimo_erro = None

    # Loop que tenta enviar o prompt para cada modelo da lista até que um responda com sucesso
    for modelo in modelos_para_testar:
        try:
            print(f"[IA] Tentando conectar usando o modelo: {modelo}...", flush=True)
            response = client.models.generate_content(
                model=modelo,
                contents=prompt_sistema,
            )
            # Se a requisição funcionar, interrompe o loop e retorna o texto da resposta
            return response.text
        except Exception as e:
            # Se falhar, armazena o erro ocorrido e continua para o próximo modelo da lista
            ultimo_erro = e
            print(f"[AVISO] O modelo {modelo} não respondeu. Tentando o próximo...", flush=True)
            continue
            
    # Caso nenhum dos modelos consiga responder, retorna o relatório do erro final encontrado
    return f"Erro crítico: Nenhum modelo disponível respondeu na API v1. Detalhes: {ultimo_erro}"

@app.route('/', methods=['GET', 'HEAD'])
def home():
    """
    Rota raiz do servidor. Serve para o Render fazer a verificação de saúde (Health Check).
    O Render envia requisições constantes aqui para saber se a aplicação continua online.
    """
    return "Sistema de Automação Imobiliária Ativo", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Rota principal que recebe as mensagens do WhatsApp encaminhadas por sua API de chat.
    Ela espera um formato JSON contendo os dados do contato e o texto enviado.
    """
    dados = request.get_json()  # Captura o corpo da requisição HTTP enviado no formato JSON
    
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
        
    # Imprime no console do Render as informações estruturadas da nova mensagem recebida
    print(f"\n[WHATSAPP] Nova mensagem recebida de {dados.get('nome', 'Cliente')}!", flush=True)
    print(f"[WHATSAPP] Texto: '{dados.get('mensagem', '')}'", flush=True)
    print("[IA] Iniciando chamada com os servidores da Google Gemini...", flush=True)
    
    # Aciona a inteligência artificial para formular uma resposta com base no texto recebido
    resposta_ia = responder_com_gemini(dados.get('mensagem', ''))
    
    # Formata a exibição do retorno gerado pela IA nos logs para facilitar seu monitoramento visual
    print("\n==================================================", flush=True)
    print(f"[IA RESPOSTA PARA {dados.get('nome', 'CLIENTE').upper()}]:", flush=True)
    print(resposta_ia, flush=True)
    print("==================================================\n", flush=True)
    
    # Retorna para o remetente da requisição uma confirmação de sucesso com o texto gerado
    return jsonify({"status": "sucesso", "resposta": resposta_ia}), 200

def rotina_segundo_plano():
    """
    Função executada de forma assíncrona (Thread Paralela). Ela cuida de rotinas e tarefas
    que precisam rodar sem bloquear o funcionamento principal das rotas do Flask.
    """
    # Pausa a execução deste bloco por 10 segundos para dar tempo do Flask inicializar por completo
    time.sleep(10)
    
    print("[TESTE] Disparando simulação interna da Mariana...", flush=True)
    
    # O 'app.test_client()' cria um simulador HTTP interno. Com ele, simulamos uma requisição
    # idêntica a que sua API do WhatsApp faria, disparando um gatilho de teste automático.
    with app.test_client() as simulador:
        simulador.post('/webhook', json={
            "nome": "Mariana",
            "mensagem": "Olá, gostaria de saber se vocês têm alguma casa de 3 quartos disponível para alugar perto do centro."
        })
    
    # Cria um loop perpétuo (infinito) que simula o monitoramento em segundo plano do seu sistema
    while True:
        # Pausa por 15 segundos entre cada checagem para evitar consumo excessivo de processamento
        time.sleep(15)
        # O 'flush=True' força o Python a enviar o texto imediatamente para o terminal do Render
        print("[LOG] Monitorando banco de dados de imóveis e novas mensagens...", flush=True)

# Ponto de entrada oficial do script Python
if __name__ == '__main__':
    print("\n--- SISTEMA DE AUTOMAÇÃO IMOBILIÁRIA ATIVO ---", flush=True)
    print("Aguardando novas mensagens de leads do WhatsApp...\n", flush=True)
    
    # Inicializa a função de segundo plano em um canal paralelo (Thread).
    # O parâmetro 'daemon=True' garante que essa tarefa seja encerrada caso o aplicativo Flask pare.
    threading.Thread(target=rotina_segundo_plano, daemon=True).start()
        
    # Define a porta de escuta do servidor. Busca a variável dinâmica do Render ou adota a 10000 por padrão.
    porta = int(os.environ.get("PORT", 10000))
    
    # Inicia o servidor web Flask para escutar em todos os endereços de rede ('0.0.0.0') na porta definida.
    # O 'use_reloader=False' é crucial para evitar que a Thread de segundo plano seja disparada duas vezes.
    app.run(host='0.0.0.0', port=porta, debug=False, use_reloader=False)