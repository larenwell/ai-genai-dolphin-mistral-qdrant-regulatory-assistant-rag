#!/usr/bin/env python3
"""
Script para Filtrar Dataset - FASE A
====================================

Filtra el dataset de evaluación para incluir SOLO preguntas en español.

FASE A: Evaluar con preguntas en español sobre ambos tipos de documentos:
- Preguntas en español sobre docs españoles (Ley 30947, DS 034-2023-EM)
- Preguntas en español sobre docs ingleses (FMDS0104, FMDS0520)

Esto refleja el uso real: usuarios preguntan en español, independientemente
del idioma del documento fuente.

Uso:
    python filter_dataset.py

Output:
    data/evaluation_dataset_spanish_only.jsonl

Autor: Laren Osorio Toribio
Fecha: 2025-01-11
"""

import json
from pathlib import Path
from typing import List, Dict, Any

def detect_question_language(text: str) -> str:
    """
    Detecta el idioma de una pregunta (heurística simple).
    
    Args:
        text: Texto de la pregunta
        
    Returns:
        "spanish" | "english"
    """
    # Indicadores de español
    spanish_indicators = [
        '¿', '¡', 'á', 'é', 'í', 'ó', 'ú', 'ñ',
        'qué', 'cuál', 'cómo', 'dónde', 'cuándo', 'por qué',
        'es', 'está', 'son', 'están', 'de', 'la', 'el', 'en',
        'para', 'con', 'por', 'se', 'los', 'las'
    ]
    
    # Indicadores de inglés
    english_indicators = [
        'what', 'which', 'how', 'where', 'when', 'why',
        'is', 'are', 'the', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'an', 'be'
    ]
    
    text_lower = text.lower()
    
    # Contar indicadores
    spanish_count = sum(1 for indicator in spanish_indicators if indicator in text_lower)
    english_count = sum(1 for indicator in english_indicators if indicator in text_lower)
    
    # Decisión
    if spanish_count > english_count:
        return "spanish"
    elif english_count > spanish_count:
        return "english"
    else:
        # Si empate, usar signos de puntuación españoles como desempate
        if '¿' in text or '¡' in text:
            return "spanish"
        return "english"

def load_full_dataset(file_path: Path) -> List[Dict[str, Any]]:
    """
    Carga el dataset completo (64 preguntas: 32 ES + 32 EN).
    
    Args:
        file_path: Ruta al archivo JSONL
        
    Returns:
        Lista de preguntas
    """
    questions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        questions.append(data)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Error en línea {line_num}: {e}")
        
        print(f"✅ Dataset completo cargado: {len(questions)} preguntas")
        return questions
        
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error cargando dataset: {e}")
        return []

def filter_spanish_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filtra solo las preguntas en español.
    
    Args:
        questions: Lista completa de preguntas
        
    Returns:
        Lista filtrada con solo preguntas en español
    """
    spanish_questions = []
    english_questions = []
    
    for question in questions:
        text = question.get("question", "")
        language = detect_question_language(text)
        
        if language == "spanish":
            spanish_questions.append(question)
        else:
            english_questions.append(question)
    
    print(f"\n📊 ANÁLISIS DEL DATASET:")
    print(f"  Total original: {len(questions)}")
    print(f"  Español: {len(spanish_questions)}")
    print(f"  Inglés: {len(english_questions)}")
    
    return spanish_questions

def save_filtered_dataset(questions: List[Dict[str, Any]], output_path: Path):
    """
    Guarda el dataset filtrado.
    
    Args:
        questions: Preguntas filtradas
        output_path: Ruta de salida
    """
    try:
        # Crear directorio si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar en formato JSONL
        with open(output_path, 'w', encoding='utf-8') as f:
            for question in questions:
                json_line = json.dumps(question, ensure_ascii=False)
                f.write(json_line + '\n')
        
        print(f"\n✅ Dataset filtrado guardado: {output_path}")
        print(f"   Total preguntas: {len(questions)}")
        
        # Análisis por tipo de pregunta
        types_count = {}
        for q in questions:
            qtype = q.get("question_type", "unknown")
            types_count[qtype] = types_count.get(qtype, 0) + 1
        
        print(f"\n📋 DISTRIBUCIÓN POR TIPO:")
        for qtype, count in sorted(types_count.items()):
            print(f"  {qtype}: {count}")
        
    except Exception as e:
        print(f"❌ Error guardando dataset: {e}")

def verify_dataset_content(questions: List[Dict[str, Any]]):
    """
    Verifica el contenido del dataset filtrado.
    
    Muestra ejemplos de preguntas para validación manual.
    """
    print(f"\n🔍 VERIFICACIÓN DEL CONTENIDO:")
    print("="*60)
    
    # Mostrar ejemplos de cada tipo de pregunta
    types_shown = set()
    
    for question in questions:
        qtype = question.get("question_type", "unknown")
        
        if qtype not in types_shown:
            print(f"\n📌 Tipo: {qtype}")
            print(f"   Pregunta: {question.get('question', '')[:100]}...")
            print(f"   Ground truth: {question.get('ground_truth', '')[:80]}...")
            types_shown.add(qtype)
        
        if len(types_shown) >= 5:  # Mostrar máximo 5 ejemplos
            break
    
    print("="*60)

def main():
    """Función principal"""
    print("="*60)
    print("🔍 FILTRADO DE DATASET PARA FASE A")
    print("="*60)
    print("Objetivo: Crear dataset solo con preguntas en español")
    print("Input: evaluation_dataset.jsonl (64 preguntas)")
    print("Output: evaluation_dataset_spanish_only.jsonl (32 preguntas)")
    print("="*60)
    
    # Rutas
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    
    input_file = data_dir / "evaluation_dataset.jsonl"
    output_file = data_dir / "evaluation_dataset_spanish_only.jsonl"
    
    # Cargar dataset completo
    print(f"\n📂 Cargando dataset completo...")
    print(f"   Archivo: {input_file}")
    
    questions = load_full_dataset(input_file)
    
    if not questions:
        print("\n❌ No se pudo cargar el dataset. Verifica la ruta:")
        print(f"   {input_file.absolute()}")
        return
    
    # Filtrar solo español
    print(f"\n🔍 Filtrando preguntas en español...")
    spanish_questions = filter_spanish_questions(questions)
    
    if not spanish_questions:
        print("\n❌ No se encontraron preguntas en español")
        return
    
    # Guardar dataset filtrado
    print(f"\n💾 Guardando dataset filtrado...")
    save_filtered_dataset(spanish_questions, output_file)
    
    # Verificar contenido
    verify_dataset_content(spanish_questions)
    
    # Resumen final
    print(f"\n✅ PROCESO COMPLETADO")
    print("="*60)
    print(f"📁 Archivo generado: {output_file}")
    print(f"📊 Preguntas en español: {len(spanish_questions)}")
    print(f"🎯 Listo para evaluación FASE A")
    print("="*60)
    
    print(f"\n📝 NOTAS IMPORTANTES:")
    print("  • Las preguntas en español incluyen preguntas sobre docs ES y EN")
    print("  • Esto refleja el uso real: usuarios preguntan en español")
    print("  • Se espera retrieval pobre en preguntas sobre docs ingleses")
    print("  • Los scores bajos son esperados por la limitación arquitectural")
    print("\n💡 SIGUIENTE PASO:")
    print("  python run_evaluation.py --all")

if __name__ == "__main__":
    main()