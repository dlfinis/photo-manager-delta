#!/usr/bin/env python3
"""
Sistema de Consolidación Inteligente de Fotos
============================================

Funcionalidades:
- Detección avanzada de duplicados (exactos, visuales, ráfaga)
- Organización por álbumes existentes
- Procesamiento de Google Takeout
- Gestión de archivos RAW
- Corrección de fechas EXIF

Uso:
    python consolidador_fotos.py --origen ./fotos --destino ./consolidadas

Dependencias:
    sudo apt install dcraw imagemagick exiv2
    pip install pillow imagededup opencv-python scikit-learn tqdm
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from detector_duplicados import DetectorDuplicadosAvanzado
from gestor_archivos import GestorArchivos
from organizador_fotos import OrganizadorFotos
from utils import configurar_logging, validar_dependencias

class ConsolidadorFotos:
    def __init__(self, origen: Path, destino: Path, temp_dir: Path):
        self.origen = origen.resolve()
        self.destino = destino.resolve()
        self.temp_dir = temp_dir.resolve()
        
        # Componentes del sistema
        self.gestor = GestorArchivos(self.origen, self.destino, self.temp_dir)
        self.detector = DetectorDuplicadosAvanzado()
        self.organizador = OrganizadorFotos(self.destino)
        
        # Estadísticas globales
        self.stats = {
            'inicio': datetime.now(),
            'archivos_procesados': 0,
            'duplicados_eliminados': 0,
            'archivos_movidos': 0,
            'errores': 0
        }
        
        self.logger = logging.getLogger(__name__)

    def validar_configuracion(self):
        """Valida la configuración inicial"""
        self.logger.info("🔍 Validando configuración...")
        
        # Validar carpetas
        if not self.origen.exists():
            raise FileNotFoundError(f"Carpeta origen no existe: {self.origen}")
        
        if self.origen == self.destino:
            raise ValueError("Carpeta origen y destino no pueden ser iguales")
        
        # Crear carpetas necesarias
        self.destino.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Validar dependencias
        validar_dependencias()
        
        self.logger.info("✅ Configuración válida")

    def ejecutar_consolidacion(self, dry_run=False, skip_visual=False, 
                             umbral_visual=0.85, umbral_temporal=5):
        """Ejecuta el proceso completo de consolidación"""
        
        try:
            self.logger.info("🚀 Iniciando consolidación de fotos...")
            self.logger.info(f"📂 Origen: {self.origen}")
            self.logger.info(f"📂 Destino: {self.destino}")
            
            # 1. Validar configuración
            self.validar_configuracion()
            
            # 2. Detectar álbumes existentes
            self.logger.info("🖼️ Detectando álbumes existentes...")
            albumes = self.organizador.detectar_albumes_existentes()
            
            # 3. Recopilar archivos
            self.logger.info("📁 Recopilando archivos...")
            archivos = self.gestor.recopilar_archivos()
            self.stats['archivos_procesados'] = len(archivos)
            
            if not archivos:
                self.logger.warning("⚠️ No se encontraron archivos para procesar")
                return
            
            # 4. Configurar detector de duplicados
            self.detector.configurar(
                umbral_visual=umbral_visual,
                umbral_temporal=umbral_temporal
            )
            
            # 5. Eliminar duplicados
            self.logger.info("🔍 Eliminando duplicados...")
            archivos_unicos = self.detector.eliminar_duplicados(
                archivos, 
                self.gestor.get_creation_time,
                skip_visual=skip_visual
            )
            
            duplicados_eliminados = len(archivos) - len(archivos_unicos)
            self.stats['duplicados_eliminados'] = duplicados_eliminados
            self.logger.info(f"✅ Duplicados eliminados: {duplicados_eliminados}")
            
            # 6. Planificar movimientos
            self.logger.info("📋 Planificando movimientos...")
            movimientos = self.organizador.planificar_movimientos(
                archivos_unicos, 
                albumes,
                self.gestor.get_creation_time
            )
            
            # 7. Generar informe
            self.logger.info("📄 Generando informe...")
            self.generar_informe(movimientos)
            
            # 8. Ejecutar movimientos
            if dry_run:
                self.logger.info("📝 Modo simulación - no se moverán archivos")
            else:
                if self.confirmar_ejecucion(len(movimientos)):
                    self.logger.info("📦 Ejecutando movimientos...")
                    archivos_movidos = self.gestor.ejecutar_movimientos(movimientos)
                    self.stats['archivos_movidos'] = archivos_movidos
                    self.logger.info("✅ Consolidación completada exitosamente")
                else:
                    self.logger.info("❌ Consolidación cancelada por el usuario")
            
        except Exception as e:
            self.logger.error(f"❌ Error durante la consolidación: {e}")
            self.stats['errores'] += 1
            raise
        
        finally:
            self.mostrar_resumen_final()

    def confirmar_ejecucion(self, num_movimientos):
        """Solicita confirmación del usuario"""
        print(f"\n📊 Resumen:")
        print(f"   - Archivos a mover: {num_movimientos}")
        print(f"   - Duplicados eliminados: {self.stats['duplicados_eliminados']}")
        
        respuesta = input("\n¿Proceder con la consolidación? (s/N): ").strip().lower()
        return respuesta in ['s', 'si', 'sí', 'y', 'yes']

    def generar_informe(self, movimientos):
        """Genera informe detallado"""
        informe_path = self.destino / "informe_consolidacion.txt"
        
        with open(informe_path, 'w', encoding='utf-8') as f:
            f.write("INFORME DE CONSOLIDACIÓN DE FOTOS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Origen: {self.origen}\n")
            f.write(f"Destino: {self.destino}\n\n")
            
            f.write("ESTADÍSTICAS:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Archivos procesados: {self.stats['archivos_procesados']}\n")
            f.write(f"Duplicados eliminados: {self.stats['duplicados_eliminados']}\n")
            f.write(f"Archivos a mover: {len(movimientos)}\n\n")
            
            # Estadísticas del detector
            stats_detector = self.detector.get_stats()
            f.write("DUPLICADOS POR TIPO:\n")
            f.write("-" * 20 + "\n")
            for tipo, cantidad in stats_detector.items():
                f.write(f"{tipo}: {cantidad}\n")
            f.write("\n")
            
            # Estadísticas del organizador
            stats_organizador = self.organizador.get_stats()
            f.write("ORGANIZACIÓN:\n")
            f.write("-" * 20 + "\n")
            for categoria, cantidad in stats_organizador.items():
                f.write(f"{categoria}: {cantidad}\n")
            f.write("\n")
            
            f.write("MOVIMIENTOS PLANIFICADOS:\n")
            f.write("-" * 30 + "\n")
            for origen, destino, timestamp in movimientos:
                fecha = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{origen} → {destino} [{fecha}]\n")
        
        self.logger.info(f"📄 Informe guardado: {informe_path}")

    def mostrar_resumen_final(self):
        """Muestra resumen final de la ejecución"""
        duracion = datetime.now() - self.stats['inicio']
        
        print(f"\n📊 RESUMEN FINAL")
        print(f"=" * 40)
        print(f"⏱️  Duración: {duracion}")
        print(f"📁 Archivos procesados: {self.stats['archivos_procesados']}")
        print(f"🗑️  Duplicados eliminados: {self.stats['duplicados_eliminados']}")
        print(f"📦 Archivos movidos: {self.stats['archivos_movidos']}")
        print(f"❌ Errores: {self.stats['errores']}")

def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Consolidación Inteligente de Fotos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s --origen ./fotos --destino ./consolidadas
  %(prog)s --origen ./takeout --destino ./consolidadas --dry-run
  %(prog)s --origen ./fotos --destino ./consolidadas --skip-visual --verbose
        """
    )
    
    parser.add_argument("--origen", required=True, type=Path,
                       help="Carpeta origen con fotos a consolidar")
    parser.add_argument("--destino", required=True, type=Path,
                       help="Carpeta destino para fotos consolidadas")
    parser.add_argument("--temp", type=Path, default=Path("/tmp/consolidacion"),
                       help="Carpeta temporal para procesamiento")
    
    parser.add_argument("--dry-run", action="store_true",
                       help="Solo simular, no mover archivos")
    parser.add_argument("--skip-visual", action="store_true",
                       help="Omitir detección visual de duplicados")
    
    parser.add_argument("--umbral-visual", type=float, default=0.85,
                       help="Umbral de similitud visual (0.0-1.0)")
    parser.add_argument("--umbral-temporal", type=int, default=5,
                       help="Segundos máximos para considerar ráfaga")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Modo verbose")
    parser.add_argument("--debug", action="store_true",
                       help="Modo debug")
    
    args = parser.parse_args()
    
    # Configurar logging
    nivel_log = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
    configurar_logging(nivel_log)
    
    try:
        # Crear y ejecutar consolidador
        consolidador = ConsolidadorFotos(args.origen, args.destino, args.temp)
        consolidador.ejecutar_consolidacion(
            dry_run=args.dry_run,
            skip_visual=args.skip_visual,
            umbral_visual=args.umbral_visual,
            umbral_temporal=args.umbral_temporal
        )
        
    except KeyboardInterrupt:
        print("\n❌ Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()