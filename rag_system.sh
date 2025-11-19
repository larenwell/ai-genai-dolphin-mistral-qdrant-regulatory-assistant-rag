#!/bin/bash

# Script Maestro Unificado del Asistente de Normativa
# Uso: ./rag_system.sh [comando] [opciones]

# Configuración
PROJECT_DIR="/root/ai-genai-rag-asistente-normativa-sincro"
DATALAYER_DIR="/root/chainlit-datalayer"
RAG_SERVICE_NAME="rag-service"
DATALAYER_SERVICE_NAME="datalayer-service"
HOST="0.0.0.0"
RAG_PORT="8000"
DATALAYER_PORT="5555"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCIONES DE VERIFICACIÓN DE SERVICIOS
# ============================================================================

check_qdrant() {
    if curl -s http://localhost:6333/collections >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_ollama() {
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_postgresql() {
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_localstack() {
    if curl -s http://localhost:4566 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_rag_service() {
    if screen -list | grep -q "$RAG_SERVICE_NAME"; then
        return 0
    else
        return 1
    fi
}

check_datalayer_service() {
    if screen -list | grep -q "$DATALAYER_SERVICE_NAME"; then
        return 0
    else
        return 1
    fi
}

check_datalayer_port() {
    if netstat -tlnp | grep -q ":$DATALAYER_PORT "; then
        return 0
    else
        return 1
    fi
}

check_docker_services() {
    if docker-compose -f "$DATALAYER_DIR/compose.yaml" ps | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# FUNCIONES DE INICIO DE SERVICIOS
# ============================================================================

start_qdrant() {
    echo -e "${BLUE}🔍 Iniciando Qdrant...${NC}"
    
    if check_qdrant; then
        echo -e "${GREEN}✅ Qdrant ya está ejecutándose en el puerto 6333${NC}"
        return 0
    fi
    
    # Verificar si hay un contenedor de Qdrant detenido que use el puerto 6333
    stopped_qdrant=$(docker ps -a --filter "publish=6333" --filter "ancestor=qdrant/qdrant" --format "{{.Names}}" | head -1)
    if [ -n "$stopped_qdrant" ]; then
        echo -e "${YELLOW}🔄 Reiniciando contenedor Qdrant detenido: $stopped_qdrant${NC}"
        docker start "$stopped_qdrant"
        echo "⏳ Esperando a que Qdrant esté listo..."
        for i in {1..30}; do
            if check_qdrant; then
                echo -e "${GREEN}✅ Qdrant reiniciado correctamente${NC}"
                return 0
            fi
            sleep 2
        done
    fi
    
    # Verificar si hay un contenedor Qdrant corriendo (aunque sea en otro puerto)
    running_qdrant=$(docker ps --filter "ancestor=qdrant/qdrant" --format "{{.Names}}" | head -1)
    if [ -n "$running_qdrant" ]; then
        echo -e "${YELLOW}⚠️  Hay un contenedor Qdrant corriendo: $running_qdrant${NC}"
        echo -e "${YELLOW}   Pero no está respondiendo en el puerto 6333${NC}"
        echo -e "${CYAN}   Verificando si podemos usar el puerto 6333...${NC}"
    fi
    
    # Crear nuevo contenedor si no existe uno con el nombre esperado
    if ! docker ps -a --format "{{.Names}}" | grep -q "^qdrant-rag$"; then
        echo -e "${BLUE}🚀 Creando nuevo contenedor Qdrant...${NC}"
        docker run -d \
            --name qdrant-rag \
            -p 6333:6333 \
            -p 6334:6334 \
            -v $(pwd)/qdrant_storage:/qdrant/storage \
            qdrant/qdrant:latest
    else
        # Si existe pero está detenido, iniciarlo
        if ! docker ps --format "{{.Names}}" | grep -q "^qdrant-rag$"; then
            echo -e "${BLUE}🔄 Reiniciando contenedor qdrant-rag...${NC}"
            docker start qdrant-rag
        fi
    fi
    
    echo "⏳ Esperando a que Qdrant esté listo..."
    for i in {1..30}; do
        if check_qdrant; then
            echo -e "${GREEN}✅ Qdrant iniciado correctamente${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ Error: Qdrant no se pudo iniciar${NC}"
    echo -e "${YELLOW}💡 Verifica los logs: docker logs qdrant-rag${NC}"
    return 1
}

start_ollama() {
    echo -e "${BLUE}🔍 Verificando Ollama...${NC}"
    
    if check_ollama; then
        echo -e "${GREEN}✅ Ollama ya está ejecutándose${NC}"
        return 0
    fi
    
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}❌ Error: Ollama no está instalado${NC}"
        return 1
    fi
    
    echo "🚀 Iniciando Ollama..."
    nohup ollama serve > /dev/null 2>&1 &
    
    echo "⏳ Esperando a que Ollama esté listo..."
    for i in {1..30}; do
        if check_ollama; then
            echo -e "${GREEN}✅ Ollama iniciado correctamente${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ Error: Ollama no se pudo iniciar${NC}"
    return 1
}

start_postgresql() {
    echo -e "${BLUE}🔍 Verificando PostgreSQL...${NC}"
    
    if check_postgresql; then
        echo -e "${GREEN}✅ PostgreSQL ya está ejecutándose${NC}"
        return 0
    fi
    
    # Verificar si hay un contenedor PostgreSQL detenido que use el puerto 5432
    stopped_postgres=$(docker ps -a --filter "publish=5432" --filter "ancestor=postgres" --format "{{.Names}}" | head -1)
    if [ -n "$stopped_postgres" ]; then
        echo -e "${YELLOW}🔄 Reiniciando contenedor PostgreSQL detenido: $stopped_postgres${NC}"
        docker start "$stopped_postgres"
        echo "⏳ Esperando a que PostgreSQL esté listo..."
        for i in {1..30}; do
            if check_postgresql; then
                echo -e "${GREEN}✅ PostgreSQL reiniciado correctamente${NC}"
                return 0
            fi
            sleep 2
        done
    fi
    
    # Verificar si hay un contenedor PostgreSQL corriendo
    running_postgres=$(docker ps --filter "ancestor=postgres" --format "{{.Names}}" | head -1)
    if [ -n "$running_postgres" ]; then
        echo -e "${YELLOW}⚠️  Hay un contenedor PostgreSQL corriendo: $running_postgres${NC}"
        echo -e "${YELLOW}   Pero no está respondiendo en el puerto 5432${NC}"
    fi
    
    # Crear nuevo contenedor si no existe uno con el nombre esperado
    if ! docker ps -a --format "{{.Names}}" | grep -q "^postgres-rag$"; then
        echo -e "${BLUE}🚀 Creando nuevo contenedor PostgreSQL...${NC}"
        docker run -d \
            --name postgres-rag \
            -e POSTGRES_PASSWORD=password \
            -e POSTGRES_DB=chainlit \
            -p 5432:5432 \
            postgres:16
    else
        # Si existe pero está detenido, iniciarlo
        if ! docker ps --format "{{.Names}}" | grep -q "^postgres-rag$"; then
            echo -e "${BLUE}🔄 Reiniciando contenedor postgres-rag...${NC}"
            docker start postgres-rag
        fi
    fi
    
    echo "⏳ Esperando a que PostgreSQL esté listo..."
    for i in {1..30}; do
        if check_postgresql; then
            echo -e "${GREEN}✅ PostgreSQL iniciado correctamente${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ Error: PostgreSQL no se pudo iniciar${NC}"
    echo -e "${YELLOW}💡 Verifica los logs: docker logs postgres-rag${NC}"
    return 1
}

start_localstack() {
    echo -e "${BLUE}🔍 Verificando LocalStack...${NC}"
    
    if check_localstack; then
        echo -e "${GREEN}✅ LocalStack ya está ejecutándose${NC}"
        return 0
    fi
    
    if docker ps | grep -q localstack; then
        echo -e "${GREEN}✅ LocalStack ya está ejecutándose en Docker${NC}"
        return 0
    fi
    
    docker run -d \
        --name localstack-rag \
        -p 4566:4566 \
        -e SERVICES=s3,lambda,iam,sts \
        localstack/localstack:latest
    
    echo "⏳ Esperando a que LocalStack esté listo..."
    for i in {1..30}; do
        if check_localstack; then
            echo -e "${GREEN}✅ LocalStack iniciado correctamente${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ Error: LocalStack no se pudo iniciar${NC}"
    return 1
}

start_docker_services() {
    echo -e "${BLUE}🐳 Iniciando servicios Docker del Datalayer...${NC}"
    
    cd "$DATALAYER_DIR"
    
    if check_docker_services; then
        echo -e "${YELLOW}⚠️  Los servicios Docker del Datalayer ya están ejecutándose${NC}"
        # Verificar que PostgreSQL esté disponible
        if ! check_postgresql; then
            echo -e "${YELLOW}⚠️  PostgreSQL del datalayer no responde, esperando...${NC}"
            sleep 5
        fi
        return 0
    fi
    
    # Verificar si hay un PostgreSQL externo corriendo en el puerto 5432
    if check_postgresql && ! docker ps --format "{{.Names}}" | grep -q "chainlit-datalayer-postgres"; then
        echo -e "${YELLOW}⚠️  Hay un PostgreSQL externo corriendo en el puerto 5432${NC}"
        echo -e "${CYAN}   Deteniendo PostgreSQL externo para usar el del datalayer...${NC}"
        docker stop postgres-rag 2>/dev/null || true
        sleep 2
    fi
    
    # Verificar si LocalStack ya está corriendo (para evitar conflicto de puerto)
    if check_localstack && ! docker ps --format "{{.Names}}" | grep -q "chainlit-datalayer-localstack"; then
        echo -e "${YELLOW}⚠️  Hay un LocalStack externo corriendo en el puerto 4566${NC}"
        echo -e "${CYAN}   Deteniendo LocalStack externo para usar el del datalayer...${NC}"
        docker stop localstack-rag 2>/dev/null || true
        sleep 2
    fi
    
    echo -e "${BLUE}🚀 Iniciando docker-compose del datalayer...${NC}"
    docker-compose up -d
    
    echo "⏳ Esperando a que los servicios Docker estén listos..."
    sleep 10
    
    if check_docker_services; then
        echo -e "${GREEN}✅ Servicios Docker del Datalayer iniciados correctamente${NC}"
        
        # Ejecutar migraciones de Prisma
        echo -e "${BLUE}📊 Ejecutando migraciones de Prisma...${NC}"
        export DATABASE_URL="postgresql://root:root@localhost:5432/postgres"
        if npx prisma migrate deploy >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Migraciones de Prisma aplicadas correctamente${NC}"
        else
            echo -e "${YELLOW}⚠️  Advertencia: No se pudieron aplicar las migraciones de Prisma${NC}"
            echo -e "${CYAN}   Puedes ejecutarlas manualmente: cd $DATALAYER_DIR && npx prisma migrate deploy${NC}"
        fi
        
        return 0
    else
        echo -e "${RED}❌ Error al iniciar servicios Docker del Datalayer${NC}"
        echo -e "${YELLOW}💡 Verifica los logs: cd $DATALAYER_DIR && docker-compose logs${NC}"
        return 1
    fi
}

start_rag_service() {
    echo -e "${BLUE}🔍 Iniciando servicio RAG...${NC}"
    
    if check_rag_service; then
        echo -e "${YELLOW}⚠️  El servicio RAG ya está ejecutándose${NC}"
        return 0
    fi
    
    # Validar dependencias críticas antes de iniciar
    echo -e "${BLUE}🔍 Validando dependencias críticas antes de iniciar RAG...${NC}"
    if ! validate_all_services; then
        echo -e "${RED}❌ Error: No se puede iniciar el servicio RAG sin las dependencias${NC}"
        echo -e "${YELLOW}💡 Asegúrate de que Qdrant, Ollama y PostgreSQL estén ejecutándose${NC}"
        return 1
    fi
    
    echo "🚀 Iniciando servicio RAG persistente..."
    echo "📁 Directorio: $PROJECT_DIR"
    echo "🌐 Host: $HOST"
    echo "🔌 Puerto: $RAG_PORT"
    echo "📺 Sesión: $RAG_SERVICE_NAME"
    
    cd "$PROJECT_DIR"
    
    screen -dmS "$RAG_SERVICE_NAME" bash -c "
        echo '🧠 Iniciando Asistente de Normativa...'
        echo '📊 Verificando dependencias...'
        uv run python -c 'import chainlit; print(\"✅ Chainlit disponible\")' || exit 1
        echo '🔍 Verificando conectividad con servicios...'
        echo '   • Qdrant: http://localhost:6333'
        echo '   • Ollama: http://localhost:11434'
        echo '   • PostgreSQL: localhost:5432'
        echo '🚀 Iniciando servicio en puerto $RAG_PORT...'
        uv run python -m chainlit run src/ui/app.py --host $HOST --port $RAG_PORT
    "
    
    sleep 5
    
    # Verificar que el servicio esté realmente funcionando
    if check_rag_service; then
        echo -e "${GREEN}✅ Servicio RAG iniciado exitosamente${NC}"
        
        # Verificar que el servicio responda en el puerto
        echo -e "${BLUE}🔍 Verificando que el servicio responda...${NC}"
        sleep 3
        if curl -s http://localhost:$RAG_PORT/ >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Servicio RAG respondiendo correctamente${NC}"
            echo "🌐 Disponible en: http://161.132.45.154:$RAG_PORT/"
        else
            echo -e "${YELLOW}⚠️  El servicio se inició pero aún no responde en el puerto${NC}"
            echo -e "${CYAN}💡 Esto es normal, puede tardar unos segundos más${NC}"
            echo "🌐 URL: http://161.132.45.154:$RAG_PORT/"
        fi
        return 0
    else
        echo -e "${RED}❌ Error al iniciar el servicio RAG${NC}"
        echo -e "${YELLOW}💡 Revisa los logs con: ./rag_system.sh logs rag${NC}"
        return 1
    fi
}

start_prisma_studio() {
    echo -e "${BLUE}🔍 Iniciando Prisma Studio...${NC}"
    
    if check_datalayer_service; then
        echo -e "${YELLOW}⚠️  Prisma Studio ya está ejecutándose${NC}"
        return 0
    fi
    
    if check_datalayer_port; then
        echo -e "${YELLOW}⚠️  El puerto $DATALAYER_PORT ya está en uso${NC}"
        return 0
    fi
    
    cd "$DATALAYER_DIR"
    
    export DATABASE_URL="postgresql://root:root@localhost:5432/postgres"
    
    screen -dmS "$DATALAYER_SERVICE_NAME" bash -c "
        echo '🔍 Iniciando Chainlit Datalayer...'
        echo '📊 Configurando base de datos...'
        export DATABASE_URL='postgresql://root:root@localhost:5432/postgres'
        echo '🚀 Iniciando Prisma Studio en puerto $DATALAYER_PORT...'
        echo '🌐 Disponible en: http://161.132.45.154:$DATALAYER_PORT/'
        npx prisma studio --port $DATALAYER_PORT --hostname 0.0.0.0
    "
    
    sleep 5
    
    if check_datalayer_service && check_datalayer_port; then
        echo -e "${GREEN}✅ Prisma Studio iniciado exitosamente${NC}"
        echo "🌐 Disponible en: http://161.132.45.154:$DATALAYER_PORT/"
        return 0
    else
        echo -e "${RED}❌ Error al iniciar Prisma Studio${NC}"
        return 1
    fi
}

# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

validate_all_services() {
    echo -e "${YELLOW}🔍 Validando que todos los servicios estén activos...${NC}"
    
    local all_ok=true
    local missing_services=()
    
    # Verificar servicios críticos para RAG
    if ! check_qdrant; then
        echo -e "${RED}  ❌ Qdrant no está disponible${NC}"
        all_ok=false
        missing_services+=("Qdrant")
    else
        echo -e "${GREEN}  ✅ Qdrant: Activo${NC}"
    fi
    
    if ! check_ollama; then
        echo -e "${RED}  ❌ Ollama no está disponible${NC}"
        all_ok=false
        missing_services+=("Ollama")
    else
        echo -e "${GREEN}  ✅ Ollama: Activo${NC}"
    fi
    
    if ! check_postgresql; then
        echo -e "${RED}  ❌ PostgreSQL no está disponible${NC}"
        all_ok=false
        missing_services+=("PostgreSQL")
    else
        echo -e "${GREEN}  ✅ PostgreSQL: Activo${NC}"
    fi
    
    # Verificar que los servicios respondan correctamente
    echo -e "${BLUE}  🔄 Verificando conectividad...${NC}"
    
    # Qdrant - verificar que responda correctamente
    if ! curl -s http://localhost:6333/collections | grep -q "result\|collections" 2>/dev/null; then
        echo -e "${YELLOW}  ⚠️  Qdrant responde pero puede no estar completamente listo${NC}"
    fi
    
    # Ollama - verificar que el modelo esté disponible
    if ! curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text" 2>/dev/null; then
        echo -e "${YELLOW}  ⚠️  Ollama responde pero el modelo 'nomic-embed-text' puede no estar disponible${NC}"
    fi
    
    if [ "$all_ok" = false ]; then
        echo ""
        echo -e "${RED}❌ ERROR: Los siguientes servicios no están disponibles:${NC}"
        for service in "${missing_services[@]}"; do
            echo -e "${RED}   • $service${NC}"
        done
        echo ""
        echo -e "${YELLOW}💡 Solución: Ejecuta los siguientes comandos:${NC}"
        for service in "${missing_services[@]}"; do
            case "$service" in
                "Qdrant") echo -e "${CYAN}   ./rag_system.sh start qdrant${NC}" ;;
                "Ollama") echo -e "${CYAN}   ./rag_system.sh start ollama${NC}" ;;
                "PostgreSQL") echo -e "${CYAN}   ./rag_system.sh start postgresql${NC}" ;;
            esac
        done
        return 1
    fi
    
    echo -e "${GREEN}✅ Todos los servicios críticos están activos${NC}"
    return 0
}

wait_for_services() {
    local max_attempts=30
    local attempt=1
    local include_postgresql=${1:-false}  # Por defecto no esperar PostgreSQL
    
    if [ "$include_postgresql" = "true" ]; then
        echo -e "${BLUE}⏳ Esperando a que todos los servicios estén completamente listos (incluyendo PostgreSQL)...${NC}"
    else
        echo -e "${BLUE}⏳ Esperando a que los servicios base estén completamente listos (Qdrant y Ollama)...${NC}"
    fi
    
    while [ $attempt -le $max_attempts ]; do
        local all_ready=true
        
        if ! check_qdrant; then
            all_ready=false
        fi
        
        if ! check_ollama; then
            all_ready=false
        fi
        
        # Solo verificar PostgreSQL si se solicita explícitamente
        if [ "$include_postgresql" = "true" ] && ! check_postgresql; then
            all_ready=false
        fi
        
        if [ "$all_ready" = true ]; then
            if [ "$include_postgresql" = "true" ]; then
                echo -e "${GREEN}✅ Todos los servicios están listos${NC}"
            else
                echo -e "${GREEN}✅ Servicios base (Qdrant y Ollama) están listos${NC}"
            fi
            return 0
        fi
        
        echo -e "${YELLOW}  Intento $attempt/$max_attempts...${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ Timeout: Los servicios no estuvieron listos a tiempo${NC}"
    return 1
}

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

start_all() {
    echo -e "${PURPLE}🚀 INICIANDO SISTEMA COMPLETO DEL ASISTENTE DE NORMATIVA${NC}"
    echo "=================================================================="
    echo -e "${CYAN}📋 Servicios a iniciar:${NC}"
    echo "   • Qdrant (Base de datos vectorial)"
    echo "   • Ollama (Modelo de embeddings)"
    echo "   • PostgreSQL (Base de datos relacional)"
    echo "   • LocalStack (Servicios AWS simulados)"
    echo "   • RAG Service (Asistente principal - Puerto 8000)"
    echo "   • Datalayer Service (Feedback - Puerto 5555)"
    echo "=================================================================="
    
    local errors=0
    
    echo -e "${YELLOW}📦 FASE 1: Servicios de infraestructura base${NC}"
    start_qdrant || ((errors++))
    start_ollama || ((errors++))
    # PostgreSQL y LocalStack se manejan en el docker-compose del datalayer
    # No los iniciamos aquí para evitar conflictos de puertos
    
    echo ""
    echo -e "${BLUE}⏳ Esperando a que los servicios base estén completamente listos...${NC}"
    # Solo esperar Qdrant y Ollama (PostgreSQL se inicia en FASE 2)
    wait_for_services false || {
        echo -e "${YELLOW}⚠️  Algunos servicios base pueden tardar más, continuando...${NC}"
        # No marcamos como error crítico, continuamos
    }
    
    echo ""
    echo -e "${YELLOW}📊 FASE 2: Servicios del datalayer (PostgreSQL + LocalStack)${NC}"
    start_docker_services || ((errors++))
    
    echo "⏳ Esperando a que PostgreSQL esté completamente listo..."
    # Esperar a que PostgreSQL responda
    for i in {1..15}; do
        if check_postgresql; then
            echo -e "${GREEN}✅ PostgreSQL del datalayer está listo${NC}"
            break
        fi
        sleep 2
    done
    
    echo ""
    echo -e "${YELLOW}🔍 FASE 2.5: Validación de servicios críticos${NC}"
    if ! validate_all_services; then
        echo -e "${RED}❌ Error: No se pueden iniciar los servicios principales sin las dependencias${NC}"
        ((errors++))
        echo ""
        echo -e "${YELLOW}💡 Intenta ejecutar: ./rag_system.sh start [servicio] para iniciar los servicios faltantes${NC}"
        echo "=================================================================="
        return 1
    fi
    
    echo ""
    echo -e "${YELLOW}🎯 FASE 3: Servicios principales${NC}"
    start_rag_service || ((errors++))
    start_prisma_studio || ((errors++))
    
    echo "=================================================================="
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✅ SISTEMA COMPLETO INICIADO CORRECTAMENTE${NC}"
        echo -e "${CYAN}🌐 URLs de acceso:${NC}"
        echo "   • Asistente RAG: http://161.132.45.154:$RAG_PORT/"
        echo "   • Feedback Datalayer: http://161.132.45.154:$DATALAYER_PORT/"
        echo "=================================================================="
    else
        echo -e "${RED}❌ Se encontraron $errors errores al iniciar el sistema${NC}"
        echo "💡 Revisa los logs para más detalles"
        echo "=================================================================="
    fi
}

stop_all() {
    echo -e "${PURPLE}🛑 DETENIENDO SISTEMA COMPLETO${NC}"
    echo "=================================================================="
    
    echo -e "${BLUE}🛑 Deteniendo servicios principales...${NC}"
    
    if check_rag_service; then
        screen -S "$RAG_SERVICE_NAME" -X quit
        echo -e "${GREEN}✅ Servicio RAG detenido${NC}"
    fi
    
    if check_datalayer_service; then
        screen -S "$DATALAYER_SERVICE_NAME" -X quit
        echo -e "${GREEN}✅ Prisma Studio detenido${NC}"
    fi
    
    echo -e "${BLUE}🐳 Deteniendo servicios Docker...${NC}"
    docker stop qdrant-rag postgres-rag localstack-rag 2>/dev/null || true
    docker rm qdrant-rag postgres-rag localstack-rag 2>/dev/null || true
    
    cd "$DATALAYER_DIR"
    docker-compose down 2>/dev/null || true
    
    pkill -f "ollama serve" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Todos los servicios detenidos${NC}"
    echo "=================================================================="
}

restart_all() {
    echo -e "${PURPLE}🔄 REINICIANDO SISTEMA COMPLETO${NC}"
    stop_all
    sleep 5
    start_all
}

status_all() {
    echo -e "${PURPLE}📊 ESTADO DEL SISTEMA COMPLETO${NC}"
    echo "=================================================================="
    
    echo -e "${CYAN}🔧 Servicios de Infraestructura:${NC}"
    if check_qdrant; then
        echo -e "${GREEN}  ✅ Qdrant: Activo${NC}"
    else
        echo -e "${RED}  ❌ Qdrant: Inactivo${NC}"
    fi
    
    if check_ollama; then
        echo -e "${GREEN}  ✅ Ollama: Activo${NC}"
    else
        echo -e "${RED}  ❌ Ollama: Inactivo${NC}"
    fi
    
    if check_postgresql; then
        echo -e "${GREEN}  ✅ PostgreSQL: Activo${NC}"
    else
        echo -e "${RED}  ❌ PostgreSQL: Inactivo${NC}"
    fi
    
    if check_localstack; then
        echo -e "${GREEN}  ✅ LocalStack: Activo${NC}"
    else
        echo -e "${RED}  ❌ LocalStack: Inactivo${NC}"
    fi
    
    echo -e "${CYAN}🎯 Servicios Principales:${NC}"
    if check_rag_service; then
        echo -e "${GREEN}  ✅ RAG Service: Activo${NC}"
        echo -e "${CYAN}     🌐 URL: http://161.132.45.154:$RAG_PORT/${NC}"
    else
        echo -e "${RED}  ❌ RAG Service: Inactivo${NC}"
    fi
    
    if check_datalayer_service; then
        echo -e "${GREEN}  ✅ Datalayer Service: Activo${NC}"
        echo -e "${CYAN}     🌐 URL: http://161.132.45.154:$DATALAYER_PORT/${NC}"
    else
        echo -e "${RED}  ❌ Datalayer Service: Inactivo${NC}"
    fi
    
    echo "=================================================================="
}

check_system() {
    echo -e "${PURPLE}🔍 VERIFICACIÓN COMPLETA DEL SISTEMA${NC}"
    echo "================================================================"
    
    echo -e "${BLUE}📁 Directorio actual:${NC}"
    pwd
    echo ""
    
    echo -e "${BLUE}🔌 Puertos en uso:${NC}"
    netstat -tlnp | grep -E ":(8000|5555|6333|11434|5432|4566)" | while read line; do
        port=$(echo $line | awk '{print $4}' | cut -d: -f2)
        if [[ "$port" =~ ^(8000|5555|6333|11434|5432|4566)$ ]]; then
            echo -e "  ${GREEN}✅ Puerto $port: Activo${NC}"
        fi
    done
    echo ""
    
    echo -e "${BLUE}⚙️ Procesos activos:${NC}"
    processes=("chainlit" "prisma" "ollama" "qdrant")
    for proc in "${processes[@]}"; do
        if ps aux | grep -q "$proc" | grep -v grep; then
            echo -e "  ${GREEN}✅ $proc: Activo${NC}"
        else
            echo -e "  ${RED}❌ $proc: Inactivo${NC}"
        fi
    done
    echo ""
    
    echo -e "${BLUE}🐳 Contenedores Docker:${NC}"
    if docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep -q "Up"; then
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep "Up"
    else
        echo -e "  ${YELLOW}⚠️ No hay contenedores Docker activos${NC}"
    fi
    echo ""
    
    echo -e "${BLUE}📺 Sesiones screen:${NC}"
    if screen -list 2>/dev/null | grep -q "rag-service\|datalayer-service"; then
        screen -list | grep -E "(rag-service|datalayer-service)"
    else
        echo -e "  ${YELLOW}⚠️ No hay sesiones screen activas${NC}"
    fi
    echo ""
    
    echo -e "${BLUE}🌐 Conectividad de servicios:${NC}"
    
    if curl -s http://localhost:8000/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ RAG Service (8000): Respondiendo${NC}"
    else
        echo -e "  ${RED}❌ RAG Service (8000): No responde${NC}"
    fi
    
    if curl -s http://localhost:5555/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Datalayer (5555): Respondiendo${NC}"
    else
        echo -e "  ${RED}❌ Datalayer (5555): No responde${NC}"
    fi
    
    if curl -s http://localhost:6333/collections >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Qdrant (6333): Respondiendo${NC}"
    else
        echo -e "  ${RED}❌ Qdrant (6333): No responde${NC}"
    fi
    
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Ollama (11434): Respondiendo${NC}"
    else
        echo -e "  ${RED}❌ Ollama (11434): No responde${NC}"
    fi
    
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ PostgreSQL (5432): Respondiendo${NC}"
    else
        echo -e "  ${RED}❌ PostgreSQL (5432): No responde${NC}"
    fi
    
    if curl -s http://localhost:4566 >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ LocalStack (4566): Respondiendo${NC}"
    else
        echo -e "  ${RED}❌ LocalStack (4566): No responde${NC}"
    fi
    
    echo ""
    
    echo -e "${CYAN}🌐 URLs de acceso:${NC}"
    echo "  • Asistente RAG: http://161.132.45.154:8000/"
    echo "  • Feedback: http://161.132.45.154:5555/"
    echo "  • Qdrant Dashboard: http://161.132.45.154:6333/dashboard"
    echo ""
    
    echo -e "${YELLOW}🛠️ Comandos de acción:${NC}"
    echo "  • Iniciar todo: ./rag_system.sh start"
    echo "  • Ver estado: ./rag_system.sh status"
    echo "  • Reiniciar: ./rag_system.sh restart"
    echo "  • Emergencia: ./rag_system.sh emergency"
    echo ""
    
    echo "================================================================"
    echo -e "${PURPLE}✅ Verificación completada${NC}"
}

monitor_system() {
    local interval=${1:-30}
    
    echo -e "${PURPLE}🔍 MONITOR DE SERVICIOS DEL ASISTENTE DE NORMATIVA${NC}"
    echo "=================================================="
    echo -e "${CYAN}⏰ Intervalo de verificación: ${interval} segundos${NC}"
    echo "💡 Presiona Ctrl+C para salir"
    echo ""
    
    while true; do
        clear
        echo -e "${PURPLE}🔍 MONITOR DE SERVICIOS - $(date)${NC}"
        echo "=================================================="
        
        if check_qdrant; then
            echo -e "${GREEN}✅ Qdrant: Activo${NC}"
        else
            echo -e "${RED}❌ Qdrant: Inactivo${NC}"
        fi
        
        if check_ollama; then
            echo -e "${GREEN}✅ Ollama: Activo${NC}"
        else
            echo -e "${RED}❌ Ollama: Inactivo${NC}"
        fi
        
        if check_postgresql; then
            echo -e "${GREEN}✅ PostgreSQL: Activo${NC}"
        else
            echo -e "${RED}❌ PostgreSQL: Inactivo${NC}"
        fi
        
        if check_localstack; then
            echo -e "${GREEN}✅ LocalStack: Activo${NC}"
        else
            echo -e "${RED}❌ LocalStack: Inactivo${NC}"
        fi
        
        if check_rag_service; then
            echo -e "${GREEN}✅ RAG Service: Activo${NC}"
            echo -e "${CYAN}🌐 URL: http://161.132.45.154:8000/${NC}"
        else
            echo -e "${RED}❌ RAG Service: Inactivo${NC}"
        fi
        
        if check_datalayer_service; then
            echo -e "${GREEN}✅ Datalayer Service: Activo${NC}"
            echo -e "${CYAN}🌐 URL: http://161.132.45.154:5555/${NC}"
        else
            echo -e "${RED}❌ Datalayer Service: Inactivo${NC}"
        fi
        
        echo "=================================================="
        echo -e "${CYAN}⏳ Próxima verificación en ${interval} segundos...${NC}"
        echo "💡 Presiona Ctrl+C para salir"
        
        sleep $interval
    done
}

emergency_restart() {
    echo -e "${PURPLE}🚨 REINICIO DE EMERGENCIA DEL ASISTENTE DE NORMATIVA${NC}"
    echo "=================================================="
    echo ""
    
    echo -e "${BLUE}🛑 Deteniendo todos los servicios...${NC}"
    stop_all
    
    echo -e "${BLUE}⏳ Esperando 5 segundos...${NC}"
    sleep 5
    
    echo -e "${BLUE}🧹 Limpiando procesos huérfanos...${NC}"
    pkill -f "ollama serve" 2>/dev/null || true
    pkill -f "chainlit" 2>/dev/null || true
    pkill -f "prisma" 2>/dev/null || true
    
    echo -e "${BLUE}🐳 Limpiando contenedores Docker...${NC}"
    docker stop $(docker ps -q) 2>/dev/null || true
    docker rm $(docker ps -aq) 2>/dev/null || true
    
    echo -e "${BLUE}⏳ Esperando 3 segundos más...${NC}"
    sleep 3
    
    echo -e "${BLUE}🚀 Iniciando todos los servicios...${NC}"
    start_all
    
    echo ""
    echo -e "${GREEN}✅ Reinicio de emergencia completado${NC}"
    echo -e "${CYAN}🌐 Asistente disponible en: http://161.132.45.154:8000/${NC}"
}

logs_rag() {
    if check_rag_service; then
        echo -e "${BLUE}📋 Mostrando logs del servicio RAG...${NC}"
        echo "💡 Presiona Ctrl+A, luego D para salir de la sesión"
        sleep 2
        screen -r "$RAG_SERVICE_NAME"
    else
        echo -e "${RED}❌ El servicio RAG no está ejecutándose${NC}"
    fi
}

logs_datalayer() {
    if check_datalayer_service; then
        echo -e "${BLUE}📋 Mostrando logs del Datalayer...${NC}"
        echo "💡 Presiona Ctrl+A, luego D para salir de la sesión"
        sleep 2
        screen -r "$DATALAYER_SERVICE_NAME"
    else
        echo -e "${RED}❌ El servicio Datalayer no está ejecutándose${NC}"
    fi
}

# ============================================================================
# FUNCIÓN DE AYUDA
# ============================================================================

help() {
    echo -e "${PURPLE}🤖 SCRIPT MAESTRO UNIFICADO DEL ASISTENTE DE NORMATIVA${NC}"
    echo "=================================================================="
    echo ""
    echo "Uso: $0 [comando] [opciones]"
    echo ""
    echo -e "${YELLOW}Comandos principales:${NC}"
    echo "  start     - Iniciar TODO el sistema (recomendado)"
    echo "  stop      - Detener TODO el sistema"
    echo "  restart   - Reiniciar TODO el sistema"
    echo "  status    - Ver estado de TODO el sistema"
    echo "  check     - Verificación completa del sistema"
    echo "  validate  - Validar que todos los servicios críticos estén activos"
    echo "  monitor   - Monitoreo continuo (opcional: intervalo en segundos)"
    echo "  emergency - Reinicio de emergencia"
    echo "  logs      - Ver logs (especificar servicio)"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo -e "${YELLOW}Servicios individuales:${NC}"
    echo "  start qdrant     - Solo Qdrant"
    echo "  start ollama     - Solo Ollama"
    echo "  start postgresql - Solo PostgreSQL"
    echo "  start localstack - Solo LocalStack"
    echo "  start rag        - Solo RAG Service"
    echo "  start datalayer  - Solo Datalayer Service"
    echo ""
    echo -e "${YELLOW}Ver logs específicos:${NC}"
    echo "  logs rag        - Logs del RAG Service"
    echo "  logs datalayer  - Logs del Datalayer"
    echo ""
    echo -e "${YELLOW}Ejemplos:${NC}"
    echo "  $0 start                    # Iniciar todo el sistema"
    echo "  $0 status                   # Ver estado completo"
    echo "  $0 check                    # Verificación completa"
    echo "  $0 monitor 60               # Monitorear cada minuto"
    echo "  $0 logs rag                # Ver logs del RAG"
    echo "  $0 start qdrant            # Solo Qdrant"
    echo ""
    echo -e "${CYAN}URLs del sistema:${NC}"
    echo "  • Asistente RAG: http://161.132.45.154:$RAG_PORT/"
    echo "  • Feedback: http://161.132.45.154:$DATALAYER_PORT/"
    echo ""
}

# ============================================================================
# PROCESAR ARGUMENTOS
# ============================================================================

case "${1:-start}" in
    start)
        if [ -n "$2" ]; then
            case "$2" in
                qdrant) start_qdrant ;;
                ollama) start_ollama ;;
                postgresql) start_postgresql ;;
                localstack) start_localstack ;;
                rag) 
                    echo -e "${YELLOW}🔍 Validando dependencias antes de iniciar RAG...${NC}"
                    if validate_all_services; then
                        start_rag_service
                    else
                        echo -e "${RED}❌ No se puede iniciar RAG sin las dependencias${NC}"
                        exit 1
                    fi
                    ;;
                datalayer) 
                    start_docker_services
                    sleep 3
                    start_prisma_studio
                    ;;
                *) echo -e "${RED}❌ Servicio desconocido: $2${NC}"; help; exit 1 ;;
            esac
        else
            start_all
        fi
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status_all
        ;;
    check)
        check_system
        ;;
    validate)
        validate_all_services
        ;;
    monitor)
        monitor_system $2
        ;;
    emergency)
        emergency_restart
        ;;
    logs)
        if [ -n "$2" ]; then
            case "$2" in
                rag) logs_rag ;;
                datalayer) logs_datalayer ;;
                *) echo -e "${RED}❌ Servicio de logs desconocido: $2${NC}"; help; exit 1 ;;
            esac
        else
            echo -e "${YELLOW}💡 Especifica el servicio: logs rag o logs datalayer${NC}"
        fi
        ;;
    help|--help|-h)
        help
        ;;
    *)
        echo -e "${RED}❌ Comando desconocido: $1${NC}"
        help
        exit 1
        ;;
esac
