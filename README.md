# 🎬 Diaresis - Sistema de Separación de Voces con IA

Sistema automatizado para separación de speakers en archivos de audio/video usando IA.

## 🚀 Características

- **Separación automática de voces** - Identifica y separa múltiples speakers
- **API REST** - Fácil integración con cualquier aplicación
- **Procesamiento paralelo** - Optimizado para velocidad
- **Múltiples formatos** - Soporta MP4, WAV, MP3, M4A, FLAC, etc.
- **Escalable** - Procesa múltiples archivos simultáneamente

## 📋 Requisitos

- Python 3.8+
- FFmpeg
- Token de Hugging Face (para pyannote.audio)

## 🔧 Instalación Rápida con Docker

### 1. Clonar repositorio
```bash
git clone https://github.com/devidbarreiro/diaresis.git
cd diaresis
```

### 2. Configurar token de Hugging Face
```bash
echo 'HUGGINGFACE_API_KEY=tu_token_aqui' > .env
```

### 3. Ejecutar con Docker Compose
```bash
docker-compose up -d
```

### 4. Verificar
```bash
curl http://localhost:5000/health
```

## 🎯 Uso de la API

### Health Check
```bash
curl http://tu-servidor/health
```

### Subir y procesar archivo
```bash
curl -X POST -F "file=@audio.mp4" http://tu-servidor/upload
```

### Ver estado del procesamiento
```bash
curl http://tu-servidor/job/<job_id>
```

### Descargar speaker separado
```bash
curl -O http://tu-servidor/job/<job_id>/download/0
```

## 📡 Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado de la API |
| GET | `/system` | Información del sistema |
| POST | `/upload` | Subir archivo de audio |
| GET | `/job/<id>` | Estado del procesamiento |
| GET | `/job/<id>/download/<speaker>` | Descargar speaker |
| GET | `/jobs` | Listar todos los jobs |

## 🛠️ Uso Local

### Instalación
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Ejecutar API
```bash
python3 speaker_diarization_api.py
```

### Ejecutar script directo
```bash
python3 speaker_diarization.py audio.mp4 --token "tu_token"
```

## 📊 Ejemplos de Uso

### Python
```python
import requests

# Subir archivo
with open('podcast.mp4', 'rb') as f:
    response = requests.post('http://tu-servidor/upload', 
                           files={'file': f})
job_id = response.json()['job_id']

# Verificar estado
status = requests.get(f'http://tu-servidor/job/{job_id}')
print(status.json())

# Descargar speakers
for i in range(2):
    response = requests.get(f'http://tu-servidor/job/{job_id}/download/{i}')
    with open(f'speaker_{i}.wav', 'wb') as f:
        f.write(response.content)
```

### JavaScript
```javascript
// Subir archivo
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://tu-servidor/upload', {
    method: 'POST',
    body: formData
});

const { job_id } = await response.json();

// Verificar estado
const status = await fetch(`http://tu-servidor/job/${job_id}`);
const data = await status.json();
```

## 🔧 Configuración Avanzada

### Parámetros de procesamiento
```bash
curl -X POST \
  -F "file=@audio.mp4" \
  -F "chunk_duration=60" \
  -F "max_workers=4" \
  -F "num_speakers=2" \
  http://tu-servidor/upload
```

### Variables de entorno (.env)
```bash
HUGGINGFACE_API_KEY=tu_token
MAX_WORKERS=4
CHUNK_DURATION=60
```

## 📈 Monitoreo

### Ver logs en tiempo real
```bash
docker logs -f diaresis-api
```

### Estado del contenedor
```bash
docker ps
```

### Reiniciar contenedor
```bash
docker-compose restart
```

## 🚨 Troubleshooting

### API no responde
```bash
# Ver logs
docker logs diaresis-api

# Reiniciar
docker-compose restart
```

### Error de memoria
```bash
# Editar docker-compose.yml y reducir workers
# Cambiar: -w 2 por -w 1

# Reiniciar
docker-compose up -d
```

### Archivos no se procesan
```bash
# Verificar permisos
ls -la uploads/ output/

# Arreglar permisos
chmod 755 uploads/ output/
```

## 📚 Documentación Adicional

- [Docker Guide](DOCKER.md) - Guía completa de Docker
- Ver más detalles en el código fuente

## 💰 Costos Estimados

### Servidor Google Cloud
- **Instancia básica**: ~$20-30/mes
- **Con procesamiento**: ~$0.50-1.00 por proyecto
- **Sin GPU**: Procesamiento en CPU (más lento pero funcional)

## 🎯 Casos de Uso

- **Podcasts** - Separar entrevistador vs invitado
- **Entrevistas** - Aislar voces para edición
- **Contenido educativo** - Separar instructor vs estudiantes
- **Roundtables** - Identificar cada participante
- **Post-producción** - Mezcla profesional por speaker

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la licencia MIT.

## 📞 Contacto

- **Email**: dev.barreiro@gmail.com
- **GitHub**: [@devidbarreiro](https://github.com/devidbarreiro)

## 🙏 Agradecimientos

- [pyannote.audio](https://github.com/pyannote/pyannote-audio) - Motor de diarización
- [Flask](https://flask.palletsprojects.com/) - Framework web
- [PyTorch](https://pytorch.org/) - Framework de ML

---

**Made with ❤️ by devidbarreiro**
