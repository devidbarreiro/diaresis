#!/usr/bin/env python3
"""
Script para concatenar múltiples archivos de audio en uno solo
Soporta diferentes formatos y maneja automáticamente la normalización
"""

import os
import sys
import argparse
from pathlib import Path
import tempfile

def check_dependencies():
    """Verifica si las dependencias están instaladas"""
    required_packages = ['torchaudio', 'ffmpeg']
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'ffmpeg':
                # Verificar ffmpeg en el sistema
                import subprocess
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            else:
                __import__(package)
        except (ImportError, subprocess.CalledProcessError, FileNotFoundError):
            missing_packages.append(package)
    
    return missing_packages

def convert_to_wav(input_file, output_file=None, sample_rate=22050):
    """Convierte cualquier archivo de audio a WAV usando ffmpeg"""
    import ffmpeg
    import tempfile
    
    if output_file is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        output_file = temp_file.name
        temp_file.close()
    
    try:
        # Usar ffmpeg para convertir a WAV
        (
            ffmpeg
            .input(input_file)
            .output(output_file, acodec='pcm_s16le', ac=1, ar=sample_rate)
            .overwrite_output()
            .run(quiet=True)
        )
        return output_file
    except Exception as e:
        print(f"❌ Error convirtiendo {input_file}: {e}")
        return None

def load_audio_file(file_path, target_sample_rate=22050):
    """Carga un archivo de audio y lo normaliza"""
    import torchaudio
    
    print(f"🎵 Cargando: {Path(file_path).name}")
    
    try:
        # Intentar cargar directamente
        waveform, sample_rate = torchaudio.load(file_path)
    except Exception:
        # Si falla, convertir con ffmpeg primero
        print(f"🔄 Convirtiendo {Path(file_path).name}...")
        temp_wav = convert_to_wav(file_path, sample_rate=target_sample_rate)
        if temp_wav is None:
            raise ValueError(f"No se pudo cargar {file_path}")
        
        waveform, sample_rate = torchaudio.load(temp_wav)
        os.unlink(temp_wav)  # Limpiar archivo temporal
    
    # Resample si es necesario
    if sample_rate != target_sample_rate:
        print(f"🔄 Resampleando de {sample_rate}Hz a {target_sample_rate}Hz...")
        resampler = torchaudio.transforms.Resample(sample_rate, target_sample_rate)
        waveform = resampler(waveform)
        sample_rate = target_sample_rate
    
    # Convertir a mono si es estéreo
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    
    return waveform, sample_rate

def concatenate_audio_files(file_paths, output_path, normalize=True, add_silence=0.0):
    """Concatena múltiples archivos de audio"""
    import torch
    import torchaudio
    
    if not file_paths:
        print("❌ No hay archivos para concatenar")
        return False
    
    print(f"🎼 Concatenando {len(file_paths)} archivos...")
    
    # Cargar todos los archivos
    waveforms = []
    sample_rate = None
    
    for file_path in file_paths:
        try:
            waveform, sr = load_audio_file(file_path)
            waveforms.append(waveform)
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                print(f"⚠️ Sample rate diferente detectado: {sr}Hz vs {sample_rate}Hz")
        except Exception as e:
            print(f"❌ Error cargando {file_path}: {e}")
            continue
    
    if not waveforms:
        print("❌ No se pudieron cargar archivos válidos")
        return False
    
    # Concatenar waveforms
    print("🔗 Concatenando audio...")
    concatenated = torch.cat(waveforms, dim=1)
    
    # Agregar silencio entre archivos si se especifica
    if add_silence > 0:
        silence_samples = int(add_silence * sample_rate)
        silence = torch.zeros(1, silence_samples)
        
        # Intercalar silencio entre cada archivo
        new_waveforms = []
        for i, waveform in enumerate(waveforms):
            new_waveforms.append(waveform)
            if i < len(waveforms) - 1:  # No agregar silencio después del último
                new_waveforms.append(silence)
        
        concatenated = torch.cat(new_waveforms, dim=1)
    
    # Normalizar si se solicita
    if normalize:
        print("🎚️ Normalizando audio...")
        max_val = torch.max(torch.abs(concatenated))
        if max_val > 0:
            concatenated = concatenated / max_val * 0.95  # Dejar un poco de margen
    
    # Guardar archivo final
    print(f"💾 Guardando: {output_path}")
    torchaudio.save(output_path, concatenated, sample_rate)
    
    duration = concatenated.shape[1] / sample_rate
    print(f"✅ Concatenación completada: {duration:.2f} segundos")
    
    return True

def find_audio_files(directory, extensions=None):
    """Encuentra archivos de audio en un directorio"""
    if extensions is None:
        extensions = ['.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg', '.mp4', '.avi', '.mov']
    
    audio_files = []
    directory = Path(directory)
    
    if directory.is_file():
        # Si es un archivo individual
        if directory.suffix.lower() in extensions:
            return [str(directory)]
        else:
            print(f"⚠️ {directory} no es un archivo de audio reconocido")
            return []
    
    # Buscar en directorio
    for ext in extensions:
        audio_files.extend(directory.glob(f'*{ext}'))
        audio_files.extend(directory.glob(f'*{ext.upper()}'))
    
    # Ordenar por nombre
    audio_files.sort()
    return [str(f) for f in audio_files]

def main():
    parser = argparse.ArgumentParser(description="Concatenar múltiples archivos de audio")
    parser.add_argument("input", nargs='+', help="Archivos o directorios de entrada")
    parser.add_argument("-o", "--output", default="concatenated_audio.wav", 
                       help="Archivo de salida (default: concatenated_audio.wav)")
    parser.add_argument("--sample-rate", type=int, default=22050,
                       help="Sample rate de salida (default: 22050)")
    parser.add_argument("--no-normalize", action="store_true",
                       help="No normalizar el audio")
    parser.add_argument("--add-silence", type=float, default=0.0,
                       help="Segundos de silencio entre archivos (default: 0.0)")
    parser.add_argument("--check-deps", action="store_true",
                       help="Verificar dependencias y salir")
    
    args = parser.parse_args()
    
    # Verificar dependencias
    missing = check_dependencies()
    if missing:
        print(f"❌ Faltan dependencias: {', '.join(missing)}")
        print("💡 Instala con: pip install torchaudio ffmpeg-python")
        return 1
    
    if args.check_deps:
        print("✅ Todas las dependencias están disponibles")
        return 0
    
    # Recopilar archivos de audio
    audio_files = []
    for input_path in args.input:
        found_files = find_audio_files(input_path)
        audio_files.extend(found_files)
    
    if not audio_files:
        print("❌ No se encontraron archivos de audio")
        return 1
    
    print(f"📁 Encontrados {len(audio_files)} archivos de audio:")
    for i, file_path in enumerate(audio_files, 1):
        print(f"  {i:2d}. {Path(file_path).name}")
    
    # Concatenar archivos
    success = concatenate_audio_files(
        audio_files,
        args.output,
        normalize=not args.no_normalize,
        add_silence=args.add_silence
    )
    
    if success:
        print(f"\n🎉 ¡Audio concatenado guardado en: {args.output}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
