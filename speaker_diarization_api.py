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
from pathlib import Path
from datetime import datetime
import time

# Importar funciones del script original
import importlib.util
spec = importlib.util.spec_from_file_location("speaker_diarization", "speaker_diarization.py")
speaker_diarization = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speaker_diarization)

load_env_token = speaker_diarization.load_env_token
check_dependencies = speaker_diarization.check_dependencies
get_audio_info = speaker_diarization.get_audio_info
print_audio_info = speaker_diarization.print_audio_info
preprocess_audio = speaker_diarization.preprocess_audio
split_audio_into_chunks = speaker_diarization.split_audio_into_chunks
run_parallel_diarization = speaker_diarization.run_parallel_diarization
merge_chunk_results = speaker_diarization.merge_chunk_results
separate_speakers_optimized = speaker_diarization.separate_speakers_optimized
print_system_info = speaker_diarization.print_system_info
load_audio_file = speaker_diarization.load_audio_file

# Flask para API REST
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
import torch

app = Flask(__name__)
CORS(app)  # Permitir CORS para frontend

# Configuración
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac', 'aac', 'ogg', 'mp4', 'avi', 'mov'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

# Crear directorios necesarios
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs('temp', exist_ok=True)

# Almacenamiento de jobs
jobs = {}
job_lock = threading.Lock()

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

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
    try:
        # Actualizar estado a procesando
        update_job_status(job_id, 'processing', 10)
        
        # Cargar token
        token_hf = load_env_token()
        if not token_hf:
            raise ValueError("No se encontró token de Hugging Face")
        
        # Verificar GPU
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🖥️ Usando: {device}")
        
        # Cargar audio
        update_job_status(job_id, 'processing', 20)
        print(f"🎵 Cargando audio: {Path(file_path).name}")
        waveform, sample_rate = load_audio_file(file_path)
        
        # Información del audio
        audio_info = get_audio_info(waveform, sample_rate)
        print_audio_info(audio_info, file_path)
        
        # Preprocesar
        update_job_status(job_id, 'processing', 30)
        waveform, sample_rate = preprocess_audio(waveform, sample_rate)
        
        # Dividir en chunks
        update_job_status(job_id, 'processing', 40)
        chunk_duration = config.get('chunk_duration', 60)
        chunks = split_audio_into_chunks(waveform, sample_rate, chunk_duration, overlap=1)
        print(f"📦 Creados {len(chunks)} chunks")
        
        # Procesamiento paralelo
        update_job_status(job_id, 'processing', 50)
        max_workers = config.get('max_workers', 2)
        chunk_results = run_parallel_diarization(chunks, token_hf, device, max_workers)
        
        # Combinar resultados
        update_job_status(job_id, 'processing', 80)
        speakers = merge_chunk_results(chunk_results)
        
        # Separar speakers
        update_job_status(job_id, 'processing', 90)
        output_dir, nombre_base = separate_speakers_optimized(waveform, sample_rate, speakers, file_path)
        
        # Preparar resultado
        result = {
            'job_id': job_id,
            'filename': Path(file_path).name,
            'audio_info': audio_info,
            'speakers_detected': len(speakers),
            'speakers': list(speakers.keys()),
            'output_files': [],
            'processing_time': time.time() - jobs[job_id]['created_at'].timestamp()
        }
        
        # Listar archivos generados
        for i in range(1, len(speakers) + 1):
            output_file = output_dir / f"{nombre_base}_persona_{i}.wav"
            if output_file.exists():
                result['output_files'].append(str(output_file))
        
        # Completar job
        update_job_status(job_id, 'completed', 100, result=result)
        
    except Exception as e:
        print(f"❌ Error procesando job {job_id}: {e}")
        update_job_status(job_id, 'failed', error=str(e))

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud de la API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'gpu_available': torch.cuda.is_available(),
        'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'dependencies': check_dependencies()
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint para subir archivos de audio"""
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
