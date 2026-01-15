#!/bin/bash
# Script para ver logs relacionados con fuentes y chunks

echo "🔍 Extrayendo logs del servicio RAG..."
screen -S rag-service -X hardcopy /tmp/rag_logs_full.txt

echo ""
echo "=========================================="
echo "LOGS DE FUENTES Y CHUNKS (últimas 100 líneas)"
echo "=========================================="
tail -100 /tmp/rag_logs_full.txt | grep -E "DEBUG|context_results|final_chunks|reranked_chunks|Fuentes|sources|after_reranking|Final chunks|Context results" | tail -50

echo ""
echo "=========================================="
echo "ESTADÍSTICAS DE CHUNKS"
echo "=========================================="
tail -200 /tmp/rag_logs_full.txt | grep -E "chunks|Chunks|📊|after_reranking|final_chunks" | tail -20

echo ""
echo "=========================================="
echo "ÚLTIMAS 30 LÍNEAS COMPLETAS"
echo "=========================================="
tail -30 /tmp/rag_logs_full.txt

