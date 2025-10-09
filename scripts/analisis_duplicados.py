#!/usr/bin/env python3
"""
Script de Análisis de Duplicados
================================

Este script analiza los duplicados encontrados en el archivo CSV de análisis de fuentes de datos.
Proporciona estadísticas detalladas sobre duplicados y genera reportes específicos.

Autor: AI Assistant
Fecha: 2025-01-06
"""

import pandas as pd
import json
import time
from pathlib import Path
from collections import defaultdict
import shutil

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

class DuplicateAnalyzer:
    """Analizador de duplicados para archivos de fuentes de datos"""
    
    def __init__(self, csv_file_path: str, output_dir: str):
        self.csv_file_path = Path(csv_file_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar datos
        self.df = None
        self.duplicate_groups = {}
        self.unique_files = []
        self.duplicate_files = []
        
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
            print(f"   📋 Columnas disponibles: {list(self.df.columns)}")
            
            # Verificar columnas necesarias (adaptado al CSV modificado)
            required_columns = ['filename', 'file_hash', 'full_path']
            missing_columns = [col for col in required_columns if col not in self.df.columns]
            
            if missing_columns:
                print(f"   ⚠️ Columnas faltantes: {missing_columns}")
                return False
            
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
            
            print(f"   📊 Archivos únicos: {len(self.df[~self.df['is_duplicate']])}")
            print(f"   📊 Archivos duplicados: {len(self.df[self.df['is_duplicate']])}")
                
            return True
            
        except Exception as e:
            print(f"   ❌ Error al cargar datos: {e}")
            return False
    
    def analyze_duplicates(self):
        """Analizar duplicados y generar estadísticas"""
        print_sub_stage("ANALIZANDO DUPLICADOS")
        
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
        
        # Separar archivos únicos y duplicados
        self.unique_files = self.df_filtered[self.df_filtered['is_duplicate'] == False].copy()
        self.duplicate_files = self.df_filtered[self.df_filtered['is_duplicate'] == True].copy()
        
        print(f"   📄 Archivos únicos: {len(self.unique_files)}")
        print(f"   📄 Archivos duplicados: {len(self.duplicate_files)}")
        
        # Agrupar duplicados por hash
        duplicate_groups = defaultdict(list)
        for _, row in self.duplicate_files.iterrows():
            duplicate_groups[row['file_hash']].append(row.to_dict())
        
        self.duplicate_groups = dict(duplicate_groups)
        
        print(f"   🔍 Grupos de duplicados: {len(self.duplicate_groups)}")
        
        # Análisis por carpeta
        self.analyze_by_folder()
        
        # Análisis por tipo de archivo
        self.analyze_by_file_type()
        
        # Análisis por idioma
        self.analyze_by_language()
        
        return True
    
    def analyze_by_folder(self):
        """Analizar duplicados por carpeta"""
        print_sub_stage("ANÁLISIS POR CARPETA")
        
        folder_stats = {}
        
        for folder in self.df_filtered['folder'].unique():
            folder_data = self.df_filtered[self.df_filtered['folder'] == folder]
            unique_in_folder = folder_data[folder_data['is_duplicate'] == False]
            duplicate_in_folder = folder_data[folder_data['is_duplicate'] == True]
            
            folder_stats[folder] = {
                'total_files': len(folder_data),
                'unique_files': len(unique_in_folder),
                'duplicate_files': len(duplicate_in_folder),
                'duplicate_percentage': (len(duplicate_in_folder) / len(folder_data)) * 100 if len(folder_data) > 0 else 0,
                'total_size_mb': folder_data['file_size_mb'].sum() if 'file_size_mb' in folder_data.columns else 0,
                'wasted_space_mb': duplicate_in_folder['file_size_mb'].sum() if 'file_size_mb' in duplicate_in_folder.columns else 0
            }
            
            print(f"   📁 {folder}:")
            print(f"      Total: {folder_stats[folder]['total_files']} archivos")
            print(f"      Únicos: {folder_stats[folder]['unique_files']} archivos")
            print(f"      Duplicados: {folder_stats[folder]['duplicate_files']} archivos")
            print(f"      % Duplicados: {folder_stats[folder]['duplicate_percentage']:.1f}%")
            print(f"      Espacio desperdiciado: {folder_stats[folder]['wasted_space_mb']:.2f} MB")
        
        self.folder_stats = folder_stats
    
    def analyze_by_file_type(self):
        """Analizar duplicados por tipo de archivo"""
        print_sub_stage("ANÁLISIS POR TIPO DE ARCHIVO")
        
        if 'file_type' not in self.df.columns:
            print("   ⚠️ Columna 'file_type' no encontrada")
            return
        
        file_type_stats = {}
        
        for file_type in self.df_filtered['file_type'].unique():
            type_data = self.df_filtered[self.df_filtered['file_type'] == file_type]
            unique_of_type = type_data[type_data['is_duplicate'] == False]
            duplicate_of_type = type_data[type_data['is_duplicate'] == True]
            
            file_type_stats[file_type] = {
                'total_files': len(type_data),
                'unique_files': len(unique_of_type),
                'duplicate_files': len(duplicate_of_type),
                'duplicate_percentage': (len(duplicate_of_type) / len(type_data)) * 100 if len(type_data) > 0 else 0
            }
            
            print(f"   📄 {file_type.upper()}:")
            print(f"      Total: {file_type_stats[file_type]['total_files']} archivos")
            print(f"      Únicos: {file_type_stats[file_type]['unique_files']} archivos")
            print(f"      Duplicados: {file_type_stats[file_type]['duplicate_files']} archivos")
            print(f"      % Duplicados: {file_type_stats[file_type]['duplicate_percentage']:.1f}%")
        
        self.file_type_stats = file_type_stats
    
    def analyze_by_language(self):
        """Analizar duplicados por idioma"""
        print_sub_stage("ANÁLISIS POR IDIOMA")
        
        if 'final_language' not in self.df.columns:
            print("   ⚠️ Columna 'final_language' no encontrada")
            return
        
        language_stats = {}
        
        for language in self.df_filtered['final_language'].unique():
            lang_data = self.df_filtered[self.df_filtered['final_language'] == language]
            unique_of_lang = lang_data[lang_data['is_duplicate'] == False]
            duplicate_of_lang = lang_data[lang_data['is_duplicate'] == True]
            
            language_stats[language] = {
                'total_files': len(lang_data),
                'unique_files': len(unique_of_lang),
                'duplicate_files': len(duplicate_of_lang),
                'duplicate_percentage': (len(duplicate_of_lang) / len(lang_data)) * 100 if len(lang_data) > 0 else 0
            }
            
            print(f"   🌐 {language.upper()}:")
            print(f"      Total: {language_stats[language]['total_files']} archivos")
            print(f"      Únicos: {language_stats[language]['unique_files']} archivos")
            print(f"      Duplicados: {language_stats[language]['duplicate_files']} archivos")
            print(f"      % Duplicados: {language_stats[language]['duplicate_percentage']:.1f}%")
        
        self.language_stats = language_stats
    
    def generate_reports(self):
        """Generar reportes detallados"""
        print_sub_stage("GENERANDO REPORTES")
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Reporte de duplicados detallado
        duplicate_report = {
            'summary': {
                'total_files': len(self.df),
                'unique_files': len(self.unique_files),
                'duplicate_files': len(self.duplicate_files),
                'duplicate_groups': len(self.duplicate_groups),
                'duplicate_percentage': (len(self.duplicate_files) / len(self.df)) * 100
            },
            'folder_analysis': self.folder_stats,
            'file_type_analysis': self.file_type_stats,
            'language_analysis': self.language_stats,
            'duplicate_groups': self.duplicate_groups
        }
        
        # Guardar reporte JSON
        json_path = self.output_dir / f"duplicate_analysis_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(duplicate_report, f, indent=2, ensure_ascii=False)
        print(f"   📄 Reporte JSON: {json_path}")
        
        # Guardar reporte de archivos únicos
        unique_csv_path = self.output_dir / f"unique_files_{timestamp}.csv"
        self.unique_files.to_csv(unique_csv_path, index=False, encoding='utf-8')
        print(f"   📄 Archivos únicos CSV: {unique_csv_path}")
        
        # Guardar reporte de duplicados
        duplicate_csv_path = self.output_dir / f"duplicate_files_{timestamp}.csv"
        self.duplicate_files.to_csv(duplicate_csv_path, index=False, encoding='utf-8')
        print(f"   📄 Archivos duplicados CSV: {duplicate_csv_path}")
        
        # Generar reporte de texto
        self.generate_text_report(duplicate_report, timestamp)
        
        return {
            'json_path': json_path,
            'unique_csv_path': unique_csv_path,
            'duplicate_csv_path': duplicate_csv_path
        }
    
    def generate_text_report(self, report_data, timestamp):
        """Generar reporte de texto legible"""
        txt_path = self.output_dir / f"duplicate_analysis_report_{timestamp}.txt"
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("ANÁLISIS DE DUPLICADOS - REPORTE DETALLADO\n")
            f.write("=" * 60 + "\n\n")
            
            # Resumen general
            summary = report_data['summary']
            f.write("RESUMEN GENERAL\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total de archivos: {summary['total_files']}\n")
            f.write(f"Archivos únicos: {summary['unique_files']}\n")
            f.write(f"Archivos duplicados: {summary['duplicate_files']}\n")
            f.write(f"Grupos de duplicados: {summary['duplicate_groups']}\n")
            f.write(f"Porcentaje de duplicados: {summary['duplicate_percentage']:.2f}%\n\n")
            
            # Análisis por carpeta
            f.write("ANÁLISIS POR CARPETA\n")
            f.write("-" * 30 + "\n")
            for folder, stats in report_data['folder_analysis'].items():
                f.write(f"\n{folder}:\n")
                f.write(f"  Total: {stats['total_files']} archivos\n")
                f.write(f"  Únicos: {stats['unique_files']} archivos\n")
                f.write(f"  Duplicados: {stats['duplicate_files']} archivos\n")
                f.write(f"  % Duplicados: {stats['duplicate_percentage']:.1f}%\n")
                f.write(f"  Espacio desperdiciado: {stats['wasted_space_mb']:.2f} MB\n")
            
            # Grupos de duplicados
            f.write("\n\nGRUPOS DE DUPLICADOS\n")
            f.write("-" * 30 + "\n")
            for i, (hash_val, files) in enumerate(report_data['duplicate_groups'].items(), 1):
                f.write(f"\nGrupo {i} (Hash: {hash_val[:8]}...):\n")
                for file_info in files:
                    f.write(f"  - {file_info['filename']} ({file_info['folder']})\n")
        
        print(f"   📄 Reporte de texto: {txt_path}")

def main():
    """Función principal"""
    print_stage_title("ANÁLISIS DE DUPLICADOS")
    
    # Configuración
    project_root = Path(__file__).parent.parent
    csv_file = project_root / "src" / "output" / "datasources" / "datasources_files_20251006_131302.csv"
    output_dir = project_root / "src" / "output" / "duplicates"
    
    print(f"📁 Archivo CSV: {csv_file}")
    print(f"📁 Directorio de salida: {output_dir}")
    
    # Crear analizador
    analyzer = DuplicateAnalyzer(csv_file, output_dir)
    
    # Ejecutar análisis
    if not analyzer.load_data():
        print("❌ Error al cargar datos")
        return
    
    if not analyzer.analyze_duplicates():
        print("❌ Error al analizar duplicados")
        return
    
    # Generar reportes
    reports = analyzer.generate_reports()
    
    print_stage_title("ANÁLISIS COMPLETADO")
    print("✅ Análisis de duplicados completado exitosamente")
    print(f"📊 Archivos únicos: {len(analyzer.unique_files)}")
    print(f"📊 Archivos duplicados: {len(analyzer.duplicate_files)}")
    print(f"📊 Grupos de duplicados: {len(analyzer.duplicate_groups)}")
    print(f"📁 Reportes guardados en: {output_dir}")

if __name__ == "__main__":
    main()
