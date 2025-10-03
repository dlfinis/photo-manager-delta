"""
Detector Avanzado de Duplicados
==============================

Detecta múltiples tipos de duplicados:
- Exactos (hash binario)
- Contenido (misma imagen, diferente compresión)
- Visuales (similitud perceptual)
- Ráfaga (secuencia temporal)
"""

import hashlib
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple

import cv2
import numpy as np
from PIL import Image, ImageStat
import imagehash
from imagededup.methods import PHash, DHash, AHash
from tqdm import tqdm

class DetectorDuplicadosAvanzado:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Algoritmos de hash perceptual
        self.phasher = PHash()
        self.dhasher = DHash()
        self.ahasher = AHash()
        
        # Configuración
        self.umbral_visual = 0.85
        self.umbral_temporal = 5
        
        # Estadísticas
        self.stats = {
            'duplicados_exactos': 0,
            'duplicados_contenido': 0,
            'duplicados_visuales': 0,
            'duplicados_rafaga': 0,
            'duplicados_opencv': 0
        }

    def configurar(self, umbral_visual=0.85, umbral_temporal=5):
        """Configura umbrales de detección"""
        self.umbral_visual = umbral_visual
        self.umbral_temporal = umbral_temporal
        self.logger.info(f"🎯 Umbrales: visual={umbral_visual}, temporal={umbral_temporal}s")

    def calcular_hash_archivo(self, archivo: Path) -> str:
        """Calcula hash SHA256 del archivo completo"""
        h = hashlib.sha256()
        try:
            with open(archivo, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            self.logger.debug(f"Error calculando hash de {archivo}: {e}")
            return ""

    def calcular_hash_contenido(self, archivo: Path) -> str:
        """Hash del contenido visual, ignorando metadatos"""
        try:
            with Image.open(archivo) as img:
                # Normalizar imagen
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img = img.resize((256, 256), Image.Resampling.LANCZOS)
                
                # Hash de píxeles
                return hashlib.md5(img.tobytes()).hexdigest()
        except Exception as e:
            self.logger.debug(f"Error calculando hash contenido de {archivo}: {e}")
            return ""

    def calcular_hashes_perceptuales(self, archivo: Path) -> Dict[str, str]:
        """Calcula múltiples hashes perceptuales"""
        hashes = {}
        try:
            # Hashes de imagededup
            hashes['phash'] = self.phasher.encode_image(image_file=str(archivo))
            hashes['dhash'] = self.dhasher.encode_image(image_file=str(archivo))
            hashes['ahash'] = self.ahasher.encode_image(image_file=str(archivo))
            
            # Hashes adicionales con imagehash
            with Image.open(archivo) as img:
                hashes['whash'] = str(imagehash.whash(img))
                hashes['colorhash'] = str(imagehash.colorhash(img))
                
        except Exception as e:
            self.logger.debug(f"Error calculando hashes perceptuales de {archivo}: {e}")
            
        return hashes

    def calcular_caracteristicas(self, archivo: Path) -> Dict:
        """Extrae características de la imagen"""
        caracteristicas = {}
        try:
            with Image.open(archivo) as img:
                caracteristicas['ancho'] = img.width
                caracteristicas['alto'] = img.height
                caracteristicas['aspecto'] = img.width / img.height
                caracteristicas['pixeles'] = img.width * img.height
                
                # Estadísticas de color
                if img.mode == 'RGB':
                    stat = ImageStat.Stat(img)
                    caracteristicas['brillo'] = sum(stat.mean) / 3
                    caracteristicas['contraste'] = sum(stat.stddev) / 3
                    
        except Exception as e:
            self.logger.debug(f"Error calculando características de {archivo}: {e}")
            
        return caracteristicas

    def detectar_duplicados_exactos(self, archivos_List[Dict]) -> Dict:
        """Detecta duplicados exactos por hash binario"""
        self.logger.info("📋 Detectando duplicados exactos...")
        
        hash_groups = defaultdict(list)
        for data in archivos_
            h = data['hash_binario']
            if h:
                hash_groups[h].append(data)
        
        duplicados = {}
        for h, group in hash_groups.items():
            if len(group) > 1:
                mejor = self.elegir_mejor_archivo(group)
                for data in group:
                    if data != mejor:
                        archivo_str = str(data['path'])
                        duplicados[archivo_str] = [(str(mejor['path']), 1.0, 'exacto')]
                        self.stats['duplicados_exactos'] += 1
        
        return duplicados

    def detectar_duplicados_contenido(self, archivos_ List[Dict]) -> Dict:
        """Detecta duplicados por contenido visual"""
        self.logger.info("🎨 Detectando duplicados de contenido...")
        
        contenido_groups = defaultdict(list)
        for data in archivos_
            h = data['hash_contenido']
            if h:
                contenido_groups[h].append(data)
        
        duplicados = {}
        for h, group in contenido_groups.items():
            if len(group) > 1:
                mejor = self.elegir_mejor_archivo(group)
                for data in group:
                    if data != mejor:
                        archivo_str = str(data['path'])
                        duplicados[archivo_str] = [(str(mejor['path']), 1.0, 'contenido')]
                        self.stats['duplicados_contenido'] += 1
        
        return duplicados

    def detectar_duplicados_visuales(self, archivos_List[Dict]) -> Dict:
        """Detecta duplicados visuales usando hashes perceptuales"""
        self.logger.info("👁️ Detectando duplicados visuales...")
        
        duplicados = {}
        
        for i, data1 in enumerate(tqdm(archivos_data, desc="Comparando")):
            matches = []
            
            for j, data2 in enumerate(archivos_data[i+1:], i+1):
                similitud = self.calcular_similitud_perceptual(
                    data1['hashes_perceptuales'],
                    data2['hashes_perceptuales']
                )
                
                if similitud > self.umbral_visual:
                    matches.append((str(data2['path']), similitud, 'visual'))
            
            if matches:
                duplicados[str(data1['path'])] = matches
                self.stats['duplicados_visuales'] += len(matches)
        
        return duplicados

    def calcular_similitud_perceptual(self, hashes1: Dict, hashes2: Dict) -> float:
        """Calcula similitud promedio entre hashes perceptuales"""
        similitudes = []
        
        # PHash (más importante)
        if 'phash' in hashes1 and 'phash' in hashes2:
            try:
                dist = bin(int(hashes1['phash'], 16) ^ int(hashes2['phash'], 16)).count('1')
                sim = 1.0 - (dist / 64.0)
                similitudes.append(sim * 2)  # Peso doble para PHash
            except:
                pass
        
        # Otros hashes
        for tipo in ['dhash', 'ahash', 'whash', 'colorhash']:
            if tipo in hashes1 and tipo in hashes2:
                try:
                    if tipo in ['whash', 'colorhash']:
                        hash1 = imagehash.hex_to_hash(hashes1[tipo])
                        hash2 = imagehash.hex_to_hash(hashes2[tipo])
                        dist = hash1 - hash2
                        sim = 1.0 - (dist / 64.0)
                    else:
                        sim = 1.0 if hashes1[tipo] == hashes2[tipo] else 0.0
                    
                    similitudes.append(sim)
                except:
                    continue
        
        return sum(similitudes) / len(similitudes) if similitudes else 0.0

    def detectar_duplicados_rafaga(self, archivos_List[Dict]) -> Dict:
        """Detecta duplicados en ráfagas fotográficas"""
        self.logger.info("📸 Detectando duplicados de ráfaga...")
        
        # Agrupar por tiempo
        grupos_temporales = self.agrupar_por_tiempo(archivos_data)
        duplicados = {}
        
        for grupo in grupos_temporales:
            if len(grupo) <= 1:
                continue
            
            # Analizar similitudes dentro del grupo
            for i, data1 in enumerate(grupo):
                matches = []
                
                for j, data2 in enumerate(grupo[i+1:], i+1):
                    sim_visual = self.calcular_similitud_perceptual(
                        data1['hashes_perceptuales'],
                        data2['hashes_perceptuales']
                    )
                    
                    sim_caracteristicas = self.calcular_similitud_caracteristicas(
                        data1['caracteristicas'],
                        data2['caracteristicas']
                    )
                    
                    similitud_total = (sim_visual * 0.7) + (sim_caracteristicas * 0.3)
                    
                    if similitud_total > 0.8:
                        matches.append((str(data2['path']), similitud_total, 'rafaga'))
                
                if matches:
                    duplicados[str(data1['path'])] = matches
                    self.stats['duplicados_rafaga'] += len(matches)
        
        return duplicados

    def agrupar_por_tiempo(self, archivos_data: List[Dict]) -> List[List[Dict]]:
        """Agrupa archivos por proximidad temporal"""
        archivos_ordenados = sorted(archivos_data, key=lambda x: x['timestamp'])
        
        grupos = []
        grupo_actual = [archivos_ordenados[0]]
        
        for i in range(1, len(archivos_ordenados)):
            archivo_actual = archivos_ordenados[i]
            archivo_anterior = archivos_ordenados[i-1]
            
            diferencia = abs(archivo_actual['timestamp'] - archivo_anterior['timestamp'])
            
            if diferencia <= self.umbral_temporal:
                grupo_actual.append(archivo_actual)
            else:
                if len(grupo_actual) > 1:
                    grupos.append(grupo_actual)
                grupo_actual = [archivo_actual]
        
        if len(grupo_actual) > 1:
            grupos.append(grupo_actual)
        
        return grupos

    def calcular_similitud_caracteristicas(self, carac1: Dict, carac2: Dict) -> float:
        """Calcula similitud basada en características"""
        if not carac1 or not carac2:
            return 0.0
        
        similitudes = []
        
        # Aspecto
        if 'aspecto' in carac1 and 'aspecto' in carac2:
            diff = abs(carac1['aspecto'] - carac2['aspecto'])
            sim = max(0, 1.0 - diff)
            similitudes.append(sim)
        
        # Brillo
        if 'brillo' in carac1 and 'brillo' in carac2:
            diff = abs(carac1['brillo'] - carac2['brillo']) / 255.0
            sim = max(0, 1.0 - diff)
            similitudes.append(sim)
        
        return sum(similitudes) / len(similitudes) if similitudes else 0.0

    def elegir_mejor_archivo(self, candidatos: List[Dict]) -> Dict:
        """Elige el mejor archivo de un grupo"""
        def score_archivo(data):
            score = 0
            
            # Tamaño del archivo
            score += data['size']
            
            # Resolución
            if 'caracteristicas' in data and 'pixeles' in data['caracteristicas']:
                score += data['caracteristicas']['pixeles'] * 0.001
            
            # Extensión
            ext = data['path'].suffix.lower()
            if ext in ['.dng', '.arw', '.nef', '.cr2']:
                score += 10000  # RAW prioridad máxima
            elif ext in ['.jpg', '.jpeg']:
                score += 1000
            elif ext == '.png':
                score += 500
            
            return score
        
        return max(candidatos, key=score_archivo)

    def eliminar_duplicados(self, archivos: List[Path], get_timestamp_func, skip_visual=False) -> List[Path]:
        """Proceso completo de eliminación de duplicados"""
        
        # Preparar datos
        self.logger.info("📋 Preparando datos para análisis...")
        archivos_data = []
        
        for archivo in tqdm(archivos, desc="Analizando archivos"):
            try:
                data = {
                    'path': archivo,
                    'timestamp': get_timestamp_func(archivo),
                    'size': archivo.stat().st_size,
                    'hash_binario': self.calcular_hash_archivo(archivo),
                    'hash_contenido': self.calcular_hash_contenido(archivo),
                    'hashes_perceptuales': self.calcular_hashes_perceptuales(archivo),
                    'caracteristicas': self.calcular_caracteristicas(archivo)
                }
                archivos_data.append(data)
            except Exception as e:
                self.logger.error(f"Error procesando {archivo}: {e}")
        
        # Detectar duplicados
        todos_duplicados = {}
        
        # 1. Duplicados exactos
        duplicados_exactos = self.detectar_duplicados_exactos(archivos_data)
        todos_duplicados.update(duplicados_exactos)
        
        # 2. Duplicados de contenido
        duplicados_contenido = self.detectar_duplicados_contenido(archivos_data)
        todos_duplicados.update(duplicados_contenido)
        
        # 3. Duplicados visuales (opcional)
        if not skip_visual:
            duplicados_visuales = self.detectar_duplicados_visuales(archivos_data)
            todos_duplicados.update(duplicados_visuales)
            
            # 4. Duplicados de ráfaga
            duplicados_rafaga = self.detectar_duplicados_rafaga(archivos_data)
            todos_duplicados.update(duplicados_rafaga)
        
        # Procesar duplicados
        archivos_a_eliminar = set()
        for archivo_original, matches in todos_duplicados.items():
            for match_path, similitud, tipo in matches:
                archivos_a_eliminar.add(Path(match_path))
        
        # Retornar archivos únicos
        archivos_unicos = [archivo for archivo in archivos if archivo not in archivos_a_eliminar]
        
        self.logger.info(f"✅ Archivos únicos: {len(archivos_unicos)} de {len(archivos)}")
        return archivos_unicos

    def get_stats(self) -> Dict[str, int]:
        """Retorna estadísticas de duplicados"""
        return self.stats.copy()