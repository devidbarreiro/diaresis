# 🎙️ Diaresis API - Speaker Diarization Service

API REST para separación automática de voces en archivos de audio/video usando IA.

🚀 **Auto-deployed via GitHub Actions** ✨

## 🚀 Inicio Rápido

### 1. Configurar token
```bash
echo 'HUGGINGFACE_API_KEY=tu_token' > .env
```

### 2. Levantar servicio
```bash
docker-compose up -d
```

### 3. Verificar
```bash
curl http://localhost:5000/health
```

## 📡 Cómo Funciona la API

### **Flujo de Procesamiento:**

```
1. Cliente sube archivo → POST /upload
2. API genera job_id único
3. Procesamiento asíncrono en background:
   ├─ Conversión de formato (si es video)
   ├─ Preprocesamiento (16kHz mono)
   ├─ División en chunks de 60s
   ├─ Diarización paralela con pyannote.audio
   ├─ Fusión de resultados
   └─ Separación de speakers en archivos WAV
4. Cliente consulta estado → GET /job/{id}
5. Cliente descarga speakers → GET /job/{id}/download/{speaker}
```

### **Arquitectura:**

```
┌─────────────┐
│   Cliente   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────┐
│      Diaresis API (Flask)       │
│  ┌───────────────────────────┐  │
│  │  Gestión de Jobs          │  │
│  │  - Queue                  │  │
│  │  - Estado                 │  │
│  │  - Métricas               │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  Procesamiento Paralelo   │  │
│  │  - ThreadPoolExecutor     │  │
│  │  - Chunks de 60s          │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  pyannote.audio 3.0       │  │
│  │  - Modelo pre-entrenado   │  │
│  │  - CPU/GPU                │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Storage   │
│  uploads/   │
│  output/    │
└─────────────┘
```

## 📋 Endpoints

### **Health Check**
```bash
GET /health
```
Respuesta:
```json
{
  "status": "healthy",
  "gpu_available": false,
  "timestamp": "2025-10-09T10:00:00"
}
```

### **Métricas**
```bash
GET /metrics
```
Respuesta:
```json
{
  "total_requests": 150,
  "successful_jobs": 142,
  "failed_jobs": 8,
  "total_files_processed": 142,
  "average_processing_time": 45.3,
  "success_rate": 94.67
}
```

### **Subir Archivo**
```bash
POST /upload
Content-Type: multipart/form-data

file: archivo.mp4
chunk_duration: 60 (opcional)
max_workers: 2 (opcional)
```
Respuesta:
```json
{
  "job_id": "uuid-123",
  "filename": "archivo.mp4",
  "status": "queued"
}
```

### **Estado del Job**
```bash
GET /job/{job_id}
```
Respuesta:
```json
{
  "id": "uuid-123",
  "status": "completed",
  "progress": 100,
  "result": {
    "speakers_detected": 2,
    "processing_time": 45.3,
    "output_files": ["path/speaker_1.wav", "path/speaker_2.wav"]
  }
}
```

### **Descargar Speaker**
```bash
GET /job/{job_id}/download/{speaker_id}
```
Descarga el archivo WAV del speaker especificado.

### **Listar Jobs**
```bash
GET /jobs
```
Lista todos los jobs procesados.

### **Info del Sistema**
```bash
GET /system
```
Información sobre CPU, GPU y dependencias.

## 🔍 Observabilidad

### **Logs Estructurados**
La API registra todas las operaciones:
```bash
# Ver logs en tiempo real
docker logs -f diaresis-api

# Ver archivo de logs
tail -f api.log
```

Formato de logs:
```
2025-10-09 10:00:00 - INFO - Request: POST /upload - IP: 192.168.1.1
2025-10-09 10:00:00 - INFO - Job abc-123: Iniciando procesamiento
2025-10-09 10:00:45 - INFO - Job abc-123: Completado en 45.3s
2025-10-09 10:00:45 - INFO - Response: /upload - Duration: 0.5s - Status: 200
```

### **Métricas en Tiempo Real**
```bash
curl http://localhost:5000/metrics
```

Métricas disponibles:
- **total_requests**: Total de peticiones recibidas
- **successful_jobs**: Jobs completados exitosamente
- **failed_jobs**: Jobs fallidos
- **total_files_processed**: Archivos procesados
- **average_processing_time**: Tiempo promedio de procesamiento
- **success_rate**: Tasa de éxito (%)

### **Monitoreo de Jobs**
Cada job registra:
- Timestamp de inicio/fin
- Duración total
- Speakers detectados
- Errores (si los hay)
- Información del audio (duración, canales, sample rate)

## 🛠️ Configuración

### **Variables de Entorno (.env)**
```bash
HUGGINGFACE_API_KEY=tu_token_aqui
```

### **Parámetros de Procesamiento**
Al subir un archivo, puedes configurar:

- **chunk_duration** (default: 60): Duración de cada chunk en segundos
- **max_workers** (default: 2): Número de workers paralelos
- **num_speakers** (default: 2): Número esperado de speakers (opcional)

Ejemplo:
```bash
curl -X POST \
  -F "file=@audio.mp4" \
  -F "chunk_duration=90" \
  -F "max_workers=4" \
  http://localhost:5000/upload
```

## 🐳 Docker

### **Comandos Básicos**
```bash
# Iniciar
docker-compose up -d

# Ver logs
docker logs -f diaresis-api

# Detener
docker-compose down

# Reiniciar
docker-compose restart

# Reconstruir
docker-compose build && docker-compose up -d
```

### **Volúmenes**
- `./uploads` - Archivos subidos
- `./output` - Archivos procesados
- `./.env` - Variables de entorno

## 📊 Ejemplo de Uso

### **Python**
```python
import requests

# 1. Subir archivo
with open('podcast.mp4', 'rb') as f:
    response = requests.post('http://localhost:5000/upload', 
                           files={'file': f})
job_id = response.json()['job_id']

# 2. Verificar estado
import time
while True:
    status = requests.get(f'http://localhost:5000/job/{job_id}')
    data = status.json()
    print(f"Progreso: {data['progress']}%")
    
    if data['status'] == 'completed':
        print(f"Speakers detectados: {data['result']['speakers_detected']}")
        break
    
    time.sleep(5)

# 3. Descargar speakers
for i in range(data['result']['speakers_detected']):
    response = requests.get(f'http://localhost:5000/job/{job_id}/download/{i}')
    with open(f'speaker_{i+1}.wav', 'wb') as f:
        f.write(response.content)
```

### **cURL**
```bash
# Subir
JOB_ID=$(curl -X POST -F "file=@audio.mp4" http://localhost:5000/upload | jq -r '.job_id')

# Estado
curl http://localhost:5000/job/$JOB_ID

# Descargar
curl -O http://localhost:5000/job/$JOB_ID/download/0
```

### **JavaScript**
```javascript
// Subir archivo
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:5000/upload', {
    method: 'POST',
    body: formData
});

const { job_id } = await response.json();

// Polling de estado
const checkStatus = async () => {
    const status = await fetch(`http://localhost:5000/job/${job_id}`);
    const data = await status.json();
    
    if (data.status === 'completed') {
        console.log('Completado!', data.result);
    } else {
        setTimeout(checkStatus, 5000);
    }
};

checkStatus();
```

## ⚡ Rendimiento

### **Optimizaciones Implementadas:**
- ✅ Procesamiento paralelo con ThreadPoolExecutor
- ✅ División en chunks de 60s para mejor paralelización
- ✅ Preprocesamiento optimizado (16kHz mono)
- ✅ Modelo pyannote/speaker-diarization-3.0
- ✅ Caché de modelos pre-cargados

### **Tiempos Estimados:**
- Audio de 1 min: ~15-30s
- Audio de 5 min: ~1-2 min
- Audio de 15 min: ~3-5 min

*Nota: Tiempos en CPU. Con GPU T4 puede ser 3-5x más rápido.*

## 🚨 Troubleshooting

### **API no responde**
```bash
docker logs diaresis-api
docker-compose restart
```

### **Job se queda en "processing"**
```bash
# Ver logs del job específico
docker logs diaresis-api | grep "Job abc-123"
```

### **Error de memoria**
Reducir workers en `docker-compose.yml`:
```yaml
command: ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", ...]
```

### **Archivos no se descargan**
```bash
# Verificar permisos
ls -la output/
chmod 755 output/
```

## 📚 Tecnologías

- **Flask** - Framework web
- **pyannote.audio 3.0** - Diarización de speakers
- **PyTorch** - Deep learning
- **torchaudio** - Procesamiento de audio
- **FFmpeg** - Conversión de formatos
- **Gunicorn** - Servidor WSGI
- **Docker** - Containerización

## 📞 Soporte

- **GitHub**: https://github.com/devidbarreiro/diaresis
- **Email**: dev.barreiro@gmail.com

---

**Made with ❤️ for AI-powered video production**