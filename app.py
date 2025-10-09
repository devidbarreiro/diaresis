#!/usr/bin/env python3
"""
Punto de entrada principal para Diaresis API
"""

import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Importar la aplicación Flask
from api import app, logger

if __name__ == '__main__':
    logger.info("🚀 Iniciando Diaresis API...")
    logger.info("📡 Endpoints disponibles:")
    logger.info("  - POST /upload - Subir archivo de audio")
    logger.info("  - GET /job/<id> - Estado del job")
    logger.info("  - GET /job/<id>/download/<speaker> - Descargar speaker")
    logger.info("  - GET /jobs - Listar todos los jobs")
    logger.info("  - GET /health - Estado de la API")
    logger.info("  - GET /metrics - Métricas de uso")
    logger.info("  - GET /system - Información del sistema")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

