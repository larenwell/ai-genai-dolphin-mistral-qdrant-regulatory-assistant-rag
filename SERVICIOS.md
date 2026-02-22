# 🚀 Gestión de Servicios del Asistente de Normativa

Este documento describe cómo gestionar todos los servicios del Asistente de Normativa con un **script unificado**.

## 📋 Script Unificado

### `rag_system.sh` - **SCRIPT MAESTRO ÚNICO** ⭐
**Gestión completa de TODO el sistema en un solo archivo**

```bash
# Comandos principales
./rag_system.sh start          # Iniciar TODO el sistema
./rag_system.sh stop           # Detener TODO el sistema
./rag_system.sh restart        # Reiniciar TODO el sistema
./rag_system.sh status         # Ver estado de TODO el sistema
./rag_system.sh check          # Verificación completa del sistema
./rag_system.sh monitor        # Monitoreo continuo (30 segundos)
./rag_system.sh monitor 60     # Monitoreo continuo (60 segundos)
./rag_system.sh emergency      # Reinicio de emergencia
./rag_system.sh logs rag       # Ver logs del RAG
./rag_system.sh logs datalayer # Ver logs del Datalayer
./rag_system.sh help           # Mostrar ayuda

# Servicios individuales
./rag_system.sh start qdrant     # Solo Qdrant
./rag_system.sh start ollama     # Solo Ollama
./rag_system.sh start postgresql # Solo PostgreSQL
./rag_system.sh start localstack # Solo LocalStack
./rag_system.sh start rag        # Solo RAG Service
./rag_system.sh start datalayer  # Solo Datalayer Service
```

## 🏗️ Arquitectura de Servicios

### Servicios de Infraestructura
| Servicio | Puerto | Propósito | Estado |
|----------|--------|-----------|--------|
| **Qdrant** | 6333 | Base de datos vectorial | ✅ Activo |
| **Ollama** | 11434 | Modelo de embeddings | ✅ Activo |
| **PostgreSQL** | 5432 | Base de datos relacional | ✅ Activo |
| **LocalStack** | 4566 | Servicios AWS simulados | ✅ Activo |

### Servicios Principales
| Servicio | Puerto | Archivo | Estado |
|----------|--------|---------|--------|
| **RAG Service** | 8000 | `src/ui/app.py` | ✅ Activo |
| **Datalayer Service** | 5555 | Prisma Studio | ✅ Activo |

## 🔧 Comandos Útiles

### Verificar Estado Rápido
```bash
./rag_system.sh status
```

### Verificación Completa del Sistema
```bash
./rag_system.sh check
```

### Ver Logs del RAG
```bash
./rag_system.sh logs rag
```

### Ver Logs del Datalayer
```bash
./rag_system.sh logs datalayer
```

### Reiniciar Solo un Servicio
```bash
./rag_system.sh start qdrant
```

### Monitoreo en Tiempo Real
```bash
./rag_system.sh monitor
```

### Monitoreo Personalizado
```bash
./rag_system.sh monitor 60  # Cada 60 segundos
```

## 🔄 **REINICIO COMPLETO Y LEVANTAMIENTO DESDE CERO**

### **Caso 1: Reinicio Normal (Servicios funcionando)**
```bash
# Verificar estado actual
./rag_system.sh status

# Reiniciar todo el sistema
./rag_system.sh restart
```

### **Caso 2: Reinicio de Emergencia (Servicios no responden)**
```bash
# Reinicio forzado con limpieza completa
./rag_system.sh emergency
```

### **Caso 3: Levantamiento desde CERO (Sistema apagado)**
```bash
# 1. Verificar que no hay procesos corriendo
ps aux | grep -E "(chainlit|prisma|ollama|qdrant)" | grep -v grep

# 2. Limpiar procesos huérfanos (si los hay)
pkill -f "chainlit"
pkill -f "prisma"
pkill -f "ollama serve"

# 3. Limpiar contenedores Docker
docker stop $(docker ps -q) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true

# 4. Iniciar sistema completo
./rag_system.sh start

# 5. Verificar que todo esté funcionando
./rag_system.sh status
```

### **Caso 4: Levantamiento después de Reinicio del Servidor**
```bash
# 1. Navegar al directorio del proyecto
cd /root/ai-genai-rag-asistente-normativa-sincro

# 2. Verificar que el script esté ejecutable
chmod +x rag_system.sh

# 3. Iniciar sistema completo
./rag_system.sh start

# 4. Verificar estado
./rag_system.sh status

# 5. Verificar URLs
echo "🌐 Asistente RAG: http://161.132.45.154:8000/"
echo "📊 Feedback: http://161.132.45.154:5555/"
```

### **Caso 5: Problemas de Puerto (Puerto en uso)**
```bash
# Verificar qué está usando los puertos
netstat -tlnp | grep -E ":(8000|5555|6333|11434|5432|4566)"

# Matar procesos específicos si es necesario
sudo fuser -k 8000/tcp  # Puerto RAG
sudo fuser -k 5555/tcp  # Puerto Datalayer
sudo fuser -k 6333/tcp  # Puerto Qdrant

# Reiniciar sistema
./rag_system.sh start
```

### **Caso 6: Problemas de Base de Datos**
```bash
# Reiniciar solo servicios de base de datos
./rag_system.sh start postgresql
./rag_system.sh start datalayer

# Verificar conexión a PostgreSQL
pg_isready -h localhost -p 5432

# Verificar Qdrant
curl -s http://localhost:6333/collections
```

### **🔍 Comandos de Verificación Rápida**
```bash
# Verificar todos los puertos
netstat -tlnp | grep -E ":(8000|5555|6333|11434|5432|4566)"

# Verificar procesos activos
ps aux | grep -E "(chainlit|prisma|ollama|qdrant)" | grep -v grep

# Verificar contenedores Docker
docker ps

# Verificar sesiones screen
screen -list

# Verificar conectividad de servicios
curl -s http://localhost:8000/ | head -5    # RAG Service
curl -s http://localhost:5555/ | head -5    # Datalayer
curl -s http://localhost:6333/collections   # Qdrant
curl -s http://localhost:11434/api/tags     # Ollama
```

### **⚡ Comando de Verificación Completa**
```bash
# Script de verificación rápida
./rag_system.sh check
```

## 🚨 Solución de Problemas

### Si un servicio no responde:
1. **Verificar estado**: `./rag_system.sh status`
2. **Verificación completa**: `./rag_system.sh check`
3. **Reiniciar servicio específico**: `./rag_system.sh start [servicio]`
4. **Reinicio completo**: `./rag_system.sh restart`
5. **Reinicio de emergencia**: `./rag_system.sh emergency`

### Si todos los servicios fallan:
```bash
./rag_system.sh emergency
```

### Verificar logs específicos:
```bash
# Logs del RAG
./rag_system.sh logs rag

# Logs del Datalayer
./rag_system.sh logs datalayer

# Logs de Docker
docker logs qdrant-rag
docker logs postgres-rag
docker logs localstack-rag

# Logs de Ollama
journalctl -u ollama
```

## 📊 URLs de Acceso

- **Asistente RAG**: http://161.132.45.154:8000/
- **Feedback Datalayer**: http://161.132.45.154:5555/
- **Qdrant Dashboard**: http://161.132.45.154:6333/dashboard

## 🔄 Flujo de Inicio Automático

1. **Verificación**: El script verifica si cada servicio ya está corriendo
2. **Inicio Inteligente**: Solo inicia servicios que no estén activos
3. **Espera de Listo**: Espera a que cada servicio esté completamente listo
4. **Verificación Final**: Confirma que todos los servicios están funcionando
5. **Reporte**: Muestra el estado final y URLs de acceso

## ⚡ Características Avanzadas

- **Script único**: Todo en un solo archivo (24KB)
- **Colores en terminal**: Estados visuales claros
- **Verificación inteligente**: No reinicia servicios ya activos
- **Manejo de errores**: Reporta problemas específicos
- **Logs detallados**: Información completa del proceso
- **Monitoreo continuo**: Verificación automática del estado
- **Reinicio de emergencia**: Limpieza completa del sistema

## 🎯 Casos de Uso

### Desarrollo Diario
```bash
./rag_system.sh start
./rag_system.sh status
```

### Despliegue en Producción
```bash
./rag_system.sh restart
./rag_system.sh monitor 60  # Monitorear cada minuto
```

### Resolución de Problemas
```bash
./rag_system.sh check
./rag_system.sh emergency
./rag_system.sh status
```

### Monitoreo Continuo
```bash
./rag_system.sh monitor 30  # Monitorear cada 30 segundos
```

---

## 🎯 **VENTAJAS DEL SCRIPT UNIFICADO**

### **✅ Beneficios**
- **Un solo archivo**: 24KB vs 5 archivos (32KB total)
- **Comandos simples**: `./rag_system.sh [comando]`
- **Funcionalidad completa**: Todo integrado
- **Fácil mantenimiento**: Un solo archivo que actualizar
- **Menos confusión**: Un solo punto de entrada
- **Portabilidad**: Fácil de copiar y usar

### **📊 Comparación**
| Antes | Después |
|-------|---------|
| 5 archivos .sh | 1 archivo .sh |
| 32KB total | 24KB total |
| Múltiples comandos | Un solo comando |
| Confuso | Simple |

---

**💡 Tip**: Usa `./rag_system.sh help` para ver todos los comandos disponibles.