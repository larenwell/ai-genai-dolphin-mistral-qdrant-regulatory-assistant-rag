#!/usr/bin/env python3
"""
Script para Aplicar Optimizaciones de Chunking
==============================================

Este script aplica las optimizaciones identificadas en el análisis
al código de producción del sistema RAG Contextual.

Optimizaciones a aplicar:
1. Reducir chunk_size de 1000 a 500
2. Reducir chunk_overlap de 200 a 100
3. Simplificar prompt de contextualización
4. Mejorar separadores para chunking
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Configuración
project_root = Path(__file__).parent.parent.parent
backup_dir = project_root / "src" / "output" / "process" / "backups"
backup_dir.mkdir(parents=True, exist_ok=True)

def create_backup(file_path):
    """Crea una copia de seguridad del archivo"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{file_path.name}_{timestamp}.backup"
    shutil.copy2(file_path, backup_file)
    print(f"✅ Backup creado: {backup_file}")
    return backup_file

def apply_optimizations():
    """Aplica las optimizaciones al código de producción"""
    
    print("🚀 APLICANDO OPTIMIZACIONES DE CHUNKING")
    print("=" * 60)
    
    # Archivo a optimizar
    target_file = project_root / "src" / "ingestion" / "ingest_mistral.py"
    
    if not target_file.exists():
        print(f"❌ Error: No se encontró el archivo {target_file}")
        return False
    
    # Crear backup
    print(f"📁 Creando backup de {target_file.name}...")
    create_backup(target_file)
    
    # Leer archivo actual
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Aplicar optimizaciones
    print("🔧 Aplicando optimizaciones...")
    
    # 1. Optimizar parámetros de chunking
    old_chunking = """        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\\n\\n", "\\n", " ", ""]
        )"""
    
    new_chunking = """        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,        # Optimizado: reducido de 1000
            chunk_overlap=100,     # Optimizado: reducido de 200
            separators=["\\n\\n", "\\n", ". ", " "]  # Optimizado: mejor separación
        )"""
    
    if old_chunking in content:
        content = content.replace(old_chunking, new_chunking)
        print("   ✅ Parámetros de chunking optimizados")
    else:
        print("   ⚠️  No se encontró configuración de chunking para optimizar")
    
    # 2. Optimizar prompt de contextualización
    old_prompt = '''        context_prompt = f"""
DOCUMENT: {book_title}
PAGE: {page_num}

DOCUMENT SUMMARY:
{document_summary}

FRAGMENT CONTENT:
{chunk_content}

VISUAL ELEMENTS: {visual_summary}

INSTRUCTIONS:
Create a contextualized summary of this fragment that:
1. Explains the content in relation to the complete document
2. Preserves key technical information
3. Briefly describes visual elements if they exist
4. Maintains specific terminology for search
5. Is concise but informative (maximum 300 words)

IMPORTANT: Keep the original technical language and specific concepts.
"""'''
    
    new_prompt = '''        context_prompt = f"""
DOCUMENT: {book_title}
PAGE: {page_num}

FRAGMENT CONTENT:
{chunk_content}

INSTRUCTIONS:
Create a brief contextual summary (max 100 words) that:
1. Preserves the original technical language and specific terminology
2. Maintains exact numbers, codes, and references
3. Adds minimal context for understanding
4. Keeps the original structure and formatting intact

IMPORTANT: Do not paraphrase technical terms or change specific values.
"""'''
    
    if old_prompt in content:
        content = content.replace(old_prompt, new_prompt)
        print("   ✅ Prompt de contextualización optimizado")
    else:
        print("   ⚠️  No se encontró prompt de contextualización para optimizar")
    
    # 3. Optimizar umbral de subdivisión de chunks
    old_threshold = "                            if len(content) > 1200:"
    new_threshold = "                            if len(content) > 600:  # Optimizado: reducido de 1200"
    
    if old_threshold in content:
        content = content.replace(old_threshold, new_threshold)
        print("   ✅ Umbral de subdivisión optimizado")
    else:
        print("   ⚠️  No se encontró umbral de subdivisión para optimizar")
    
    # Guardar archivo optimizado
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Optimizaciones aplicadas a {target_file.name}")
    
    # Crear archivo de configuración optimizada
    config_file = project_root / "src" / "output" / "process" / "chunking_optimization_config.md"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write("""# Configuración de Chunking Optimizada

## Parámetros Aplicados

### RecursiveCharacterTextSplitter
- **chunk_size:** 1000 → 500 caracteres
- **chunk_overlap:** 200 → 100 caracteres  
- **separators:** ["\\n\\n", "\\n", ". ", " "] (mejor separación)

### Contextualización
- **Prompt simplificado:** Máximo 100 palabras
- **Preservación:** Terminología técnica y referencias específicas
- **Contexto mínimo:** Solo información esencial

### Umbral de Subdivisión
- **Tamaño máximo:** 1200 → 600 caracteres
- **Subdivisión automática:** Para chunks que excedan el límite

## Beneficios Esperados

1. **Mejor Context Precision:** Chunks más pequeños y enfocados
2. **Mejor Answer Relevancy:** Contextualización mínima preserva relevancia
3. **Mejor Faithfulness:** Preservación de información específica
4. **Mejor Context Recall:** Mayor granularidad para cobertura completa

## Próximos Pasos

1. Reprocesar documentos existentes con configuración optimizada
2. Ejecutar evaluación RAGAS para validar mejoras
3. Monitorear métricas de calidad de chunking
4. Ajustar parámetros según resultados

## Archivos Modificados

- `src/ingestion/ingest_mistral.py` - Configuración de chunking optimizada
""")
    
    print(f"📝 Configuración guardada en: {config_file}")
    
    return True

def create_reprocessing_script():
    """Crea un script para reprocesar documentos con configuración optimizada"""
    
    script_content = '''#!/usr/bin/env python3
"""
Script de Reprocesamiento con Chunking Optimizado
================================================

Este script reprocesa todos los documentos PDF con la configuración
de chunking optimizada para mejorar las métricas RAGAS.

Uso:
    python reprocess_with_optimized_chunking.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Configuración
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
load_dotenv(project_root / '.env')

from ingestion_manual_mistral import operate_in_folder

def main():
    """Reprocesa documentos con chunking optimizado"""
    print("🚀 REPROCESAMIENTO CON CHUNKING OPTIMIZADO")
    print("=" * 60)
    
    # Verificar que las optimizaciones estén aplicadas
    ingest_file = project_root / "src" / "ingestion" / "ingest_mistral.py"
    with open(ingest_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "chunk_size=500" not in content:
        print("❌ Error: Las optimizaciones no están aplicadas")
        print("   Ejecuta primero: python apply_chunking_optimizations.py")
        return
    
    print("✅ Optimizaciones verificadas")
    
    # Directorio de PDFs
    pdf_folder = project_root / "data" / "test"
    
    if not pdf_folder.exists():
        print(f"❌ Error: No se encontró el directorio {pdf_folder}")
        return
    
    print(f"📁 Procesando PDFs en: {pdf_folder}")
    
    # Cambiar al directorio src para ejecutar
    os.chdir(project_root / "src")
    
    # Ejecutar reprocesamiento
    try:
        operate_in_folder("../data/test")
        print("\\n✅ Reprocesamiento completado exitosamente")
        print("📊 Ejecuta la evaluación RAGAS para validar mejoras")
    except Exception as e:
        print(f"❌ Error durante el reprocesamiento: {str(e)}")

if __name__ == "__main__":
    main()
'''
    
    script_file = project_root / "src" / "output" / "process" / "reprocess_with_optimized_chunking.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Hacer el script ejecutable
    os.chmod(script_file, 0o755)
    
    print(f"📜 Script de reprocesamiento creado: {script_file}")
    return script_file

def main():
    """Función principal"""
    print("🔧 APLICADOR DE OPTIMIZACIONES DE CHUNKING")
    print("=" * 60)
    
    # Aplicar optimizaciones
    if apply_optimizations():
        print("\\n✅ Optimizaciones aplicadas exitosamente")
        
        # Crear script de reprocesamiento
        reprocess_script = create_reprocessing_script()
        
        print("\\n📋 PRÓXIMOS PASOS:")
        print("1. Verificar que las optimizaciones se aplicaron correctamente")
        print("2. Ejecutar el reprocesamiento:")
        print(f"   cd {project_root}/src")
        print(f"   python {reprocess_script.name}")
        print("3. Ejecutar evaluación RAGAS para validar mejoras")
        print("4. Comparar métricas antes/después")
        
    else:
        print("\\n❌ Error aplicando optimizaciones")
        print("   Revisa los logs para más detalles")

if __name__ == "__main__":
    main()
