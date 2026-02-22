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

# IPs permitidas para acceso al puerto 8000 (RAG Service)
ALLOWED_IPS=(
    "209.45.68.70"
    "161.132.3.56"
    "161.132.3.57"
    "161.132.3.58"
    "161.132.3.59"
)

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

check_firewall_rules() {
    # Verificar si existen reglas de iptables para el puerto 8000
    if iptables -L INPUT -n 2>/dev/null | grep -q ":$RAG_PORT"; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# FUNCIONES DE FIREWALL
# ============================================================================

configure_firewall() {
    echo -e "${BLUE}🔥 Configurando firewall para puerto $RAG_PORT...${NC}"
    
    # Verificar si el usuario tiene permisos de root o sudo
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}⚠️  Se requieren permisos de root para configurar firewall${NC}"
        echo -e "${CYAN}💡 Intentando con sudo...${NC}"
        SUDO_CMD="sudo"
    else
        SUDO_CMD=""
    fi
    
    # Primero, eliminar reglas existentes para el puerto 8000 (si existen)
    echo -e "${BLUE}🧹 Limpiando reglas existentes para puerto $RAG_PORT...${NC}"
    $SUDO_CMD iptables -D INPUT -p tcp --dport $RAG_PORT -j DROP 2>/dev/null || true
    
    # Eliminar reglas de IPs permitidas existentes
    for ip in "${ALLOWED_IPS[@]}"; do
        $SUDO_CMD iptables -D INPUT -p tcp -s "$ip" --dport $RAG_PORT -j ACCEPT 2>/dev/null || true
    done
    
    # Agregar reglas para permitir solo las IPs especificadas
    echo -e "${BLUE}✅ Agregando reglas para IPs permitidas...${NC}"
    for ip in "${ALLOWED_IPS[@]}"; do
        $SUDO_CMD iptables -I INPUT -p tcp -s "$ip" --dport $RAG_PORT -j ACCEPT
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ IP permitida: $ip${NC}"
        else
            echo -e "${RED}  ❌ Error al agregar regla para IP: $ip${NC}"
            return 1
        fi
    done
    
    # Bloquear todas las demás conexiones al puerto 8000
    echo -e "${BLUE}🔒 Bloqueando acceso desde otras IPs al puerto $RAG_PORT...${NC}"
    $SUDO_CMD iptables -A INPUT -p tcp --dport $RAG_PORT -j DROP
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Regla de bloqueo agregada${NC}"
    else
        echo -e "${RED}❌ Error al agregar regla de bloqueo${NC}"
        return 1
    fi
    
    # Guardar reglas de iptables de forma persistente
    echo -e "${BLUE}💾 Guardando reglas de firewall de forma persistente...${NC}"
    
    # Intentar guardar con netfilter-persistent (método preferido)
    if command -v netfilter-persistent &> /dev/null; then
        if $SUDO_CMD netfilter-persistent save >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Reglas guardadas con netfilter-persistent (persistentes después de reinicio)${NC}"
        else
            echo -e "${YELLOW}⚠️  No se pudo guardar con netfilter-persistent, intentando método alternativo...${NC}"
            save_firewall_rules_manual
        fi
    # Método alternativo: guardar manualmente en /etc/iptables/rules.v4
    elif command -v iptables-save &> /dev/null; then
        save_firewall_rules_manual
    else
        echo -e "${RED}❌ Error: No se encontró iptables-save${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Firewall configurado correctamente y guardado de forma persistente${NC}"
    return 0
}

save_firewall_rules_manual() {
    # Crear directorio si no existe
    $SUDO_CMD mkdir -p /etc/iptables 2>/dev/null || true
    
    # Guardar todas las reglas de iptables
    if $SUDO_CMD iptables-save > /tmp/iptables_rules_backup.txt 2>/dev/null; then
        if $SUDO_CMD cp /tmp/iptables_rules_backup.txt /etc/iptables/rules.v4 2>/dev/null; then
            echo -e "${GREEN}✅ Reglas guardadas en /etc/iptables/rules.v4${NC}"
            
            # Crear script de inicio para restaurar reglas al arrancar
            create_firewall_restore_script
            
            # Limpiar archivo temporal
            rm -f /tmp/iptables_rules_backup.txt 2>/dev/null || true
            
            return 0
        else
            echo -e "${YELLOW}⚠️  No se pudo guardar en /etc/iptables/rules.v4 (puede requerir permisos)${NC}"
            echo -e "${CYAN}💡 Las reglas están activas pero no serán persistentes después de reiniciar${NC}"
            rm -f /tmp/iptables_rules_backup.txt 2>/dev/null || true
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  No se pudo guardar las reglas${NC}"
        return 1
    fi
}

create_firewall_restore_script() {
    # Crear script systemd para restaurar reglas al arrancar
    local script_path="/etc/systemd/system/rag-firewall-restore.service"
    
    # Verificar si ya existe y está habilitado
    if [ -f "$script_path" ]; then
        if $SUDO_CMD systemctl is-enabled rag-firewall-restore.service >/dev/null 2>&1; then
            echo -e "${CYAN}ℹ️  Servicio de restauración ya existe y está habilitado${NC}"
            return 0
        fi
    fi
    
    # Crear servicio systemd para restaurar reglas al arrancar
    $SUDO_CMD tee "$script_path" > /dev/null <<EOF
[Unit]
Description=Restore RAG Firewall Rules for Port 8000
After=network.target
Before=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'if [ -f /etc/iptables/rules.v4 ]; then iptables-restore < /etc/iptables/rules.v4; fi'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    if [ $? -eq 0 ]; then
        # Habilitar el servicio
        $SUDO_CMD systemctl daemon-reload 2>/dev/null || true
        $SUDO_CMD systemctl enable rag-firewall-restore.service 2>/dev/null || true
        echo -e "${GREEN}✅ Servicio de restauración de firewall creado y habilitado${NC}"
        echo -e "${CYAN}💡 Las reglas se restaurarán automáticamente al reiniciar el sistema${NC}"
    else
        echo -e "${YELLOW}⚠️  No se pudo crear el servicio de restauración${NC}"
        echo -e "${CYAN}💡 Puedes restaurar manualmente con: iptables-restore < /etc/iptables/rules.v4${NC}"
    fi
}

restore_firewall_rules() {
    echo -e "${BLUE}🔄 Verificando y restaurando reglas de firewall...${NC}"
    
    # Verificar si las reglas ya están presentes
    if check_firewall_rules; then
        echo -e "${GREEN}✅ Las reglas de firewall ya están activas${NC}"
        return 0
    fi
    
    # Verificar si existe archivo de reglas guardadas
    if [ -f "/etc/iptables/rules.v4" ]; then
        echo -e "${BLUE}📂 Restaurando reglas desde /etc/iptables/rules.v4...${NC}"
        
        # Verificar si el usuario tiene permisos de root o sudo
        if [ "$EUID" -ne 0 ]; then
            SUDO_CMD="sudo"
        else
            SUDO_CMD=""
        fi
        
        if $SUDO_CMD iptables-restore < /etc/iptables/rules.v4 2>/dev/null; then
            echo -e "${GREEN}✅ Reglas de firewall restauradas correctamente${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  No se pudieron restaurar las reglas desde el archivo guardado${NC}"
            echo -e "${CYAN}💡 Reconfigurando firewall...${NC}"
            configure_firewall
            return $?
        fi
    else
        echo -e "${YELLOW}⚠️  No se encontró archivo de reglas guardadas${NC}"
        echo -e "${CYAN}💡 Configurando firewall por primera vez...${NC}"
        configure_firewall
        return $?
    fi
}

remove_firewall_rules() {
    echo -e "${BLUE}🧹 Eliminando reglas de firewall para puerto $RAG_PORT...${NC}"
    
    # Verificar si el usuario tiene permisos de root o sudo
    if [ "$EUID" -ne 0 ]; then
        SUDO_CMD="sudo"
    else
        SUDO_CMD=""
    fi
    
    # Eliminar regla de bloqueo
    $SUDO_CMD iptables -D INPUT -p tcp --dport $RAG_PORT -j DROP 2>/dev/null || true
    
    # Eliminar reglas de IPs permitidas
    for ip in "${ALLOWED_IPS[@]}"; do
        $SUDO_CMD iptables -D INPUT -p tcp -s "$ip" --dport $RAG_PORT -j ACCEPT 2>/dev/null || true
    done
    
    # Actualizar reglas guardadas
    if command -v netfilter-persistent &> /dev/null; then
        $SUDO_CMD netfilter-persistent save 2>/dev/null || true
    elif [ -f /etc/iptables/rules.v4 ]; then
        $SUDO_CMD iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Reglas de firewall eliminadas${NC}"
    return 0
}

show_firewall_status() {
    echo -e "${BLUE}🔥 Estado del firewall para puerto $RAG_PORT:${NC}"
    
    if check_firewall_rules; then
        echo -e "${GREEN}✅ Reglas de firewall activas${NC}"
        echo ""
        echo -e "${CYAN}IPs permitidas:${NC}"
        for ip in "${ALLOWED_IPS[@]}"; do
            if iptables -L INPUT -n 2>/dev/null | grep -q "$ip.*$RAG_PORT"; then
                echo -e "${GREEN}  ✅ $ip${NC}"
            else
                echo -e "${RED}  ❌ $ip (regla no encontrada)${NC}"
            fi
        done
        echo ""
        echo -e "${CYAN}Reglas de iptables para puerto $RAG_PORT:${NC}"
        iptables -L INPUT -n 2>/dev/null | grep -A 10 ":$RAG_PORT" || echo -e "${YELLOW}  No se encontraron reglas${NC}"
    else
        echo -e "${RED}❌ No hay reglas de firewall configuradas${NC}"
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
    
    # Verificar si el contenedor qdrant-rag existe y validar su volumen
    # IMPORTANTE: Usar ruta absoluta para evitar problemas con cambios de directorio
    PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
    expected_volume="${PROJECT_DIR}/qdrant_storage"
    
    # Asegurar que el directorio existe
    mkdir -p "$expected_volume"
    
    if docker ps -a --format "{{.Names}}" | grep -q "^qdrant-rag$"; then
        # Verificar el volumen montado
        current_volume=$(docker inspect qdrant-rag 2>/dev/null | grep -A 5 '"Mounts"' | grep '"Source"' | head -1 | sed 's/.*"Source": "\([^"]*\)".*/\1/')
        
        # Normalizar rutas para comparación (resolver rutas relativas y symlinks)
        current_volume=$(readlink -f "$current_volume" 2>/dev/null || echo "$current_volume")
        expected_volume=$(readlink -f "$expected_volume" 2>/dev/null || echo "$expected_volume")
        
        if [ -n "$current_volume" ] && [ "$current_volume" != "$expected_volume" ]; then
            echo -e "${YELLOW}⚠️  El contenedor qdrant-rag tiene un volumen incorrecto${NC}"
            echo -e "${CYAN}   Volumen actual: $current_volume${NC}"
            echo -e "${CYAN}   Volumen esperado: $expected_volume${NC}"
            echo -e "${RED}⚠️  ADVERTENCIA: Esto puede causar pérdida de datos${NC}"
            echo -e "${BLUE}🔄 Recreando contenedor con el volumen correcto...${NC}"
            
            # Detener y eliminar el contenedor con volumen incorrecto
            docker stop qdrant-rag 2>/dev/null || true
            docker rm qdrant-rag 2>/dev/null || true
        fi
    fi
    
    # Crear nuevo contenedor si no existe uno con el nombre esperado
    if ! docker ps -a --format "{{.Names}}" | grep -q "^qdrant-rag$"; then
        echo -e "${BLUE}🚀 Creando nuevo contenedor Qdrant...${NC}"
        echo -e "${CYAN}   Volumen: $expected_volume${NC}"
        docker run -d \
            --name qdrant-rag \
            -p 6333:6333 \
            -p 6334:6334 \
            -v "${expected_volume}:/qdrant/storage" \
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
        
        # Verificar y restaurar reglas de firewall si es necesario
        if ! check_firewall_rules; then
            echo -e "${YELLOW}⚠️  Reglas de firewall no encontradas, restaurando...${NC}"
            restore_firewall_rules || true
        fi
        return 0
    fi
    
    # Validar dependencias críticas antes de iniciar
    echo -e "${BLUE}🔍 Validando dependencias críticas antes de iniciar RAG...${NC}"
    if ! validate_all_services; then
        echo -e "${RED}❌ Error: No se puede iniciar el servicio RAG sin las dependencias${NC}"
        echo -e "${YELLOW}💡 Asegúrate de que Qdrant, Ollama y PostgreSQL estén ejecutándose${NC}"
        return 1
    fi
    
    # Verificar y restaurar/configurar firewall para permitir solo IPs autorizadas
    echo ""
    echo -e "${BLUE}🔥 Verificando y restaurando firewall (automático y persistente)...${NC}"
    if ! restore_firewall_rules; then
        echo -e "${YELLOW}⚠️  Advertencia: No se pudo configurar/restaurar el firewall${NC}"
        echo -e "${CYAN}💡 El servicio se iniciará, pero el firewall puede no estar configurado${NC}"
        echo -e "${CYAN}💡 Verifica los permisos de root/sudo para configurar iptables${NC}"
        echo -e "${CYAN}💡 Puedes configurarlo manualmente con: ./rag_system.sh firewall configure${NC}"
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
    echo -e "${YELLOW}🔥 FASE 2.6: Verificación y configuración de firewall${NC}"
    restore_firewall_rules || {
        echo -e "${YELLOW}⚠️  Advertencia: No se pudo configurar/restaurar el firewall${NC}"
        echo -e "${CYAN}💡 El sistema continuará, pero el firewall puede no estar configurado${NC}"
        echo -e "${CYAN}💡 Puedes configurarlo manualmente con: ./rag_system.sh firewall configure${NC}"
        # No marcamos como error crítico, solo advertencia
    }
    
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

restart_rag_service() {
    echo -e "${PURPLE}🔄 REINICIANDO SOLO SERVICIO RAG${NC}"
    echo "=================================================================="
    echo -e "${YELLOW}⚠️  NOTA: Este comando NO reinicia Ollama, Qdrant u otros servicios${NC}"
    echo -e "${CYAN}💡 Esto permite que el proceso de ingesta continúe sin interrupciones${NC}"
    echo "=================================================================="
    
    # Detener solo el servicio RAG
    if check_rag_service; then
        echo -e "${BLUE}🛑 Deteniendo servicio RAG...${NC}"
        screen -S "$RAG_SERVICE_NAME" -X quit
        sleep 2
        echo -e "${GREEN}✅ Servicio RAG detenido${NC}"
    else
        echo -e "${YELLOW}⚠️  El servicio RAG no estaba ejecutándose${NC}"
    fi
    
    # Iniciar solo el servicio RAG
    echo -e "${BLUE}🚀 Iniciando servicio RAG...${NC}"
    if validate_all_services; then
        start_rag_service
    else
        echo -e "${RED}❌ No se puede iniciar RAG sin las dependencias${NC}"
        return 1
    fi
}

restart_datalayer_service() {
    echo -e "${PURPLE}🔄 REINICIANDO SOLO DATALAYER SERVICE${NC}"
    echo "=================================================================="
    
    # Detener solo el datalayer
    if check_datalayer_service; then
        echo -e "${BLUE}🛑 Deteniendo Datalayer Service...${NC}"
        screen -S "$DATALAYER_SERVICE_NAME" -X quit
        sleep 2
        echo -e "${GREEN}✅ Datalayer Service detenido${NC}"
    else
        echo -e "${YELLOW}⚠️  El Datalayer Service no estaba ejecutándose${NC}"
    fi
    
    # Iniciar solo el datalayer
    echo -e "${BLUE}🚀 Iniciando Datalayer Service...${NC}"
    start_docker_services
    sleep 3
    start_prisma_studio
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
    
    echo ""
    echo -e "${CYAN}🔥 Firewall (Puerto $RAG_PORT):${NC}"
    if check_firewall_rules; then
        echo -e "${GREEN}  ✅ Reglas de firewall activas${NC}"
        echo -e "${CYAN}     IPs permitidas:${NC}"
        for ip in "${ALLOWED_IPS[@]}"; do
            echo -e "${CYAN}       • $ip${NC}"
        done
    else
        echo -e "${YELLOW}  ⚠️  Reglas de firewall no configuradas${NC}"
        echo -e "${CYAN}     💡 Ejecuta: ./rag_system.sh firewall configure${NC}"
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
    echo "  restart   - Reiniciar TODO el sistema (⚠️  reinicia Ollama/Qdrant)"
    echo "  restart rag - Solo reiniciar servicio RAG (✅ NO afecta Ollama/Qdrant)"
    echo "  restart datalayer - Solo reiniciar Datalayer Service"
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
    echo -e "${YELLOW}Firewall:${NC}"
    echo "  firewall configure - Configurar reglas de firewall para puerto 8000"
    echo "  firewall remove    - Eliminar reglas de firewall"
    echo "  firewall status    - Ver estado de reglas de firewall"
    echo ""
    echo -e "${YELLOW}Ver logs específicos:${NC}"
    echo "  logs rag        - Logs del RAG Service"
    echo "  logs datalayer  - Logs del Datalayer"
    echo ""
    echo -e "${YELLOW}Ejemplos:${NC}"
    echo "  $0 start                    # Iniciar todo el sistema"
    echo "  $0 restart rag              # Solo reiniciar RAG (sin afectar ingesta)"
    echo "  $0 restart                  # Reiniciar TODO (incluye Ollama/Qdrant)"
    echo "  $0 status                   # Ver estado completo"
    echo "  $0 check                    # Verificación completa"
    echo "  $0 monitor 60               # Monitorear cada minuto"
    echo "  $0 logs rag                # Ver logs del RAG"
    echo "  $0 start qdrant            # Solo Qdrant"
    echo "  $0 firewall configure     # Configurar firewall"
    echo "  $0 firewall status        # Ver estado del firewall"
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
        if [ -n "$2" ]; then
            case "$2" in
                rag) 
                    restart_rag_service
                    ;;
                datalayer) 
                    restart_datalayer_service
                    ;;
                all|"")
                    restart_all
                    ;;
                *) 
                    echo -e "${RED}❌ Opción desconocida: $2${NC}"
                    echo -e "${YELLOW}💡 Usa: restart [rag|datalayer|all]${NC}"
                    echo -e "${CYAN}   restart rag      - Solo reinicia el servicio RAG (NO afecta Ollama/Qdrant)${NC}"
                    echo -e "${CYAN}   restart datalayer - Solo reinicia el Datalayer${NC}"
                    echo -e "${CYAN}   restart all      - Reinicia TODO el sistema${NC}"
                    exit 1
                    ;;
            esac
        else
            restart_all
        fi
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
    firewall)
        if [ -n "$2" ]; then
            case "$2" in
                configure) configure_firewall ;;
                remove) remove_firewall_rules ;;
                status) show_firewall_status ;;
                *) echo -e "${RED}❌ Comando de firewall desconocido: $2${NC}"; echo -e "${CYAN}💡 Usa: firewall configure, firewall remove, o firewall status${NC}"; exit 1 ;;
            esac
        else
            echo -e "${YELLOW}💡 Especifica la acción: firewall configure, firewall remove, o firewall status${NC}"
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
