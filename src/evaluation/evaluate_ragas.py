#!/usr/bin/env python3
"""
Evaluación RAG con RAGAS - FASE A
==================================

FASE A: Evaluación con KB mixta + detección de idioma de documentos
- Reactivado faithfulness con manejo robusto de errores
- Análisis por idioma del documento fuente
- Timeout aumentado para Mistral evaluador

Autor: Laren Osorio Toribio
Fecha: 2025-01-11
"""

import os
import sys
import json
import time
import math
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

sys.path.append('/usr/local/lib/python3.12/dist-packages')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# RAGAS imports
from ragas import evaluate
from ragas.metrics import (
    faithfulness,  # ✅ REACTIVADO
    answer_relevancy,
    context_precision,
    context_recall
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from datasets import Dataset

from langchain_community.embeddings import OllamaEmbeddings as LangChainOllamaEmbeddings
from langchain_mistralai import ChatMistralAI as LangChainMistralAI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluation_ragas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """Resultado de evaluación - FASE A"""
    question: str
    answer: str
    ground_truth: str
    context: List[str]
    question_type: str
    document_language: str  # ✅ NUEVO: "ES", "EN", "MIXED", "UNKNOWN"
    faithfulness_score: float  # ✅ REACTIVADO
    answer_relevancy_score: float
    context_precision_score: float
    context_recall_score: float
    api_response_time: float
    evaluation_time: float
    context_sources: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    faithfulness_error: Optional[str] = None  # ✅ Track errores específicos

class RAGEvaluator:
    """Evaluador RAG - FASE A con faithfulness y análisis por idioma"""
    
    def __init__(self, api_url: str = "http://localhost:8001", dataset_path: str = None):
        self.api_url = api_url
        self.dataset_path = dataset_path or Path(__file__).parent / "data" / "evaluation_dataset_spanish_only.jsonl"
        self.results: List[EvaluationResult] = []
        
        self._setup_mistral_for_ragas()
        self._setup_ragas_metrics()
        
        logger.info("RAGEvaluator FASE A inicializado")
    
    def _setup_mistral_for_ragas(self):
        """Configura Mistral para RAGAS"""
        try:
            mistral_langchain = LangChainMistralAI(
                api_key=os.getenv("MISTRAL_API_KEY"),
                model="mistral-large-latest",
                temperature=0.0  # Determinístico para evaluación
            )
            self.mistral_llm = LangchainLLMWrapper(mistral_langchain)
            
            ollama_langchain = LangChainOllamaEmbeddings(
                model="nomic-embed-text",
                base_url="http://localhost:11434"
            )
            self.ollama_embeddings = LangchainEmbeddingsWrapper(ollama_langchain)
            
            logger.info("Mistral configurado para RAGAS")
        except Exception as e:
            logger.error(f"Error configurando Mistral: {e}")
            raise
    
    def _setup_ragas_metrics(self):
        """Configura métricas RAGAS - FASE A con faithfulness"""
        self.metrics = [
            faithfulness,      # ✅ REACTIVADO con manejo robusto
            answer_relevancy,
            context_precision,
            context_recall
        ]
        logger.info("Métricas FASE A: faithfulness, answer_relevancy, context_precision, context_recall")
    
    def _detect_document_language(self, context_sources: List[Dict]) -> str:
        """
        Detecta idioma predominante del contexto recuperado
        
        Returns:
            "ES" | "EN" | "MIXED" | "UNKNOWN"
        """
        if not context_sources:
            return "UNKNOWN"
        
        spanish_docs = ["DS NRO 034-2023-EM", "Ley NRO 30947"]
        english_docs = ["FMDS0104", "FMDS0520"]
        
        es_count = 0
        en_count = 0
        
        for source in context_sources:
            doc_name = source.get("document_name", "")
            if any(es_doc in doc_name for es_doc in spanish_docs):
                es_count += 1
            elif any(en_doc in doc_name for en_doc in english_docs):
                en_count += 1
        
        if es_count > en_count:
            return "ES"
        elif en_count > es_count:
            return "EN"
        elif es_count == en_count and es_count > 0:
            return "MIXED"
        else:
            return "UNKNOWN"
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Carga dataset (filtrado a español en FASE A)"""
        try:
            dataset = []
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            dataset.append(data)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Error línea {line_num}: {e}")
            
            logger.info(f"Dataset cargado: {len(dataset)} preguntas")
            return dataset
        except FileNotFoundError:
            logger.error(f"Dataset no encontrado: {self.dataset_path}")
            raise
    
    def check_api_availability(self) -> bool:
        """Verifica disponibilidad de API"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("API disponible")
                return True
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"API no disponible: {e}")
            return False
    
    def query_rag_api(self, question: str) -> Dict[str, Any]:
        """Consulta API RAG con timeout aumentado"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.api_url}/rag",
                json={"question": question},
                timeout=90  # ✅ Aumentado de 30 a 90s
            )
            
            api_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                context = data.get("context", data.get("relevant_docs", []))
                context_sources = data.get("context_sources", [])
                
                if isinstance(context, str):
                    try:
                        context = json.loads(context)
                    except:
                        context = [context]
                
                if isinstance(context_sources, str):
                    try:
                        context_sources = json.loads(context_sources)
                    except:
                        context_sources = []
                
                return {
                    "answer": data.get("answer", ""),
                    "context": context,
                    "context_sources": context_sources,
                    "workflow_info": data.get("workflow_info", {}),
                    "api_time": api_time,
                    "success": True
                }
            else:
                logger.error(f"API error {response.status_code}")
                return {
                    "answer": "", "context": [], "context_sources": [],
                    "api_time": api_time, "success": False,
                    "error": f"HTTP {response.status_code}"
                }
        except requests.exceptions.Timeout:
            logger.error("Timeout en API")
            return {
                "answer": "", "context": [], "context_sources": [],
                "api_time": 90.0, "success": False, "error": "Timeout"
            }
        except Exception as e:
            logger.error(f"Error en API: {e}")
            return {
                "answer": "", "context": [], "context_sources": [],
                "api_time": 0.0, "success": False, "error": str(e)
            }
    
    def evaluate_single_question(self, question_data: Dict[str, Any]) -> EvaluationResult:
        """Evalúa una pregunta con faithfulness reactivado"""
        question = question_data["question"]
        ground_truth = question_data["ground_truth"]
        question_type = question_data["question_type"]
        
        logger.info(f"Evaluando '{question_type}': {question[:50]}...")
        
        api_response = self.query_rag_api(question)
        
        if not api_response["success"]:
            return EvaluationResult(
                question=question, answer="", ground_truth=ground_truth,
                context=[], context_sources=[], question_type=question_type,
                document_language="UNKNOWN",
                faithfulness_score=0.0, answer_relevancy_score=0.0,
                context_precision_score=0.0, context_recall_score=0.0,
                api_response_time=api_response["api_time"],
                evaluation_time=0.0, error=api_response.get("error")
            )
        
        # Detectar idioma del documento fuente
        doc_language = self._detect_document_language(api_response["context_sources"])
        
        ragas_data = {
            "question": [question],
            "answer": [api_response["answer"]],
            "ground_truth": [ground_truth],
            "contexts": [api_response["context"]]
        }
        
        try:
            eval_start = time.time()
            dataset = Dataset.from_dict(ragas_data)
            
            # ✅ Evaluar con faithfulness + manejo robusto
            try:
                result = evaluate(
                    dataset,
                    metrics=self.metrics,
                    llm=self.mistral_llm,
                    embeddings=self.ollama_embeddings,
                    show_progress=False
                )
                scores = result.scores[0] if hasattr(result, 'scores') and result.scores else {}
            except Exception as ragas_error:
                logger.warning(f"Error RAGAS: {ragas_error}")
                scores = {}
            
            eval_time = time.time() - eval_start
            
            # ✅ Extraer faithfulness con manejo de error
            faithfulness_score = 0.0
            faithfulness_error = None
            
            if 'faithfulness' in scores:
                try:
                    faithfulness_score = float(scores['faithfulness'])
                    if math.isnan(faithfulness_score):
                        faithfulness_score = 0.0
                        faithfulness_error = "NaN value"
                except (ValueError, TypeError) as e:
                    faithfulness_error = f"Parse error: {e}"
            else:
                faithfulness_error = "Metric not in results"
            
            return EvaluationResult(
                question=question,
                answer=api_response["answer"],
                ground_truth=ground_truth,
                context=api_response["context"],
                context_sources=api_response["context_sources"],
                question_type=question_type,
                document_language=doc_language,  # ✅ NUEVO
                faithfulness_score=faithfulness_score,  # ✅ REACTIVADO
                answer_relevancy_score=self._safe_float(scores.get("answer_relevancy", 0.0)),
                context_precision_score=self._safe_float(scores.get("context_precision", 0.0)),
                context_recall_score=self._safe_float(scores.get("context_recall", 0.0)),
                api_response_time=api_response["api_time"],
                evaluation_time=eval_time,
                faithfulness_error=faithfulness_error
            )
        except Exception as e:
            logger.error(f"Error evaluación: {e}")
            return EvaluationResult(
                question=question, answer=api_response["answer"],
                ground_truth=ground_truth, context=api_response["context"],
                context_sources=api_response["context_sources"],
                question_type=question_type, document_language=doc_language,
                faithfulness_score=0.0, answer_relevancy_score=0.0,
                context_precision_score=0.0, context_recall_score=0.0,
                api_response_time=api_response["api_time"],
                evaluation_time=0.0, error=str(e)
            )
    
    def _safe_float(self, value) -> float:
        """Convierte a float seguro"""
        try:
            val = float(value)
            return 0.0 if math.isnan(val) else val
        except:
            return 0.0
    
    def evaluate_batch(self, questions: List[Dict[str, Any]], batch_size: int = 3) -> List[EvaluationResult]:
        """Evalúa lote de preguntas"""
        results = []
        total = len(questions)
        
        logger.info(f"Evaluando {total} preguntas en lotes de {batch_size}")
        
        for i in range(0, total, batch_size):
            batch = questions[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            logger.info(f"Lote {batch_num}/{total_batches} ({len(batch)} preguntas)")
            
            for question_data in batch:
                try:
                    result = self.evaluate_single_question(question_data)
                    results.append(result)
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    error_result = EvaluationResult(
                        question=question_data["question"], answer="",
                        ground_truth=question_data["ground_truth"],
                        context=[], context_sources=[],
                        question_type=question_data["question_type"],
                        document_language="UNKNOWN",
                        faithfulness_score=0.0, answer_relevancy_score=0.0,
                        context_precision_score=0.0, context_recall_score=0.0,
                        api_response_time=0.0, evaluation_time=0.0, error=str(e)
                    )
                    results.append(error_result)
        
        return results
    
    def calculate_metrics_by_language(self) -> Dict[str, Dict[str, float]]:
        """✅ NUEVO: Calcula métricas por idioma del documento"""
        lang_metrics = {"ES": {}, "EN": {}, "MIXED": {}, "UNKNOWN": {}}
        
        for lang in lang_metrics:
            results_lang = [r for r in self.results if r.document_language == lang and not r.error]
            
            if results_lang:
                lang_metrics[lang] = {
                    "count": len(results_lang),
                    "faithfulness_avg": self._safe_avg([r.faithfulness_score for r in results_lang]),
                    "faithfulness_errors": len([r for r in results_lang if r.faithfulness_error]),
                    "answer_relevancy_avg": self._safe_avg([r.answer_relevancy_score for r in results_lang]),
                    "context_precision_avg": self._safe_avg([r.context_precision_score for r in results_lang]),
                    "context_recall_avg": self._safe_avg([r.context_recall_score for r in results_lang])
                }
        
        return lang_metrics
    
    def _safe_avg(self, values: List[float]) -> float:
        """Promedio seguro"""
        valid = [v for v in values if v is not None and not math.isnan(v)]
        return sum(valid) / len(valid) if valid else 0.0
    
    def generate_report(self) -> str:
        """Genera reporte con análisis por idioma"""
        if not self.results:
            return "No hay resultados"
        
        total = len(self.results)
        successful = len([r for r in self.results if not r.error])
        failed = total - successful
        
        lang_metrics = self.calculate_metrics_by_language()
        
        report = []
        report.append("="*80)
        report.append("REPORTE EVALUACIÓN RAGAS - FASE A")
        report.append("="*80)
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total preguntas: {total}")
        report.append(f"Exitosas: {successful} | Fallidas: {failed}")
        report.append("")
        
        # Métricas generales
        if successful > 0:
            valid = [r for r in self.results if not r.error]
            
            report.append("MÉTRICAS GENERALES")
            report.append("-"*40)
            report.append(f"Faithfulness: {self._safe_avg([r.faithfulness_score for r in valid]):.3f}")
            report.append(f"  Errores faithfulness: {len([r for r in valid if r.faithfulness_error])}/{len(valid)}")
            report.append(f"Answer Relevancy: {self._safe_avg([r.answer_relevancy_score for r in valid]):.3f}")
            report.append(f"Context Precision: {self._safe_avg([r.context_precision_score for r in valid]):.3f}")
            report.append(f"Context Recall: {self._safe_avg([r.context_recall_score for r in valid]):.3f}")
            report.append("")
        
        # ✅ Análisis por idioma
        report.append("ANÁLISIS POR IDIOMA DEL DOCUMENTO")
        report.append("-"*40)
        for lang, metrics in lang_metrics.items():
            if metrics.get("count", 0) > 0:
                report.append(f"\n{lang} ({metrics['count']} preguntas):")
                report.append(f"  Faithfulness: {metrics['faithfulness_avg']:.3f} (errores: {metrics.get('faithfulness_errors', 0)})")
                report.append(f"  Answer Relevancy: {metrics['answer_relevancy_avg']:.3f}")
                report.append(f"  Context Precision: {metrics['context_precision_avg']:.3f}")
                report.append(f"  Context Recall: {metrics['context_recall_avg']:.3f}")
        
        report.append("\n" + "="*80)
        return "\n".join(report)
    
    def export_results(self, output_dir: str = "evaluation_results"):
        """Exporta resultados con idioma de documento"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV
        csv_data = []
        for r in self.results:
            csv_data.append({
                "question": r.question,
                "answer": r.answer,
                "ground_truth": r.ground_truth,
                "question_type": r.question_type,
                "document_language": r.document_language,  # ✅ NUEVO
                "faithfulness_score": r.faithfulness_score,  # ✅ REACTIVADO
                "faithfulness_error": r.faithfulness_error or "",
                "answer_relevancy_score": r.answer_relevancy_score,
                "context_precision_score": r.context_precision_score,
                "context_recall_score": r.context_recall_score,
                "api_response_time": r.api_response_time,
                "evaluation_time": r.evaluation_time,
                "error": r.error or ""
            })
        
        df = pd.DataFrame(csv_data)
        csv_file = output_path / f"evaluation_results_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        logger.info(f"CSV: {csv_file}")
        
        # JSON
        json_data = {
            "evaluation_metadata": {
                "phase": "FASE A",
                "timestamp": timestamp,
                "total_questions": len(self.results),
                "successful_evaluations": len([r for r in self.results if not r.error])
            },
            "results": csv_data,
            "metrics_by_language": self.calculate_metrics_by_language()
        }
        
        json_file = output_path / f"evaluation_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=lambda x: None if isinstance(x, float) and (math.isnan(x) or math.isinf(x)) else x)
        logger.info(f"JSON: {json_file}")
        
        # Reporte
        report_file = output_path / f"evaluation_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        logger.info(f"Reporte: {report_file}")
    
    def run_evaluation(self, batch_size: int = 3):
        """Ejecuta evaluación FASE A"""
        logger.info("Iniciando evaluación FASE A")
        
        if not self.check_api_availability():
            logger.error("API no disponible")
            return
        
        try:
            dataset = self.load_dataset()
        except Exception as e:
            logger.error(f"Error cargando dataset: {e}")
            return
        
        logger.info("Ejecutando evaluación...")
        self.results = self.evaluate_batch(dataset, batch_size)
        
        logger.info("Generando reporte...")
        report = self.generate_report()
        print("\n" + report)
        
        logger.info("Exportando resultados...")
        self.export_results()
        
        logger.info("Evaluación completada")

def main():
    print("🚀 Evaluación RAGAS - FASE A")
    print("="*50)
    
    if not os.getenv("MISTRAL_API_KEY"):
        print("❌ MISTRAL_API_KEY no configurada")
        return
    
    evaluator = RAGEvaluator()
    
    try:
        evaluator.run_evaluation(batch_size=3)
    except KeyboardInterrupt:
        print("\n⏹️ Interrumpido")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()