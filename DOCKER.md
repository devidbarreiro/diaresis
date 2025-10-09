# 🐳 Docker - Diaresis API

## 🚀 Inicio Rápido

### 1. Construir y ejecutar con Docker Compose
```bash
docker-compose up -d
```

### 2. Verificar que está funcionando
```bash
curl http://localhost:5000/health
```

### 3. Ver logs
```bash
docker logs -f diaresis-api
```

## 📋 Comandos Útiles

### Detener el contenedor
```bash
docker-compose down
```

### Reiniciar el contenedor
```bash
docker-compose restart
```

### Ver estado
```bash
docker ps
```

### Reconstruir imagen
```bash
docker-compose build
docker-compose up -d
```

### Limpiar todo
```bash
docker-compose down -v
docker system prune -a
```

## 🔧 Configuración

### Variables de entorno (.env)
```bash
HUGGINGFACE_API_KEY=tu_token_aqui
```

### Volúmenes montados
- `./uploads` - Archivos subidos
- `./output` - Archivos procesados
- `./.env` - Variables de entorno

## 🌐 Acceso

- **API Local**: http://localhost:5000
- **API Externa**: http://51.91.166.216:5000 (si el firewall lo permite)

## 📊 Endpoints

- `GET /health` - Estado de la API
- `POST /upload` - Subir archivo
- `GET /job/<id>` - Estado del job
- `GET /job/<id>/download/<speaker>` - Descargar speaker
- `GET /jobs` - Listar jobs
- `GET /system` - Info del sistema

## 🔍 Troubleshooting

### El contenedor no inicia
```bash
docker logs diaresis-api
```

### Problemas de permisos
```bash
chmod 755 uploads output
```

### Limpiar archivos antiguos
```bash
find uploads -type f -mtime +7 -delete
find output -type f -mtime +7 -delete
```

## 🔄 Actualizar

```bash
git pull
docker-compose build
docker-compose up -d
```
