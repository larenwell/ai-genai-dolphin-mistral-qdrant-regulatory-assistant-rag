#!/usr/bin/env python3
"""
Script para Generar Reporte Comparativo - FASE A
================================================

Genera reporte comparativo de las 7 bases de conocimiento evaluadas.
Incluye faithfulness y análisis por idioma.

Uso:
    python generate_comparison_report.py

Autor: Laren Osorio Toribio
Fecha: 2025-01-11
"""

import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Agregar directorio raíz al path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def load_evaluation_results(evaluation_dir: Path) -> Dict[str, Any]:
    """
    Carga los resultados de todas las evaluaciones.
    
    Args:
        evaluation_dir: Directorio de evaluaciones
        
    Returns:
        Diccionario con resultados por base de conocimiento
    """
    results = {}
    
    # Buscar archivos JSON de resultados
    json_files = glob.glob(str(evaluation_dir / "**" / "evaluation_results_*.json"), recursive=True)
    
    print(f"Archivos JSON encontrados: {len(json_files)}")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Determinar el tipo de KB basado en la ruta
            path_parts = Path(json_file).parts
            kb_type = None
            
            # Lista completa de 7 KBs
            kb_names = [
                "contextual", "recursive", "structural",
                "semantic_p95", "semantic_p75", "semantic_gradient",
                "hybrid"
            ]
            
            for part in path_parts:
                if part in kb_names:
                    kb_type = part
                    break
            
            if kb_type and "evaluation_metadata" in data:
                metadata = data["evaluation_metadata"]
                
                # Calcular métricas promedio
                if "results" in data and data["results"]:
                    valid_results = [r for r in data["results"] if not r.get("error")]
                    
                    if valid_results:
                        # Calcular promedios con manejo de None/NaN
                        def safe_avg(key):
                            values = [r.get(key, 0) for r in valid_results if r.get(key) is not None]
                            return sum(values) / len(values) if values else 0.0
                        
                        avg_faithfulness = safe_avg("faithfulness_score")
                        avg_answer_relevancy = safe_avg("answer_relevancy_score")
                        avg_context_precision = safe_avg("context_precision_score")
                        avg_context_recall = safe_avg("context_recall_score")
                        avg_api_time = safe_avg("api_response_time")
                        
                        # Contar errores de faithfulness
                        faithfulness_errors = len([r for r in valid_results 
                                                  if r.get("faithfulness_error")])
                    else:
                        avg_faithfulness = avg_answer_relevancy = 0.0
                        avg_context_precision = avg_context_recall = avg_api_time = 0.0
                        faithfulness_errors = 0
                else:
                    avg_faithfulness = avg_answer_relevancy = 0.0
                    avg_context_precision = avg_context_recall = avg_api_time = 0.0
                    faithfulness_errors = 0
                
                # Métricas por idioma (si existen)
                metrics_by_lang = data.get("metrics_by_language", {})
                
                results[kb_type] = {
                    "name": get_kb_display_name(kb_type),
                    "timestamp": metadata.get("timestamp", "Unknown"),
                    "total_questions": metadata.get("total_questions", 0),
                    "successful_evaluations": metadata.get("successful_evaluations", 0),
                    "failed_evaluations": metadata.get("failed_evaluations", 0),
                    "avg_faithfulness": avg_faithfulness,
                    "avg_answer_relevancy": avg_answer_relevancy,
                    "avg_context_precision": avg_context_precision,
                    "avg_context_recall": avg_context_recall,
                    "avg_api_time": avg_api_time,
                    "faithfulness_errors": faithfulness_errors,
                    "metrics_by_language": metrics_by_lang,
                    "file_path": json_file
                }
                
                print(f"  ✅ Cargado: {kb_type}")
                
        except Exception as e:
            print(f"  ⚠️  Error cargando {json_file}: {e}")
    
    return results

def get_kb_display_name(kb_type: str) -> str:
    """Obtiene el nombre de visualización para el tipo de KB - FASE A (7 KBs)"""
    names = {
        "contextual": "Contextual RAG (Original)",
        "recursive": "Recursive Character Chunking",
        "structural": "Structural Chunking",
        "semantic_p95": "Semantic RAG (Percentil 95)",
        "semantic_p75": "Semantic RAG (Percentil 75)",
        "semantic_gradient": "Semantic RAG (Gradient)",
        "hybrid": "Hybrid Chunking (P80 + Markdown)"
    }
    return names.get(kb_type, kb_type.title())

def generate_comparison_report(results: Dict[str, Any]) -> str:
    """
    Genera el reporte comparativo - FASE A.
    
    Args:
        results: Resultados de las evaluaciones
        
    Returns:
        Reporte en formato texto
    """
    report = []
    report.append("=" * 100)
    report.append("REPORTE COMPARATIVO - FASE A: 7 BASES DE CONOCIMIENTO")
    report.append("=" * 100)
    report.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Bases de conocimiento evaluadas: {len(results)}/7")
    report.append("")
    report.append("ADVERTENCIA FASE A:")
    report.append("  • Scores absolutos bajos esperados (0.30-0.50)")
    report.append("  • Limitación: KB mixta + embeddings monolingües")
    report.append("  • Objetivo: Comparación RELATIVA entre métodos")
    report.append("")
    
    if not results:
        report.append("❌ No se encontraron resultados de evaluación")
        return "\n".join(report)
    
    # Tabla comparativa
    report.append("TABLA COMPARATIVA")
    report.append("-" * 130)
    header = f"{'Base de Conocimiento':<32} {'Faith':<8} {'Relev':<8} {'Precis':<8} {'Recall':<8} {'F-Err':<6} {'API Time':<10}"
    report.append(header)
    report.append("-" * 130)
    
    # Ordenar por puntuación compuesta
    sorted_results = sorted(
        results.items(),
        key=lambda x: (x[1]['avg_faithfulness'] + x[1]['avg_answer_relevancy'] + 
                      x[1]['avg_context_precision'] + x[1]['avg_context_recall']) / 4,
        reverse=True
    )
    
    for kb_type, result in sorted_results:
        name = result["name"][:31]
        faith = f"{result['avg_faithfulness']:.3f}"
        relev = f"{result['avg_answer_relevancy']:.3f}"
        precis = f"{result['avg_context_precision']:.3f}"
        recall = f"{result['avg_context_recall']:.3f}"
        f_err = f"{result['faithfulness_errors']}"
        api_time = f"{result['avg_api_time']:.2f}s"
        
        report.append(f"{name:<32} {faith:<8} {relev:<8} {precis:<8} {recall:<8} {f_err:<6} {api_time:<10}")
    
    report.append("-" * 130)
    report.append("")
    
    # Rankings
    report.append("RANKINGS POR MÉTRICA")
    report.append("-" * 50)
    
    metrics = [
        ("avg_faithfulness", "Faithfulness"),
        ("avg_answer_relevancy", "Answer Relevancy"),
        ("avg_context_precision", "Context Precision"),
        ("avg_context_recall", "Context Recall")
    ]
    
    for metric_key, metric_name in metrics:
        best = max(results.items(), key=lambda x: x[1][metric_key], default=(None, None))
        if best[0]:
            report.append(f"🏆 {metric_name}: {best[1]['name']} ({best[1][metric_key]:.3f})")
    
    # Mejor tiempo
    best_time = min(results.items(), key=lambda x: x[1]['avg_api_time'], default=(None, None))
    if best_time[0]:
        report.append(f"⚡ Mejor tiempo API: {best_time[1]['name']} ({best_time[1]['avg_api_time']:.2f}s)")
    
    report.append("")
    
    # Mejor general
    if results:
        best_overall = sorted_results[0]
        composite = (best_overall[1]['avg_faithfulness'] + 
                    best_overall[1]['avg_answer_relevancy'] + 
                    best_overall[1]['avg_context_precision'] + 
                    best_overall[1]['avg_context_recall']) / 4
        
        report.append("MEJOR BASE DE CONOCIMIENTO GENERAL")
        report.append("-" * 50)
        report.append(f"🏆 {best_overall[1]['name']}")
        report.append(f"   Puntuación compuesta: {composite:.3f}")
        report.append(f"   Faithfulness: {best_overall[1]['avg_faithfulness']:.3f}")
        report.append(f"   Answer Relevancy: {best_overall[1]['avg_answer_relevancy']:.3f}")
        report.append(f"   Context Precision: {best_overall[1]['avg_context_precision']:.3f}")
        report.append(f"   Context Recall: {best_overall[1]['avg_context_recall']:.3f}")
        report.append("")
    
    # Análisis por idioma (si existe)
    report.append("ANÁLISIS POR IDIOMA DEL DOCUMENTO")
    report.append("-" * 50)
    
    has_lang_analysis = False
    for kb_type, result in sorted_results:
        if result.get("metrics_by_language"):
            has_lang_analysis = True
            report.append(f"\n{result['name']}:")
            for lang, metrics in result["metrics_by_language"].items():
                if metrics.get("count", 0) > 0:
                    report.append(f"  {lang}: {metrics['count']} preguntas")
                    report.append(f"    Faithfulness: {metrics.get('faithfulness_avg', 0):.3f}")
                    report.append(f"    Relevancy: {metrics.get('answer_relevancy_avg', 0):.3f}")
                    report.append(f"    Precision: {metrics.get('context_precision_avg', 0):.3f}")
                    report.append(f"    Recall: {metrics.get('context_recall_avg', 0):.3f}")
    
    if not has_lang_analysis:
        report.append("  (No disponible en resultados)")
    
    report.append("")
    
    # Análisis detallado
    report.append("ANÁLISIS DETALLADO POR BASE DE CONOCIMIENTO")
    report.append("-" * 50)
    
    for kb_type, result in sorted_results:
        report.append(f"\n{result['name'].upper()}")
        report.append(f"  Timestamp: {result['timestamp']}")
        report.append(f"  Preguntas: {result['successful_evaluations']}/{result['total_questions']}")
        report.append(f"  Faithfulness: {result['avg_faithfulness']:.3f} (errores: {result['faithfulness_errors']})")
        report.append(f"  Answer Relevancy: {result['avg_answer_relevancy']:.3f}")
        report.append(f"  Context Precision: {result['avg_context_precision']:.3f}")
        report.append(f"  Context Recall: {result['avg_context_recall']:.3f}")
        report.append(f"  Tiempo API: {result['avg_api_time']:.2f}s")
        report.append(f"  Archivo: {Path(result['file_path']).name}")
    
    # Recomendaciones FASE A
    report.append("\nRECOMENDACIONES FASE A")
    report.append("-" * 50)
    
    if sorted_results:
        winner = sorted_results[0][1]
        report.append(f"✅ Mejor método: {winner['name']}")
        report.append(f"   → Usar este método para FASE B (KBs limpias)")
        report.append("")
        report.append("⚠️  ADVERTENCIAS:")
        report.append("   • Todos los scores son bajos (limitación arquitectural)")
        report.append("   • KB mixta + embeddings monolingües = retrieval subóptimo")
        report.append("   • Preguntas ESP sobre docs ENG tienen scores muy bajos")
        report.append("")
        report.append("💡 SIGUIENTE PASO (FASE B):")
        report.append(f"   1. Crear 2 KBs con {winner['name']}")
        report.append("      - rag_recursive_ES (solo 2 docs español)")
        report.append("      - rag_recursive_EN (solo 2 docs inglés)")
        report.append("   2. Re-evaluar con KBs separadas")
        report.append("   3. Scores esperados: 0.70-0.85 (+75% mejora)")
    
    report.append("\n" + "=" * 100)
    
    return "\n".join(report)

def main():
    """Función principal"""
    print("=" * 60)
    print("📊 Generador de Reporte Comparativo - FASE A")
    print("=" * 60)
    
    # Directorio de evaluaciones
    evaluation_dir = project_root / "src" / "output" / "evaluation"
    
    if not evaluation_dir.exists():
        print(f"❌ Directorio no encontrado: {evaluation_dir}")
        print(f"   Ruta esperada: {evaluation_dir.absolute()}")
        return
    
    # Cargar resultados
    print("\n📁 Cargando resultados...")
    results = load_evaluation_results(evaluation_dir)
    
    if not results:
        print("\n❌ No se encontraron resultados de evaluación")
        print("   Asegúrate de haber ejecutado: python run_evaluation.py --all")
        return
    
    print(f"\n✅ Cargados {len(results)}/7 conjuntos de resultados")
    
    # Generar reporte
    print("\n📝 Generando reporte comparativo...")
    report = generate_comparison_report(results)
    
    # Guardar reporte
    comparison_dir = evaluation_dir / "comparison"
    comparison_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = comparison_dir / f"comparison_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Reporte guardado: {report_file}")
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

if __name__ == "__main__":
    main()