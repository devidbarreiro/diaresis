#!/usr/bin/env python3
"""
API REST para Speaker Diarization con procesamiento en GPU
Permite subir archivos de audio y recibir resultados procesados
"""

import os
import sys
import json
import uuid
import tempfile
import threading
import logging
from pathlib import Path
from datetime import datetime
import time
from functools import wraps

# Importar funciones del módulo de diarización
import speaker_diarization

load_env_token = speaker_diarization.load_env_token
check_dependencies = speaker_diarization.check_dependencies
get_audio_info = speaker_diarization.get_audio_info
print_audio_info = speaker_diarization.print_audio_info
preprocess_audio = speaker_diarization.preprocess_audio
split_audio_into_chunks = speaker_diarization.split_audio_into_chunks
run_parallel_diarization = speaker_diarization.run_parallel_diarization
merge_chunk_results = speaker_diarization.merge_chunk_results
separate_speakers_optimized = speaker_diarization.separate_speakers_optimized
load_audio_file = speaker_diarization.load_audio_file

# Flask para API REST
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
import torch

app = Flask(__name__)

# Configuración CORS permisiva para permitir peticiones desde cualquier origen
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Permite todos los orígenes (Vercel, v0.dev, localhost, etc.)
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "expose_headers": ["Content-Disposition", "Content-Length"],
        "supports_credentials": False,
        "max_age": 3600  # Cache preflight requests por 1 hora
    }
})

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuración
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac', 'aac', 'ogg', 'mp4', 'avi', 'mov'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

# Crear directorios necesarios
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs('temp', exist_ok=True)

# Almacenamiento de jobs y métricas
jobs = {}
job_lock = threading.Lock()
metrics = {
    'total_requests': 0,
    'successful_jobs': 0,
    'failed_jobs': 0,
    'total_processing_time': 0,
    'total_files_processed': 0
}
metrics_lock = threading.Lock()

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Decorador para logging de requests
def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"Request: {request.method} {request.path} - IP: {request.remote_addr}")
        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Response: {request.path} - Duration: {duration:.2f}s - Status: 200")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error: {request.path} - Duration: {duration:.2f}s - Error: {str(e)}")
            raise
    return decorated_function

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_job_status(job_id):
    """Obtiene el estado de un job"""
    with job_lock:
        return jobs.get(job_id, None)

def update_job_status(job_id, status, progress=0, error=None, result=None):
    """Actualiza el estado de un job"""
    with job_lock:
        if job_id in jobs:
            jobs[job_id].update({
                'status': status,
                'progress': progress,
                'error': error,
                'result': result,
                'updated_at': datetime.now().isoformat()
            })

def process_audio_job(job_id, file_path, config):
    """Procesa un archivo de audio en un hilo separado"""
    start_time = time.time()
    try:
        logger.info(f"Job {job_id}: Iniciando procesamiento de {Path(file_path).name}")
        
        # Actualizar estado a procesando
        update_job_status(job_id, 'processing', 10)
        
        # Cargar token
        token_hf = load_env_token()
        if not token_hf:
            raise ValueError("No se encontró token de Hugging Face")
        
        # Verificar GPU
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Job {job_id}: Usando dispositivo: {device}")
        
        # Cargar audio
        update_job_status(job_id, 'processing', 20)
        logger.info(f"Job {job_id}: Cargando audio")
        waveform, sample_rate = load_audio_file(file_path)
        
        # Información del audio
        audio_info = get_audio_info(waveform, sample_rate)
        logger.info(f"Job {job_id}: Audio info - Duración: {audio_info['duration']:.2f}s, Canales: {audio_info['channels']}")
        
        # Preprocesar
        update_job_status(job_id, 'processing', 30)
        waveform, sample_rate = preprocess_audio(waveform, sample_rate)
        
        # Dividir en chunks
        update_job_status(job_id, 'processing', 40)
        chunk_duration = config.get('chunk_duration', 60)
        chunks = split_audio_into_chunks(waveform, sample_rate, chunk_duration, overlap=1)
        logger.info(f"Job {job_id}: Creados {len(chunks)} chunks de {chunk_duration}s")
        
        # Procesamiento paralelo
        update_job_status(job_id, 'processing', 50)
        max_workers = config.get('max_workers', 2)
        chunk_results = run_parallel_diarization(chunks, token_hf, device, max_workers)
        
        # Combinar resultados
        update_job_status(job_id, 'processing', 80)
        speakers = merge_chunk_results(chunk_results)
        logger.info(f"Job {job_id}: Detectados {len(speakers)} speakers")
        
        # Separar speakers
        update_job_status(job_id, 'processing', 90)
        output_dir, nombre_base = separate_speakers_optimized(waveform, sample_rate, speakers, file_path)
        
        # Preparar resultado
        processing_time = time.time() - start_time
        result = {
            'job_id': job_id,
            'filename': Path(file_path).name,
            'audio_info': audio_info,
            'speakers_detected': len(speakers),
            'speakers': list(speakers.keys()),
            'output_files': [],
            'processing_time': processing_time
        }
        
        # Listar archivos generados
        for i in range(1, len(speakers) + 1):
            output_file = output_dir / f"{nombre_base}_persona_{i}.wav"
            if output_file.exists():
                result['output_files'].append(str(output_file))
        
        # Completar job
        update_job_status(job_id, 'completed', 100, result=result)
        
        # Actualizar métricas
        with metrics_lock:
            metrics['successful_jobs'] += 1
            metrics['total_processing_time'] += processing_time
            metrics['total_files_processed'] += 1
        
        logger.info(f"Job {job_id}: Completado en {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error - {str(e)}", exc_info=True)
        update_job_status(job_id, 'failed', error=str(e))
        
        # Actualizar métricas
        with metrics_lock:
            metrics['failed_jobs'] += 1

@app.route('/', methods=['GET'])
def index():
    """Endpoint raíz - Redirige a la app de Vercel"""
    from flask import redirect
    
    # URL de tu app en Vercel (cámbiala por la tuya)
    VERCEL_APP_URL = os.getenv('VERCEL_APP_URL', 'https://diaresis.vercel.app')
    
    # Si es una petición desde el navegador, redirigir
    user_agent = request.headers.get('User-Agent', '')
    if 'Mozilla' in user_agent or 'Chrome' in user_agent:
        return redirect(VERCEL_APP_URL)
    
    # Si es una petición de API (curl, fetch, etc), devolver info
    return jsonify({
        'name': 'Diaresis API',
        'version': '1.0.0',
        'description': 'API de diarización de speakers con IA',
        'app_url': VERCEL_APP_URL,
        'endpoints': {
            'health': '/health',
            'metrics': '/metrics',
            'upload': 'POST /upload',
            'job_status': 'GET /job/<job_id>',
            'download_speaker': 'GET /job/<job_id>/download/<speaker_id>',
            'list_jobs': 'GET /jobs',
            'system_info': 'GET /system'
        },
        'docs': 'https://github.com/devidbarreiro/diaresis',
        'status': 'operational'
    })

@app.route('/health', methods=['GET'])
@log_request
def health_check():
    """Endpoint de salud de la API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'gpu_available': torch.cuda.is_available(),
        'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'dependencies': check_dependencies()
    })

@app.route('/metrics', methods=['GET'])
@log_request
def get_metrics():
    """Endpoint para obtener métricas de la API"""
    with metrics_lock:
        avg_processing_time = (metrics['total_processing_time'] / metrics['total_files_processed'] 
                              if metrics['total_files_processed'] > 0 else 0)
        
        return jsonify({
            'total_requests': metrics['total_requests'],
            'successful_jobs': metrics['successful_jobs'],
            'failed_jobs': metrics['failed_jobs'],
            'total_files_processed': metrics['total_files_processed'],
            'total_processing_time': round(metrics['total_processing_time'], 2),
            'average_processing_time': round(avg_processing_time, 2),
            'success_rate': round((metrics['successful_jobs'] / (metrics['successful_jobs'] + metrics['failed_jobs']) * 100) 
                                 if (metrics['successful_jobs'] + metrics['failed_jobs']) > 0 else 0, 2)
        })

@app.route('/upload', methods=['POST'])
@log_request
def upload_file():
    """Endpoint para subir archivos de audio"""
    with metrics_lock:
        metrics['total_requests'] += 1
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Generar job ID único
    job_id = str(uuid.uuid4())
    
    # Guardar archivo
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(file_path)
    
    # Configuración por defecto
    config = {
        'chunk_duration': int(request.form.get('chunk_duration', 60)),
        'max_workers': int(request.form.get('max_workers', 2)),
        'num_speakers': int(request.form.get('num_speakers', 2))
    }
    
    # Crear job
    with job_lock:
        jobs[job_id] = {
            'id': job_id,
            'filename': filename,
            'file_path': file_path,
            'config': config,
            'status': 'queued',
            'progress': 0,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
    
    # Iniciar procesamiento en hilo separado
    thread = threading.Thread(target=process_audio_job, args=(job_id, file_path, config))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'filename': filename,
        'status': 'queued',
        'message': 'File uploaded successfully, processing started'
    })

@app.route('/job/<job_id>', methods=['GET'])
def get_job_status_endpoint(job_id):
    """Endpoint para obtener el estado de un job"""
    job = get_job_status(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    response = {
        'id': job['id'],
        'filename': job['filename'],
        'status': job['status'],
        'progress': job['progress'],
        'created_at': job['created_at'].isoformat(),
        'updated_at': job['updated_at'].isoformat()
    }
    
    if job.get('error'):
        response['error'] = job['error']
    
    if job.get('result'):
        response['result'] = job['result']
    
    return jsonify(response)

@app.route('/job/<job_id>/download/<int:speaker_id>', methods=['GET'])
def download_speaker_file(job_id, speaker_id):
    """Endpoint para descargar archivos de speaker específicos"""
    job = get_job_status(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    result = job.get('result')
    if not result or speaker_id >= len(result['output_files']):
        return jsonify({'error': 'Speaker file not found'}), 404
    
    file_path = result['output_files'][speaker_id]
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found on disk'}), 404
    
    return send_file(file_path, as_attachment=True, download_name=f"speaker_{speaker_id + 1}.wav")

@app.route('/jobs', methods=['GET'])
def list_jobs():
    """Endpoint para listar todos los jobs"""
    with job_lock:
        job_list = []
        for job_id, job in jobs.items():
            job_list.append({
                'id': job['id'],
                'filename': job['filename'],
                'status': job['status'],
                'progress': job['progress'],
                'created_at': job['created_at'].isoformat(),
                'updated_at': job['updated_at'].isoformat()
            })
        
        return jsonify({'jobs': job_list})

@app.route('/system', methods=['GET'])
def system_info():
    """Endpoint para obtener información del sistema"""
    return jsonify({
        'system_info': {
            'cpu_cores': os.cpu_count(),
            'gpu_available': torch.cuda.is_available(),
            'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            'gpu_memory': torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else None
        },
        'dependencies': check_dependencies(),
        'active_jobs': len([j for j in jobs.values() if j['status'] in ['queued', 'processing']])
    })

@app.errorhandler(413)
def too_large(e):
    """Manejo de archivos demasiado grandes"""
    return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413

@app.errorhandler(500)
def internal_error(e):
    """Manejo de errores internos"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Verificar dependencias
    missing = check_dependencies()
    if missing:
        print(f"❌ Faltan dependencias: {', '.join(missing)}")
        print("💡 Instala con: pip install flask flask-cors")
        sys.exit(1)
    
    print("🚀 Iniciando API de Speaker Diarization...")
    print("📡 Endpoints disponibles:")
    print("  - POST /upload - Subir archivo de audio")
    print("  - GET /job/<id> - Estado del job")
    print("  - GET /job/<id>/download/<speaker> - Descargar speaker")
    print("  - GET /jobs - Listar todos los jobs")
    print("  - GET /health - Estado de la API")
    print("  - GET /system - Información del sistema")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
