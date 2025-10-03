"""
Organizador de Fotos
===================

Maneja la organización por álbumes y fechas.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Callable

class OrganizadorFotos:
    def __init__(self, destino: Path):
        self.destino = destino
        self.logger = logging.getLogger(__name__)
        
        # Extensiones RAW
        self.raw_extensions = {'.dng', '.arw', '.nef', '.cr2', '.cr3', '.orf', '.rw2', '.raf'}
        
        # Estadísticas
        self.stats = {
            'asignados_a_album': 0,
            'organizados_por_fecha': 0,
            'raw_procesados': 0
        }

    def detectar_albumes_existentes(self) -> Dict[str, Path]:
        """Detecta álbumes existentes en la carpeta destino"""
        albumes = {}
        
        if not self.destino.exists():
            return albumes
        
        for item in self.destino.iterdir():
            if item.is_dir() and item.name not in ['raw', 'temp', 'duplicados', '.git']:
                # Crear variantes del nombre para matching
                nombre_original = item.name
                nombre_lower = nombre_original.lower()
                nombre_normalizado = nombre_lower.replace('_', ' ').replace('-', ' ')
                
                # Agregar variantes
                albumes[nombre_lower] = item
                albumes[nombre_normalizado] = item
                
                # Agregar palabras clave
                palabras = nombre_normalizado.split()
                for palabra in palabras:
                    if len(palabra) > 3:  # Solo palabras significativas
                        albumes[palabra] = item
        
        album_names = set(item.name for item in albumes.values())
        self.logger.info(f"🖼️ Álbumes detectados: {album_names}")
        
        return albumes

    def encontrar_album_coincidente(self, file_path: Path, albumes: Dict[str, Path]) -> Path:
        """Encuentra álbum coincidente basado en el path"""
        path_str = str(file_path).lower()
        path_parts = [part.lower() for part in file_path.parts]
        
        # Buscar coincidencias exactas
        for album_key, album_path in albumes.items():
            if album_key in path_str:
                self.logger.debug(f"Coincidencia: {file_path} → {album_path.name}")
                return album_path
        
        # Buscar en partes del path
        for album_key, album_path in albumes.items():
            for part in path_parts:
                if album_key in part or part in album_key:
                    self.logger.debug(f"Coincidencia parcial: {file_path} → {album_path.name}")
                    return album_path
        
        return None

    def planificar_movimientos(self, archivos: List[Path], albumes: Dict[str, Path], 
                             get_timestamp_func: Callable) -> List[Tuple[Path, Path, float]]:
        """Planifica dónde mover cada archivo"""
        movimientos = []
        raw_dir = self.destino / "raw"
        
        for archivo in archivos:
            # Obtener timestamp
            timestamp = get_timestamp_func(archivo)
            fecha = datetime.fromtimestamp(timestamp)
            
            # Determinar si es RAW
            es_raw = archivo.suffix.lower() in self.raw_extensions
            
            # Buscar álbum coincidente
            album_destino = self.encontrar_album_coincidente(archivo, albumes)
            
            if album_destino and not es_raw:
                # Asignar a álbum
                destino_final = album_destino / archivo.name
                self.stats['asignados_a_album'] += 1
                
            elif es_raw:
                # Mover a carpeta RAW
                year = str(fecha.year)
                destino_final = raw_dir / year / archivo.name
                self.stats['raw_procesados'] += 1
                
            else:
                # Organizar por fecha
                year = str(fecha.year)
                month = f"{fecha.month:02d}"
                destino_final = self.destino / year / month / archivo.name
                self.stats['organizados_por_fecha'] += 1
            
            # Resolver colisiones de nombres
            destino_final = self.resolver_colision_nombre(destino_final)
            
            movimientos.append((archivo, destino_final, timestamp))
        
        return movimientos

    def resolver_colision_nombre(self, destino: Path) -> Path:
        """Resuelve colisiones de nombres"""
        if not destino.exists():
            return destino
        
        contador = 1
        base = destino
        
        while destino.exists():
            stem = base.stem
            suffix = base.suffix
            destino = base.parent / f"{stem}_{contador}{suffix}"
            contador += 1
        
        return destino

    def get_stats(self) -> Dict[str, int]:
        """Retorna estadísticas"""
        return self.stats.copy()