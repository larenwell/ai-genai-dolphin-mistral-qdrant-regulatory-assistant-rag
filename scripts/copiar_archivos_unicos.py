#!/usr/bin/env python3
"""
Script para Copiar Archivos Únicos
==================================

Este script copia los archivos únicos identificados en el análisis de duplicados
a una carpeta `data/unique` para su posterior ingesta.

Autor: AI Assistant
Fecha: 2025-01-06
"""

import pandas as pd
import shutil
import time
from pathlib import Path
from collections import defaultdict

def print_stage_title(title: str, stage_number: int = None):
    """Imprimir un título de etapa con separadores visuales"""
    if stage_number:
        print(f"\n{'='*80}")
        print(f"🚀 ETAPA {stage_number}: {title}")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"🎯 {title}")
        print(f"{'='*80}")

def print_sub_stage(title: str):
    """Imprimir un subtítulo de etapa"""
    print(f"\n📋 {title}")
    print(f"{'-'*60}")

class UniqueFileCopier:
    """Copiador de archivos únicos para preparar ingesta"""
    
    def __init__(self, csv_file_path: str, data_root: str, unique_folder: str):
        self.csv_file_path = Path(csv_file_path)
        self.data_root = Path(data_root)
        self.unique_folder = Path(unique_folder)
        self.unique_folder.mkdir(parents=True, exist_ok=True)
        
        # Cargar datos
        self.df = None
        self.unique_files = []
        self.copied_files = []
        self.failed_files = []
        
    def load_data(self):
        """Cargar datos del archivo CSV"""
        print_sub_stage("CARGANDO DATOS")
        
        try:
            # Intentar leer con diferentes separadores
            for sep in ['\t', ',', ';']:
                try:
                    self.df = pd.read_csv(self.csv_file_path, sep=sep, encoding='utf-8')
                    print(f"   ✅ Archivo leído con separador: '{sep}'")
                    break
                except:
                    continue
            
            if self.df is None:
                raise Exception("No se pudo leer el archivo CSV con ningún separador")
            
            print(f"   📊 Total de registros cargados: {len(self.df)}")
            
            # Crear columna is_duplicate basada en duplicados de hash
            print("   🔍 Detectando duplicados por hash...")
            hash_counts = self.df['file_hash'].value_counts()
            
            # Inicializar todos como únicos
            self.df['is_duplicate'] = False
            
            # Para cada hash que aparece más de una vez, marcar solo la primera ocurrencia como única
            for hash_val, count in hash_counts.items():
                if count > 1:
                    # Encontrar todas las filas con este hash
                    duplicate_mask = self.df['file_hash'] == hash_val
                    duplicate_indices = self.df[duplicate_mask].index.tolist()
                    
                    # Marcar la primera ocurrencia como única (mantener False)
                    # Marcar el resto como duplicados (True)
                    for i, idx in enumerate(duplicate_indices):
                        if i > 0:  # No es la primera ocurrencia
                            self.df.loc[idx, 'is_duplicate'] = True
            
            # Filtrar solo las carpetas principales (excluir ingested y test)
            main_folders = ['NFPA', 'normativa', 'normativa_extra']
            self.df_filtered = self.df[self.df['folder'].isin(main_folders)].copy()
            
            print(f"   📁 Carpetas analizadas: {', '.join(main_folders)}")
            print(f"   📊 Archivos en carpetas principales: {len(self.df_filtered)}")
            
            # Recalcular duplicados solo para las carpetas principales
            hash_counts = self.df_filtered['file_hash'].value_counts()
            self.df_filtered['is_duplicate'] = False
            
            # Para cada hash que aparece más de una vez, marcar solo la primera ocurrencia como única
            for hash_val, count in hash_counts.items():
                if count > 1:
                    # Encontrar todas las filas con este hash
                    duplicate_mask = self.df_filtered['file_hash'] == hash_val
                    duplicate_indices = self.df_filtered[duplicate_mask].index.tolist()
                    
                    # Marcar la primera ocurrencia como única (mantener False)
                    # Marcar el resto como duplicados (True)
                    for i, idx in enumerate(duplicate_indices):
                        if i > 0:  # No es la primera ocurrencia
                            self.df_filtered.loc[idx, 'is_duplicate'] = True
            
            # Filtrar solo archivos únicos
            self.unique_files = self.df_filtered[self.df_filtered['is_duplicate'] == False].copy()
            print(f"   📄 Archivos únicos encontrados: {len(self.unique_files)}")
            print(f"   📄 Archivos duplicados: {len(self.df_filtered[self.df_filtered['is_duplicate']])}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error al cargar datos: {e}")
            return False
    
    def organize_by_folder(self):
        """Organizar archivos únicos por carpeta de origen"""
        print_sub_stage("ORGANIZANDO POR CARPETA")
        
        folder_organization = defaultdict(list)
        
        for _, row in self.unique_files.iterrows():
            folder = row['folder']
            folder_organization[folder].append(row)
        
        print(f"   📁 Carpetas encontradas: {len(folder_organization)}")
        for folder, files in folder_organization.items():
            print(f"      {folder}: {len(files)} archivos únicos")
        
        return folder_organization
    
    def copy_files(self, folder_organization):
        """Copiar archivos únicos a la carpeta de destino"""
        print_sub_stage("COPIANDO ARCHIVOS ÚNICOS")
        
        total_files = sum(len(files) for files in folder_organization.values())
        processed = 0
        
        for folder, files in folder_organization.items():
            print(f"   📁 Procesando carpeta: {folder}")
            
            # Crear subcarpeta en destino
            dest_folder = self.unique_folder / folder
            dest_folder.mkdir(exist_ok=True)
            
            for file_info in files:
                try:
                    source_path = Path(file_info['full_path'])
                    dest_path = dest_folder / file_info['filename']
                    
                    # Verificar que el archivo fuente existe
                    if not source_path.exists():
                        print(f"      ⚠️ Archivo no encontrado: {source_path}")
                        self.failed_files.append({
                            'filename': file_info['filename'],
                            'source_path': str(source_path),
                            'reason': 'Archivo no encontrado'
                        })
                        continue
                    
                    # Copiar archivo
                    shutil.copy2(source_path, dest_path)
                    
                    self.copied_files.append({
                        'filename': file_info['filename'],
                        'source_path': str(source_path),
                        'dest_path': str(dest_path),
                        'folder': folder,
                        'file_size_mb': file_info.get('file_size_mb', 0)
                    })
                    
                    processed += 1
                    if processed % 100 == 0:
                        print(f"      📄 Procesados: {processed}/{total_files}")
                    
                except Exception as e:
                    print(f"      ❌ Error copiando {file_info['filename']}: {e}")
                    self.failed_files.append({
                        'filename': file_info['filename'],
                        'source_path': str(source_path),
                        'reason': str(e)
                    })
        
        print(f"   ✅ Archivos copiados exitosamente: {len(self.copied_files)}")
        print(f"   ❌ Archivos con error: {len(self.failed_files)}")
    
    def generate_summary(self):
        """Generar resumen de la operación"""
        print_sub_stage("GENERANDO RESUMEN")
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Estadísticas por carpeta
        folder_stats = defaultdict(lambda: {'count': 0, 'size_mb': 0})
        
        for file_info in self.copied_files:
            folder = file_info['folder']
            folder_stats[folder]['count'] += 1
            folder_stats[folder]['size_mb'] += file_info['file_size_mb']
        
        # Crear resumen
        summary = {
            'timestamp': timestamp,
            'total_unique_files': len(self.unique_files),
            'successfully_copied': len(self.copied_files),
            'failed_copies': len(self.failed_files),
            'success_rate': (len(self.copied_files) / len(self.unique_files)) * 100 if len(self.unique_files) > 0 else 0,
            'folder_stats': dict(folder_stats),
            'total_size_mb': sum(file_info['file_size_mb'] for file_info in self.copied_files),
            'copied_files': self.copied_files,
            'failed_files': self.failed_files
        }
        
        # Guardar resumen JSON
        summary_path = self.unique_folder / f"copy_summary_{timestamp}.json"
        import json
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"   📄 Resumen guardado: {summary_path}")
        
        # Mostrar estadísticas
        print(f"   📊 Archivos únicos totales: {summary['total_unique_files']}")
        print(f"   ✅ Archivos copiados exitosamente: {summary['successfully_copied']}")
        print(f"   ❌ Archivos con error: {summary['failed_copies']}")
        print(f"   📈 Tasa de éxito: {summary['success_rate']:.1f}%")
        print(f"   💾 Tamaño total copiado: {summary['total_size_mb']:.2f} MB")
        
        print(f"\n   📁 Estadísticas por carpeta:")
        for folder, stats in folder_stats.items():
            print(f"      {folder}: {stats['count']} archivos ({stats['size_mb']:.2f} MB)")
        
        return summary

def main():
    """Función principal"""
    print_stage_title("COPIA DE ARCHIVOS ÚNICOS")
    
    # Configuración
    project_root = Path(__file__).parent.parent
    csv_file = project_root / "src" / "output" / "datasources" / "datasources_files_20251006_131302.csv"
    data_root = project_root / "data"
    unique_folder = project_root / "data" / "unique"
    
    print(f"📁 Archivo CSV: {csv_file}")
    print(f"📁 Directorio de datos: {data_root}")
    print(f"📁 Carpeta de archivos únicos: {unique_folder}")
    
    # Crear copiador
    copier = UniqueFileCopier(csv_file, data_root, unique_folder)
    
    # Ejecutar proceso
    if not copier.load_data():
        print("❌ Error al cargar datos")
        return
    
    folder_organization = copier.organize_by_folder()
    copier.copy_files(folder_organization)
    summary = copier.generate_summary()
    
    print_stage_title("COPIA COMPLETADA")
    print("✅ Proceso de copia de archivos únicos completado")
    print(f"📁 Archivos únicos disponibles en: {unique_folder}")
    
    if summary['failed_copies'] > 0:
        print(f"⚠️ {summary['failed_copies']} archivos no pudieron ser copiados")
        print("   Revisa el resumen para más detalles")

if __name__ == "__main__":
    main()
