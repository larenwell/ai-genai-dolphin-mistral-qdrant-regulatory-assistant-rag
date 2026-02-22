# 🔥 Configuración de Firewall Persistente para RAG Service

## 📋 Resumen

Se ha implementado un sistema completo de firewall persistente que:
- ✅ Configura automáticamente las reglas de iptables al iniciar el servicio
- ✅ Guarda las reglas de forma persistente (sobreviven a reinicios)
- ✅ Restaura automáticamente las reglas si no están presentes
- ✅ Verifica y mantiene las reglas activas

---

## 🎯 IPs Permitidas

El puerto **8000** (RAG Service) está configurado para permitir acceso **solo** desde las siguientes IPs:

- `209.45.68.70`
- `161.132.3.56`
- `161.132.3.57`
- `161.132.3.58`
- `161.132.3.59`

**Todas las demás IPs están bloqueadas** por defecto.

---

## 🚀 Funcionalidades Implementadas

### 1. **Configuración Automática**

El firewall se configura automáticamente cuando:
- Inicias el servicio RAG con `./rag_system.sh start rag`
- Inicias todo el sistema con `./rag_system.sh start`
- El servicio RAG ya está corriendo pero las reglas no están presentes

### 2. **Persistencia de Reglas**

Las reglas se guardan de forma persistente usando:
- **Método preferido**: `netfilter-persistent` (si está instalado)
- **Método alternativo**: Guardado manual en `/etc/iptables/rules.v4`

Las reglas **sobreviven a reinicios del sistema**.

### 3. **Restauración Automática**

El script verifica si las reglas están presentes y:
- Si están presentes: ✅ Continúa normalmente
- Si no están presentes: 🔄 Las restaura automáticamente desde el archivo guardado
- Si no existe archivo guardado: 🔧 Configura el firewall por primera vez

### 4. **Verificación Continua**

El sistema verifica las reglas en múltiples puntos:
- Al iniciar el servicio RAG
- Al iniciar todo el sistema (`start_all`)
- Cuando el servicio RAG ya está corriendo

---

## 📝 Comandos Disponibles

### Configurar Firewall Manualmente

```bash
./rag_system.sh firewall configure
```

**Qué hace:**
- Limpia reglas existentes para el puerto 8000
- Agrega reglas para permitir las 5 IPs autorizadas
- Bloquea todas las demás IPs
- Guarda las reglas de forma persistente

### Ver Estado del Firewall

```bash
./rag_system.sh firewall status
```

**Muestra:**
- Si las reglas están activas
- Lista de IPs permitidas
- Reglas de iptables actuales

### Eliminar Reglas de Firewall

```bash
./rag_system.sh firewall remove
```

**⚠️ Advertencia**: Esto elimina todas las reglas de firewall para el puerto 8000, permitiendo acceso desde cualquier IP.

---

## 🔧 Funciones Técnicas

### `configure_firewall()`
Configura las reglas de iptables y las guarda de forma persistente.

**Proceso:**
1. Limpia reglas existentes
2. Agrega reglas ACCEPT para cada IP permitida
3. Agrega regla DROP para todas las demás IPs
4. Guarda las reglas con `netfilter-persistent` o método alternativo

### `restore_firewall_rules()`
Verifica y restaura las reglas si no están presentes.

**Proceso:**
1. Verifica si las reglas están activas
2. Si no están, intenta restaurar desde `/etc/iptables/rules.v4`
3. Si no existe archivo, configura el firewall por primera vez

### `save_firewall_rules_manual()`
Guarda las reglas manualmente en `/etc/iptables/rules.v4`.

**Usado cuando:**
- `netfilter-persistent` no está disponible
- Como método alternativo de respaldo

### `create_firewall_restore_script()`
Crea un servicio systemd para restaurar reglas al arrancar el sistema.

**Ubicación**: `/etc/systemd/system/rag-firewall-restore.service`

**Estado**: Se crea automáticamente si se usa el método manual de guardado.

---

## 🔄 Flujo de Inicio del Sistema

Cuando ejecutas `./rag_system.sh start`:

```
FASE 1: Servicios de infraestructura base
  ├─ Qdrant
  └─ Ollama

FASE 2: Servicios del datalayer
  ├─ PostgreSQL
  └─ LocalStack

FASE 2.5: Validación de servicios críticos
  └─ Verifica Qdrant, Ollama, PostgreSQL

FASE 2.6: Verificación y configuración de firewall ⭐ NUEVO
  └─ restore_firewall_rules()
      ├─ Verifica si las reglas están activas
      ├─ Si no: Restaura desde archivo guardado
      └─ Si no existe archivo: Configura por primera vez

FASE 3: Servicios principales
  ├─ RAG Service (puerto 8000)
  └─ Datalayer Service (puerto 5555)
```

---

## 📊 Verificación de Estado

### Ver Estado Completo del Sistema

```bash
./rag_system.sh status
```

**Incluye sección de firewall:**
```
🔥 Firewall (Puerto 8000):
  ✅ Reglas de firewall activas
     IPs permitidas:
       • 209.45.68.70
       • 161.132.3.56
       • 161.132.3.57
       • 161.132.3.58
       • 161.132.3.59
```

### Verificar Reglas de iptables Directamente

```bash
iptables -L INPUT -n | grep -A 10 "8000"
```

---

## 🛡️ Seguridad

### Reglas Aplicadas

1. **ACCEPT** para cada IP autorizada (5 reglas)
2. **DROP** para todas las demás IPs (1 regla)

**Orden de evaluación:**
- Las reglas ACCEPT se evalúan primero (orden de inserción)
- La regla DROP se evalúa al final (bloquea todo lo demás)

### Verificación de Reglas

Las reglas se verifican en múltiples puntos:
- Al iniciar servicios
- Cuando el servicio RAG ya está corriendo
- Al ejecutar `status` o `check`

---

## 🔍 Troubleshooting

### Las reglas no se guardan

**Problema**: Las reglas se pierden después de reiniciar.

**Solución**:
```bash
# Verificar si netfilter-persistent está instalado
which netfilter-persistent

# Si no está instalado, instalar:
apt-get install iptables-persistent

# Guardar reglas manualmente:
./rag_system.sh firewall configure
```

### No tengo permisos de root

**Problema**: El script requiere permisos de root/sudo.

**Solución**: El script detecta automáticamente si necesitas sudo y lo usa.

### Las reglas no se restauran automáticamente

**Problema**: Después de reiniciar, las reglas no están presentes.

**Solución**:
1. Verificar que `netfilter-persistent` esté instalado
2. Verificar que el archivo `/etc/iptables/rules.v4` exista
3. Ejecutar manualmente: `./rag_system.sh firewall configure`

### Verificar si las reglas están activas

```bash
# Ver estado del firewall
./rag_system.sh firewall status

# Ver reglas directamente
iptables -L INPUT -n | grep 8000

# Verificar si netfilter-persistent guardó las reglas
netfilter-persistent status
```

---

## 📈 Mejoras Implementadas

### ✅ Antes vs Después

**Antes:**
- ❌ Reglas no persistentes (se perdían al reiniciar)
- ❌ Configuración manual requerida
- ❌ No había verificación automática

**Después:**
- ✅ Reglas persistentes (sobreviven a reinicios)
- ✅ Configuración automática al iniciar servicios
- ✅ Restauración automática si las reglas no están presentes
- ✅ Verificación continua del estado del firewall
- ✅ Integración completa en el flujo de inicio del sistema

### 🎯 Beneficios

1. **Seguridad mejorada**: Las reglas siempre están activas
2. **Automatización**: No requiere intervención manual
3. **Robustez**: Se restaura automáticamente si algo falla
4. **Visibilidad**: Estado del firewall visible en `status`
5. **Persistencia**: Las reglas sobreviven a reinicios

---

## 🔐 Archivos y Ubicaciones

### Archivos de Configuración

- **Reglas guardadas**: `/etc/iptables/rules.v4`
- **Servicio systemd**: `/etc/systemd/system/rag-firewall-restore.service` (si se crea)

### Variables en el Script

```bash
# IPs permitidas (configurables en rag_system.sh)
ALLOWED_IPS=(
    "209.45.68.70"
    "161.132.3.56"
    "161.132.3.57"
    "161.132.3.58"
    "161.132.3.59"
)

# Puerto del RAG Service
RAG_PORT="8000"
```

---

## 📚 Referencias

- **netfilter-persistent**: Sistema de persistencia de reglas de iptables
- **iptables**: Herramienta de firewall de Linux
- **systemd**: Sistema de gestión de servicios de Linux

---

## ✅ Checklist de Verificación

Después de configurar el firewall, verifica:

- [ ] Las reglas están activas: `./rag_system.sh firewall status`
- [ ] Las reglas están guardadas: `netfilter-persistent status`
- [ ] El servicio RAG puede iniciarse: `./rag_system.sh start rag`
- [ ] Las IPs autorizadas pueden acceder al puerto 8000
- [ ] Las IPs no autorizadas están bloqueadas
- [ ] Las reglas sobreviven a un reinicio (opcional: reiniciar y verificar)

---

**Última actualización**: 2024-12-22
**Versión del script**: rag_system.sh v2.0 (con firewall persistente)

