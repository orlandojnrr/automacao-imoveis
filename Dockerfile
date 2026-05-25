# 1. Usa a imagem do Python
FROM python:3.10-slim
# 2. Define a pasta dentro do container
WORKDIR /app
# 3. Copia todos os arquivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
# 4. O "-u" força o Python a cuspir os prints na tela IMEDIATAMENTE
CMD ["python", "-u", "main.py"]