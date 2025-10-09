#!/usr/bin/env python3
"""
Script optimizado para separar speakers en archivos de audio usando pyannote.audio
Versión optimizada con procesamiento en chunks paralelos
"""

import os
import sys
import subprocess
from pathlib import Path
import argparse
import time
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

def load_env_token():
    """Carga el token de Hugging Face desde el archivo .env"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('HUGGINGFACE_API_KEY')
        if token:
            print("🔑 Token cargado desde .env")
            return token
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️ Error cargando .env: {e}")
    
    return None

def install_package(package):
    """Instala un paquete usando pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
        return True
    except subprocess.CalledProcessError:
        return False

def check_dependencies():
    """Verifica si las dependencias están instaladas"""
    required_packages = ['torch', 'torchaudio', 'pyannote.audio', 'ffmpeg', 'onnxruntime']
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'ffmpeg':
                # Verificar ffmpeg en el sistema
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            else:
                __import__(package.replace('-', '_'))
        except (ImportError, subprocess.CalledProcessError, FileNotFoundError):
            missing_packages.append(package)
    
    return missing_packages

def get_audio_info(waveform, sample_rate):
    """Obtiene información detallada del audio"""
    duration = waveform.shape[1] / sample_rate
    size_mb = waveform.numel() * waveform.element_size() / (1024 * 1024)
    channels = waveform.shape[0]
    
    return {
        'duration': duration,
        'size_mb': size_mb,
        'channels': channels,
        'sample_rate': sample_rate,
        'samples': waveform.shape[1]
    }

def print_audio_info(info, filename):
    """Imprime información detallada del audio"""
    print(f"\n📊 Información del audio:")
    print(f"   📁 Archivo: {Path(filename).name}")
    print(f"   📏 Tamaño: {info['size_mb']:.1f} MB")
    print(f"   ⏱️ Duración: {info['duration']//60:.0f}:{info['duration']%60:05.1f} minutos")
    print(f"   🎚️ Sample rate: {info['sample_rate']} Hz")
    print(f"   🔊 Canales: {info['channels']} ({'mono' if info['channels'] == 1 else 'estéreo'})")
    print(f"   📈 Muestras: {info['samples']:,}")

def split_audio_into_chunks(waveform, sample_rate, chunk_duration=60, overlap=1):
    """Divide el audio en chunks de duración específica"""
    chunk_samples = int(chunk_duration * sample_rate)
    overlap_samples = int(overlap * sample_rate)
    step_samples = chunk_samples - overlap_samples
    
    chunks = []
    start = 0
    
    while start < waveform.shape[1]:
        end = min(start + chunk_samples, waveform.shape[1])
        chunk = waveform[:, start:end]
        chunks.append({
            'waveform': chunk,
            'start_time': start / sample_rate,
            'end_time': end / sample_rate,
            'chunk_id': len(chunks)
        })
        start += step_samples
    
    return chunks

def preprocess_audio(waveform, sample_rate, target_sample_rate=16000):
    """Preprocesa el audio para optimizar el rendimiento"""
    import torch
    import torchaudio
    
    print("🔧 Preprocesando audio...")
    
    # Resample a 16kHz para mejor rendimiento
    if sample_rate != target_sample_rate:
        print(f"🔄 Resampleando de {sample_rate}Hz a {target_sample_rate}Hz...")
        resampler = torchaudio.transforms.Resample(sample_rate, target_sample_rate)
        waveform = resampler(waveform)
        sample_rate = target_sample_rate
    
    # Convertir a mono si es necesario
    if waveform.shape[0] > 1:
        print("🔄 Convirtiendo a mono...")
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    
    # Normalizar
    print("🎚️ Normalizando...")
    max_val = torch.max(torch.abs(waveform))
    if max_val > 0:
        waveform = waveform / max_val * 0.95
    
    # Aplicar filtro de paso alto para reducir ruido de baja frecuencia
    print("🔊 Aplicando filtro de audio...")
    try:
        highpass = torchaudio.transforms.HighpassBiquad(sample_rate, cutoff_freq=80)
        waveform = highpass(waveform)
    except:
        print("⚠️ No se pudo aplicar filtro de paso alto")
    
    return waveform, sample_rate

def install_missing_dependencies():
    """Instala solo las dependencias que faltan"""
    missing = check_dependencies()
    
    if not missing:
        print("✅ Todas las dependencias están instaladas")
        return True
    
    print(f"📦 Faltan dependencias: {', '.join(missing)}")
    
    # Instalar dependencias faltantes
    for package in missing:
        if package == 'ffmpeg':
            print("❌ ffmpeg no está instalado. Por favor instálalo manualmente:")
            print("   sudo apt update && sudo apt install ffmpeg")
            return False
        else:
            print(f"📦 Instalando {package}...")
            if not install_package(package):
                print(f"❌ Error instalando {package}")
                return False
    
    print("✅ Dependencias instaladas correctamente")
    return True

def force_reinstall_dependencies():
    """Fuerza la reinstalación completa de dependencias (comportamiento original)"""
    print("🔍 Reinstalando todas las dependencias...")
    
    # Desinstalar numpy incompatible y reinstalar versión correcta
    print("📦 Reinstalando numpy...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "numpy", "-y", "-q"], 
                   capture_output=True)
    if not install_package("numpy==2.2.2"):
        print("❌ Error instalando numpy")
        return False
    
    # Instalar pyannote.audio
    print("📦 Instalando pyannote.audio...")
    if not install_package("pyannote.audio"):
        print("❌ Error instalando pyannote.audio")
        return False
    
    print("✅ Dependencias reinstaladas correctamente")
    return True

def convert_video_to_audio(video_path, sample_rate=16000):
    """Convierte un archivo de video a audio usando ffmpeg"""
    import ffmpeg
    import tempfile
    import os
    
    # Crear archivo temporal para el audio
    temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_audio.close()
    
    print(f"🎬 Convirtiendo video a audio: {video_path}")
    
    try:
        # Usar ffmpeg para extraer audio
        (
            ffmpeg
            .input(video_path)
            .output(temp_audio.name, acodec='pcm_s16le', ac=1, ar=sample_rate)
            .overwrite_output()
            .run(quiet=True)
        )
        print(f"✅ Audio extraído: {temp_audio.name}")
        return temp_audio.name
    except ffmpeg.Error as e:
        print(f"❌ Error convirtiendo video: {e}")
        os.unlink(temp_audio.name)
        return None

def load_audio_file(file_path):
    """Carga un archivo de audio o video optimizado"""
    import torchaudio
    
    # Verificar si es un archivo de video
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext in video_extensions:
        # Convertir video a audio con configuración optimizada
        temp_audio = convert_video_to_audio(file_path, sample_rate=16000)
        if temp_audio is None:
            raise ValueError(f"No se pudo convertir el video {file_path}")
        
        print(f"🎵 Cargando audio convertido: {Path(temp_audio).name}")
        waveform, sample_rate = torchaudio.load(temp_audio)
        
        # Limpiar archivo temporal
        import os
        os.unlink(temp_audio)
    else:
        print(f"🎵 Cargando audio: {Path(file_path).name}")
        waveform, sample_rate = torchaudio.load(file_path)
    
    return waveform, sample_rate

def run_diarization_chunk(chunk_data, token_hf, device, chunk_id, total_chunks):
    """Ejecuta la diarización en un chunk específico"""
    from pyannote.audio import Pipeline
    
    chunk = chunk_data['waveform']
    start_time = chunk_data['start_time']
    
    print(f"🎯 Procesando chunk {chunk_id + 1}/{total_chunks} ({start_time:.1f}s - {chunk_data['end_time']:.1f}s)")
    
    # Cargar pipeline (se puede reutilizar)
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.0",  # Modelo disponible
        token=token_hf
    )
    pipeline.to(device)
    
    # Configurar parámetros optimizados
    diarization = pipeline({
        "waveform": chunk,
        "sample_rate": 16000
    }, num_speakers=2)
    
    return {
        'chunk_id': chunk_id,
        'start_time': start_time,
        'end_time': chunk_data['end_time'],
        'diarization': diarization
    }

def run_parallel_diarization(chunks, token_hf, device, max_workers=2):
    """Ejecuta la diarización en paralelo usando threads"""
    print(f"\n🚀 Iniciando procesamiento paralelo con {max_workers} workers...")
    
    results = []
    completed_chunks = 0
    total_chunks = len(chunks)
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Enviar todos los trabajos
        future_to_chunk = {
            executor.submit(run_diarization_chunk, chunk, token_hf, device, i, total_chunks): i 
            for i, chunk in enumerate(chunks)
        }
        
        # Procesar resultados conforme van completándose
        for future in as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            try:
                result = future.result()
                results.append(result)
                completed_chunks += 1
                
                # Calcular progreso
                elapsed_time = time.time() - start_time
                progress = (completed_chunks / total_chunks) * 100
                avg_time_per_chunk = elapsed_time / completed_chunks
                remaining_chunks = total_chunks - completed_chunks
                eta = remaining_chunks * avg_time_per_chunk
                
                print(f"✅ Chunk {completed_chunks}/{total_chunks} completado "
                      f"({progress:.1f}%) - ETA: {eta/60:.1f}min")
                
            except Exception as e:
                print(f"❌ Error en chunk {chunk_idx}: {e}")
    
    # Ordenar resultados por chunk_id
    results.sort(key=lambda x: x['chunk_id'])
    
    total_time = time.time() - start_time
    print(f"\n🎉 Procesamiento paralelo completado en {total_time/60:.1f} minutos")
    
    return results

def merge_chunk_results(chunk_results):
    """Combina los resultados de todos los chunks"""
    print("🔗 Combinando resultados de chunks...")
    
    all_speakers = {}
    chunk_offset = 0
    
    for i, result in enumerate(chunk_results):
        diarization = result['diarization']
        start_time = result['start_time']
        
        # Acceder al atributo correcto
        annotation = diarization.speaker_diarization
        
        # Iterar sobre los segmentos y ajustar timestamps
        for turn, _, label in annotation.itertracks(yield_label=True):
            adjusted_start = turn.start + start_time
            adjusted_end = turn.end + start_time
            
            if label not in all_speakers:
                all_speakers[label] = []
            all_speakers[label].append((adjusted_start, adjusted_end))
    
    print(f"✅ Combinados {len(chunk_results)} chunks, detectados {len(all_speakers)} hablantes")
    return all_speakers

def save_chunk_audio(waveform, sample_rate, chunk_id, output_dir):
    """Guarda un chunk de audio como archivo temporal"""
    import torchaudio
    
    chunk_file = output_dir / f"chunk_{chunk_id:03d}.wav"
    torchaudio.save(str(chunk_file), waveform, sample_rate, 
                   channels_first=True, format="wav")
    return chunk_file

def separate_speakers_optimized(waveform, sample_rate, speakers, archivo, job_id=None):
    """Separa cada speaker en archivos individuales de forma optimizada"""
    import torch
    import torchaudio
    
    print("✂️ Separando speakers...")
    
    # Crear directorio de salida base (ruta absoluta)
    output_base = Path("output").absolute()
    output_base.mkdir(exist_ok=True)
    
    # Si hay job_id, crear carpeta específica para el job
    if job_id:
        output_dir = output_base / job_id
        output_dir.mkdir(exist_ok=True)
    else:
        output_dir = output_base
    
    nombre_base = Path(archivo).stem
    
    for idx, (label, segments) in enumerate(list(speakers.items())[:2]):
        print(f"\n👤 Procesando Persona {idx + 1} ({label})...")
        
        pista = torch.zeros_like(waveform)
        tiempo_total = 0
        
        for start, end in segments:
            s1 = max(0, min(int(start * sample_rate), waveform.shape[1]))
            s2 = max(0, min(int(end * sample_rate), waveform.shape[1]))
            
            if s1 < s2:
                pista[:, s1:s2] = waveform[:, s1:s2]
                tiempo_total += (end - start)
        
        salida = output_dir / f"speaker_{idx}.wav"
        # Guardar con configuración optimizada
        torchaudio.save(str(salida), pista, sample_rate, 
                       channels_first=True, format="wav")
        print(f"✅ Guardado: {salida} ({tiempo_total:.1f}s)")
    
    print("\n🎉 ¡Separación completada!")
    return output_dir, nombre_base

def print_system_info():
    """Imprime información del sistema"""
    print(f"\n💻 Información del sistema:")
    print(f"   🖥️ CPU: {psutil.cpu_count()} cores")
    print(f"   🧠 RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    
    # Verificar GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"   🎮 GPU: {gpu_name} ({gpu_memory:.1f} GB)")
        else:
            print(f"   🎮 GPU: No disponible")
    except:
        print(f"   🎮 GPU: No disponible")

def main():
    parser = argparse.ArgumentParser(description="Separar speakers en archivos de audio (optimizado)")
    parser.add_argument("audio_file", help="Ruta al archivo de audio a procesar")
    parser.add_argument("--token", help="Token de Hugging Face (opcional si está en .env)")
    parser.add_argument("--install-deps", action="store_true", 
                       help="Instalar dependencias faltantes automáticamente")
    parser.add_argument("--force-reinstall", action="store_true",
                       help="Forzar reinstalación completa de dependencias")
    parser.add_argument("--skip-deps", action="store_true",
                       help="Saltarse verificación de dependencias")
    parser.add_argument("--chunk-duration", type=int, default=60,
                       help="Duración de chunks en segundos (default: 60)")
    parser.add_argument("--max-workers", type=int, default=2,
                       help="Número máximo de workers paralelos (default: 2)")
    
    args = parser.parse_args()
    
    # Mostrar información del sistema
    print_system_info()
    
    # Obtener token de Hugging Face
    token_hf = args.token
    if not token_hf:
        token_hf = load_env_token()
        if not token_hf:
            print("❌ Error: No se encontró token de Hugging Face")
            print("💡 Opciones:")
            print("   - Usar --token 'tu_token'")
            print("   - Crear archivo .env con HUGGINGFACE_API_KEY=tu_token")
            return 1
    
    # Verificar que el archivo existe
    if not os.path.exists(args.audio_file):
        print(f"❌ Error: El archivo {args.audio_file} no existe")
        return 1
    
    # Manejar dependencias
    if not args.skip_deps:
        if args.force_reinstall:
            if not force_reinstall_dependencies():
                return 1
        elif args.install_deps:
            if not install_missing_dependencies():
                return 1
        else:
            # Solo verificar sin instalar
            missing = check_dependencies()
            if missing:
                print(f"❌ Faltan dependencias: {', '.join(missing)}")
                print("💡 Usa --install-deps para instalarlas automáticamente")
                print("💡 O --skip-deps para saltarte la verificación")
                return 1
            else:
                print("✅ Todas las dependencias están disponibles")
    
    # Verificar GPU
    import torch
    device = torch.device("cuda")  # Forzar GPU
    print(f"🖥️ Usando: {device}")
    
    # Cargar y analizar audio
    print(f"\n🎵 Cargando audio: {Path(args.audio_file).name}")
    waveform, sample_rate = load_audio_file(args.audio_file)
    
    # Mostrar información detallada del audio
    audio_info = get_audio_info(waveform, sample_rate)
    print_audio_info(audio_info, args.audio_file)
    
    # Preprocesar audio
    waveform, sample_rate = preprocess_audio(waveform, sample_rate)
    
    # Dividir en chunks
    print(f"\n✂️ Dividiendo audio en chunks de {args.chunk_duration} segundos...")
    chunks = split_audio_into_chunks(waveform, sample_rate, args.chunk_duration, overlap=1)
    print(f"📦 Creados {len(chunks)} chunks")
    
    # Ejecutar diarización en paralelo
    chunk_results = run_parallel_diarization(chunks, token_hf, device, args.max_workers)
    
    # Combinar resultados
    speakers = merge_chunk_results(chunk_results)
    
    # Separar speakers
    output_dir, nombre_base = separate_speakers_optimized(waveform, sample_rate, speakers, args.audio_file)
    
    # Mostrar archivos generados
    print(f"\n📁 Archivos generados en: {output_dir}")
    for i in range(1, 3):
        archivo_generado = output_dir / f"{nombre_base}_persona_{i}.wav"
        if archivo_generado.exists():
            print(f"  - {archivo_generado}")
    
    print("\n🎊 ¡Proceso completado exitosamente!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
