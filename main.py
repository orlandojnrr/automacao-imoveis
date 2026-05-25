import time
import threading
from flask import Flask

app = Flask(__name__)

# O site fake que o Render precisa ver para manter o robô vivo de graça
@app.route('/')
def home():
    return "Robô Ativo!", 200

# O coração do seu robô imobiliário continua aqui dentro
def loop_do_robo():
    print("--- SISTEMA DE AUTOMAÇÃO IMOBILIÁRIA ATIVO ---")
    print("Aguardando novas mensagens de leads do WhatsApp...")
    while True:
        print("[LOG] Monitorando banco de dados de imóveis e mensagens...")
        time.sleep(10)

if __name__ == "__main__":
    # Inicia o robô em segundo plano (Thread separada)
    threading.Thread(target=loop_do_robo, daemon=True).start()

    # Inicia o servidor web na porta padrão que o Render exige
    app.run(host="0.0.0.0", port=10000)