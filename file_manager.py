"""
Gestor de Archivos
=================

Maneja la recopilación, movimiento y gestión de fechas de archivos.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import logging
from tqdm import tqdm

class GestorArchivos:
    def __init__(self, origen: Path, destino: Path, temp_dir: Path):
        self.origen = origen
        self.destino = destino
        self.temp_dir = temp_dir
        self.logger = logging.getLogger(__name__)
        
        # Extensiones soportadas
        self.img_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif'}
        self.raw_extensions = {'.dng', '.arw', '.nef', '.cr2', '.cr3', '.orf', '.rw2', '.raf'}
        self.all_extensions = self.img_extensions | self.raw_extensions

    def recopilar_archivos(self) -> List[Path]:
        """Recopila todos los archivos de imagen"""
        self.logger.info("📁 Recopilando archivos...")
        
        archivos = []
        
        # Buscar en origen
        for ext in self.all_extensions:
            archivos.extend(self.origen.rglob(f"*{ext}"))
            archivos.extend(self.origen.rglob(f"*{ext.upper()}"))
        
        # Filtrar solo archivos válidos
        archivos = [f for f in archivos if f.is_file() and f.stat().st_size > 0]
        
        self.logger.info(f"📁 Archivos encontrados: {len(archivos)}")
        return archivos

    def get_creation_time(self, file_path: Path) -> float:
        """Obtiene fecha de creación desde múltiples fuentes"""
        
        # 1. JSON de Google Takeout
        json_paths = [
            file_path.with_suffix(file_path.suffix + '.json'),
            file_path.with_suffix('.json'),
            file_path.parent / (file_path.stem + '.json')
        ]
        
        for json_path in json_paths:
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        
                        # Diferentes formatos de timestamp
                        for key in ['creationTime', 'photoTakenTime']:
                            if key in meta:
                                time_data = meta[key]
                                if isinstance(time_data, dict):
                                    ts = int(time_data.get('timestamp', 0))
                                elif isinstance(time_data, str):
                                    ts = int(time_data)
                                else:
                                    ts = int(time_data) if time_data else 0
                                
                                if ts > 0:
                                    self.logger.debug(f"Fecha desde JSON: {datetime.fromtimestamp(ts)}")
                                    return ts
                                    
                except Exception as e:
                    self.logger.debug(f"Error leyendo JSON {json_path}: {e}")
        
        # 2. EXIF data
        try:
            from PIL import Image, ExifTags
            with Image.open(file_path) as img:
                exif = img.getexif()
                if exif:
                    for tag_name in ["DateTimeOriginal", "DateTime", "DateTimeDigitized"]:
                        for tag, value in exif.items():
                            if ExifTags.TAGS.get(tag, tag) == tag_name and value:
                                try:
                                    dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                    self.logger.debug(f"Fecha desde EXIF ({tag_name}): {dt}")
                                    return dt.timestamp()
                                except ValueError:
                                    continue
        except Exception as e:
            self.logger.debug(f"No se pudo leer EXIF de {file_path}: {e}")
        
        # 3. Fecha del sistema
        return file_path.stat().st_mtime

    def ejecutar_movimientos(self, movimientos: List[Tuple[Path, Path, float]]) -> int:
        """Ejecuta los movimientos planificados"""
        archivos_movidos = 0
        
        for archivo_origen, archivo_destino, timestamp in tqdm(movimientos, desc="Moviendo archivos"):
            try:
                # Crear directorio destino
                archivo_destino.parent.mkdir(parents=True, exist_ok=True)
                
                # Copiar archivo preservando metadatos
                shutil.copy2(archivo_origen, archivo_destino)
                
                # Corregir fecha de creación
                os.utime(archivo_destino, (timestamp, timestamp))
                
                # Eliminar original si está en origen
                if self.origen in archivo_origen.parents:
                    archivo_origen.unlink()
                
                archivos_movidos += 1
                
            except Exception as e:
                self.logger.error(f"Error moviendo {archivo_origen} → {archivo_destino}: {e}")
        
        return archivos_movidos

    def convertir_raw_a_jpg(self, raw_path: Path, jpg_path: Path) -> bool:
        """Convierte archivo RAW a JPG para análisis"""
        try:
            # Verificar dcraw
            subprocess.run(["dcraw", "-v"], capture_output=True, check=True)
            
            # Convertir
            cmd = ["dcraw", "-c", "-w", "-H", "1", "-q", "3", "-T", str(raw_path)]
            result = subprocess.run(cmd, capture_output=True, check=True)
            
            # Procesar con ImageMagick
            convert_cmd = [
                "convert", "-", "-strip", "-resize", "1024x1024>", 
                "-quality", "85", str(jpg_path)
            ]
            subprocess.run(convert_cmd, input=result.stdout, check=True)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error convirtiendo {raw_path}: {e}")
            return False