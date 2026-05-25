# 1. Usa a imagem do Python
FROM python:3.11-slim

# 2. Define a pasta dentro do container
WORKDIR /app

# 3. Copia todos os arquivos
COPY . .

# 4. O "-u" força o Python a cuspir os prints na tela IMEDIATAMENTE
CMD ["python", "-u", "main.py"]