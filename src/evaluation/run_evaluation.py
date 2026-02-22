#!/usr/bin/env python3
"""
Script Maestro para Evaluación - FASE A
======================================

FASE A: Evalúa 7 bases de conocimiento con KB mixta
Limitación conocida: Retrieval subóptimo por embeddings monolingües

Uso:
    python run_evaluation.py --collection <name> [--output-suffix <suffix>]
    python run_evaluation.py --all
    python run_evaluation.py --list

Autor: Laren Osorio Toribio
Fecha: 2025-01-11
"""

import os
import sys
import time
import subprocess
import requests
import argparse
from pathlib import Path
from datetime import datetime

# Agregar directorio raíz al path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from evaluate_ragas import RAGEvaluator

# FASE A: 7 Bases de Conocimiento (todas con KB mixta)
KNOWLEDGE_BASES = {
    "contextual": {
        "collection": "asistente-normativa-sincro-kb",
        "name": "Contextual RAG (Original)",
        "description": "Base de conocimiento contextual original"
    },
    "recursive": {
        "collection": "rag_recursive_character_construction",
        "name": "Recursive Character Chunking",
        "description": "Chunking recursivo por caracteres"
    },
    "structural": {
        "collection": "rag_structural_construction",
        "name": "Structural Chunking",
        "description": "Chunking estructural basado en markdown"
    },
    "semantic_p95": {
        "collection": "rag_semantic_construction",
        "name": "Semantic RAG (Percentil 95)",
        "description": "Semantic chunking con percentil 95"
    },
    "semantic_p75": {
        "collection": "rag_semantic_construction_p75",
        "name": "Semantic RAG (Percentil 75)",
        "description": "Semantic chunking con percentil 75"
    },
    "semantic_gradient": {
        "collection": "rag_semantic_construction_gradient",
        "name": "Semantic RAG (Gradient)",
        "description": "Semantic chunking con método gradient"
    },
    "hybrid": {
        "collection": "rag_hybrid_construction_p80_markdown",
        "name": "Hybrid Chunking (P80 + Markdown)",
        "description": "Chunking híbrido percentil 80 + markdown"
    }
}

class EvaluationManager:
    """Gestor de evaluaciones - FASE A"""
    
    def __init__(self):
        self.project_root = project_root
        self.evaluation_dir = self.project_root / "src" / "output" / "evaluation"
        self.api_process = None
        self.evaluation_dir.mkdir(parents=True, exist_ok=True)
    
    def start_api_rag(self, collection_name: str) -> bool:
        """Inicia la API RAG con la colección especificada."""
        try:
            print(f"🔧 Configurando API RAG para: {collection_name}")
            os.environ["QDRANT_COLLECTION_NAME"] = collection_name
            
            print("🚀 Iniciando API RAG...")
            api_path = self.project_root / "src" / "evaluation" / "api_rag.py"
            self.api_process = subprocess.Popen([
                "uv", "run", "python", str(api_path)
            ], cwd=str(self.project_root))
            
            return self.wait_for_api()
        except Exception as e:
            print(f"❌ Error iniciando API: {e}")
            return False
    
    def wait_for_api(self, timeout: int = 60) -> bool:
        """Espera a que la API esté disponible."""
        print("⏳ Esperando API...")
        
        for i in range(timeout):
            try:
                response = requests.get("http://localhost:8001/health", timeout=2)
                if response.status_code == 200:
                    print("✅ API disponible")
                    return True
            except:
                pass
            
            time.sleep(1)
            if i % 10 == 0 and i > 0:
                print(f"⏳ Esperando... ({i}/{timeout}s)")
        
        print("❌ Timeout esperando API")
        return False
    
    def print_kb_status(self, collection_name: str, kb_config: dict):
        """Imprime estado de la KB."""
        env_collection = os.getenv("QDRANT_COLLECTION_NAME", "not_set")
        match = env_collection == collection_name
        status = "✅ CORRECTO" if match else "❌ ERROR"
        
        print("\n" + "="*60)
        print("📊 ESTADO DE LA BASE DE CONOCIMIENTO - FASE A")
        print("="*60)
        print(f"Nombre: {kb_config['name']}")
        print(f"Colección: {collection_name}")
        print(f"Variable ENV: {env_collection}")
        print(f"Estado: {status}")
        print(f"Tipo KB: Mixta (2 docs ES + 2 docs EN)")
        print(f"Embeddings: nomic-embed-text (monolingüe)")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
    
    def stop_api_rag(self):
        """Detiene la API RAG."""
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                print("🛑 API detenida")
            except:
                self.api_process.kill()
                print("🛑 API forzada a detener")
            finally:
                self.api_process = None
    
    def evaluate_knowledge_base(self, kb_key: str, collection_name: str = None, output_suffix: str = None) -> bool:
        """Evalúa una base de conocimiento."""
        kb_config = KNOWLEDGE_BASES.get(kb_key)
        if not kb_config and not collection_name:
            print(f"❌ KB desconocida: {kb_key}")
            return False
        
        if not collection_name:
            collection_name = kb_config["collection"]
        
        if not kb_config:
            kb_config = {
                "name": collection_name,
                "description": "Custom KB"
            }
        
        print(f"\n{'='*60}")
        print(f"🔍 EVALUANDO: {kb_config['name']}")
        print(f"{'='*60}")
        
        try:
            if not self.start_api_rag(collection_name):
                print("❌ No se pudo iniciar la API")
                return False
            
            self.print_kb_status(collection_name, kb_config)
            
            # Crear evaluador con timeout aumentado
            evaluator = RAGEvaluator(api_url="http://localhost:8001")
            
            # Cargar dataset (filtrado a español en FASE A)
            try:
                dataset = evaluator.load_dataset()
                print(f"📊 Dataset: {len(dataset)} preguntas")
            except Exception as e:
                print(f"❌ Error cargando dataset: {e}")
                return False
            
            # Evaluar
            print("🔄 Ejecutando evaluación...")
            print("⏱️  Estimado: ~2-3 min por pregunta con Mistral")
            try:
                evaluator.results = evaluator.evaluate_batch(dataset, batch_size=3)
            except Exception as e:
                print(f"❌ Error durante evaluación: {e}")
                self.stop_api_rag()
                return False
            
            # Configurar output
            output_dir = self.evaluation_dir / (output_suffix or kb_key)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Exportar resultados
            evaluator.export_results(str(output_dir))
            
            # Resumen
            successful = len([r for r in evaluator.results if not r.error])
            total = len(evaluator.results)
            
            print(f"\n📊 RESULTADOS:")
            print(f"  Preguntas evaluadas: {successful}/{total}")
            
            if successful > 0:
                valid_results = [r for r in evaluator.results if not r.error]
                
                def safe_avg(scores):
                    valid = [s for s in scores if s is not None]
                    return sum(valid) / len(valid) if valid else 0.0
                
                avg_faithfulness = safe_avg([r.faithfulness_score for r in valid_results])
                avg_answer_relevancy = safe_avg([r.answer_relevancy_score for r in valid_results])
                avg_context_precision = safe_avg([r.context_precision_score for r in valid_results])
                avg_context_recall = safe_avg([r.context_recall_score for r in valid_results])
                avg_api_time = safe_avg([r.api_response_time for r in valid_results])
                
                print(f"  Faithfulness: {avg_faithfulness:.3f}")
                print(f"  Answer Relevancy: {avg_answer_relevancy:.3f}")
                print(f"  Context Precision: {avg_context_precision:.3f}")
                print(f"  Context Recall: {avg_context_recall:.3f}")
                print(f"  Tiempo promedio API: {avg_api_time:.2f}s")
                print(f"\n  ⚠️  Scores esperados bajos (0.30-0.50) por limitación KB mixta")
            
            print(f"📁 Resultados: {output_dir}")
            print("✅ Evaluación completada")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        finally:
            self.stop_api_rag()
    
    def evaluate_all(self) -> bool:
        """Evalúa todas las 7 bases de conocimiento."""
        print("🚀 FASE A: EVALUANDO 7 BASES DE CONOCIMIENTO")
        print("=" * 60)
        print("⚠️  Limitación conocida: KB mixta + embeddings monolingües")
        print("📊 Objetivo: Comparación RELATIVA entre métodos")
        print("=" * 60)
        
        results = {}
        
        try:
            for i, (kb_key, kb_config) in enumerate(KNOWLEDGE_BASES.items(), 1):
                print(f"\n🔄 Progreso: {i}/{len(KNOWLEDGE_BASES)}")
                
                success = self.evaluate_knowledge_base(kb_key)
                
                results[kb_key] = {
                    "success": success,
                    "name": kb_config["name"],
                    "collection": kb_config["collection"]
                }
                
                # Pausa entre evaluaciones
                if i < len(KNOWLEDGE_BASES):
                    print(f"\n⏳ Pausa 10s antes de siguiente evaluación...")
                    time.sleep(10)
            
            # Resumen
            print(f"\n{'='*60}")
            print("📊 RESUMEN FASE A")
            print(f"{'='*60}")
            
            successful = sum(1 for r in results.values() if r["success"])
            total = len(results)
            
            print(f"Total: {total}")
            print(f"Exitosas: {successful}")
            print(f"Fallidas: {total - successful}")
            print()
            
            for kb_key, result in results.items():
                status = "✅" if result["success"] else "❌"
                print(f"{status} {result['name']}")
            
            print(f"\n📁 Resultados: {self.evaluation_dir}")
            
            # Generar reporte comparativo
            print(f"\n📊 Generando reporte comparativo...")
            try:
                subprocess.run([
                    "uv", "run", "python",
                    str(self.project_root / "src" / "evaluation" / "generate_comparison_report.py")
                ], cwd=str(self.project_root), check=True)
                print("✅ Reporte generado")
            except Exception as e:
                print(f"⚠️  Error generando reporte: {e}")
            
            return successful == total
            
        except KeyboardInterrupt:
            print("\n⏹️  Interrumpido")
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

def list_knowledge_bases():
    """Lista las 7 bases de conocimiento."""
    print("📋 BASES DE CONOCIMIENTO DISPONIBLES (FASE A)")
    print("=" * 60)
    
    for kb_key, kb_config in KNOWLEDGE_BASES.items():
        print(f"\n🔑 {kb_key}")
        print(f"   Colección: {kb_config['collection']}")
        print(f"   Nombre: {kb_config['name']}")
        print(f"   Descripción: {kb_config['description']}")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Evaluador FASE A - 7 Bases de Conocimiento",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--collection", help="Nombre de la colección")
    group.add_argument("--all", action="store_true", help="Evaluar todas")
    group.add_argument("--list", action="store_true", help="Listar KBs")
    
    parser.add_argument("--output-suffix", help="Sufijo para output")
    
    args = parser.parse_args()
    
    if args.list:
        list_knowledge_bases()
        return
    
    manager = EvaluationManager()

    try:
        if args.all:
            success = manager.evaluate_all()
            sys.exit(0 if success else 1)
        else:
            # Buscar kb_key o usar custom collection
            kb_key = None
            for key, config in KNOWLEDGE_BASES.items():
                if config["collection"] == args.collection:
                    kb_key = key
                    break
            
            if kb_key:
                success = manager.evaluate_knowledge_base(kb_key, output_suffix=args.output_suffix)
            else:
                success = manager.evaluate_knowledge_base(
                    kb_key="custom",
                    collection_name=args.collection,
                    output_suffix=args.output_suffix
                )
            
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        manager.stop_api_rag()

if __name__ == "__main__":
    main()