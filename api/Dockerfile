# Dockerfile para Diaresis API
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copiar código de la aplicación
COPY app.py .
COPY src/ ./src/

# Crear directorios necesarios
RUN mkdir -p uploads output temp

# Exponer puerto
EXPOSE 5000

# Variables de entorno
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
