#!/bin/bash

# Script para iniciar el servicio RAG de forma persistente
# Uso: ./start_rag_service.sh

# Configuración
PROJECT_DIR="/root/ai-genai-rag-asistente-normativa-sincro"
SERVICE_NAME="rag-service"
HOST="0.0.0.0"
PORT="8000"

# Función para verificar si el servicio ya está ejecutándose
check_service() {
    if screen -list | grep -q "$SERVICE_NAME"; then
        echo "⚠️  El servicio $SERVICE_NAME ya está ejecutándose"
        echo "📋 Sesiones activas:"
        screen -list | grep "$SERVICE_NAME"
        return 0
    else
        return 1
    fi
}

# Función para detener el servicio
stop_service() {
    if check_service; then
        echo "🛑 Deteniendo servicio $SERVICE_NAME..."
        screen -S "$SERVICE_NAME" -X quit
        sleep 2
        echo "✅ Servicio detenido"
    else
        echo "ℹ️  El servicio no está ejecutándose"
    fi
}

# Función para iniciar el servicio
start_service() {
    if check_service; then
        echo "ℹ️  El servicio ya está ejecutándose. Usa 'restart' para reiniciarlo."
        return 0
    fi
    
    echo "🚀 Iniciando servicio RAG persistente..."
    echo "📁 Directorio: $PROJECT_DIR"
    echo "🌐 Host: $HOST"
    echo "🔌 Puerto: $PORT"
    echo "📺 Sesión: $SERVICE_NAME"
    
    # Cambiar al directorio del proyecto
    cd "$PROJECT_DIR"
    
    # Crear sesión screen y ejecutar el servicio
    screen -dmS "$SERVICE_NAME" bash -c "
        echo '🧠 Iniciando Asistente de Normativa...'
        echo '📊 Verificando dependencias...'
        uv run python -c 'import chainlit; print(\"✅ Chainlit disponible\")'
        echo '🚀 Iniciando servicio en puerto $PORT...'
        uv run python -m chainlit run src/frontend_rag.py --host $HOST --port $PORT
    "
    
    # Esperar un momento para que se inicie
    sleep 3
    
    # Verificar que se inició correctamente
    if check_service; then
        echo "✅ Servicio iniciado exitosamente"
        echo "🌐 Disponible en: http://161.132.45.154:$PORT/"
        echo "📺 Para ver logs: screen -r $SERVICE_NAME"
        echo "🛑 Para detener: screen -S $SERVICE_NAME -X quit"
    else
        echo "❌ Error al iniciar el servicio"
        return 1
    fi
}

# Función para mostrar estado
status() {
    if check_service; then
        echo "✅ Servicio $SERVICE_NAME está ejecutándose"
        echo "🌐 URL: http://161.132.45.154:$PORT/"
        echo "📊 Procesos:"
        ps aux | grep chainlit | grep -v grep
    else
        echo "❌ Servicio $SERVICE_NAME no está ejecutándose"
    fi
}

# Función para mostrar logs
logs() {
    if check_service; then
        echo "📋 Mostrando logs del servicio $SERVICE_NAME..."
        echo "💡 Presiona Ctrl+A, luego D para salir de la sesión"
        sleep 2
        screen -r "$SERVICE_NAME"
    else
        echo "❌ El servicio no está ejecutándose"
    fi
}

# Función para reiniciar
restart() {
    echo "🔄 Reiniciando servicio $SERVICE_NAME..."
    stop_service
    sleep 2
    start_service
}

# Función de ayuda
help() {
    echo "🤖 Script de Gestión del Servicio RAG"
    echo "======================================"
    echo ""
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  start     - Iniciar el servicio"
    echo "  stop      - Detener el servicio"
    echo "  restart   - Reiniciar el servicio"
    echo "  status    - Mostrar estado del servicio"
    echo "  logs      - Mostrar logs en tiempo real"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 logs"
}

# Procesar argumentos
case "${1:-start}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    help|--help|-h)
        help
        ;;
    *)
        echo "❌ Comando desconocido: $1"
        help
        exit 1
        ;;
esac
