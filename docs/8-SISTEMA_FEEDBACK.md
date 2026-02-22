# Sistema de Feedback - Chainlit Datalayer

## 📋 Descripción General

El sistema de feedback permite a los usuarios evaluar las respuestas del asistente mediante **thumbs up/down** y **comentarios opcionales**. Esta información se almacena automáticamente en PostgreSQL y puede visualizarse mediante Prisma Studio.

**Componente**: Chainlit Datalayer  
**Ubicación**: `/root/chainlit-datalayer`  
**Base de Datos**: PostgreSQL (puerto 5432)  
**Interfaz de Visualización**: Prisma Studio (puerto 5555)

---

## 🎯 Propósito

El sistema de feedback permite:
- ✅ **Evaluación de respuestas**: Los usuarios pueden indicar si una respuesta fue útil o no
- ✅ **Comentarios opcionales**: Los usuarios pueden agregar comentarios explicativos
- ✅ **Análisis de calidad**: Los datos de feedback permiten analizar la calidad de las respuestas
- ✅ **Mejora continua**: Los comentarios ayudan a identificar áreas de mejora

---

## 🏗️ Arquitectura del Sistema

### Componentes

```
Usuario (Chainlit UI)
    ↓
Thumbs Up/Down + Comentario (opcional)
    ↓
Chainlit Framework (automático)
    ↓
Prisma ORM
    ↓
PostgreSQL Database
    ↓
Prisma Studio (visualización)
```

### Flujo de Datos

1. **Usuario interactúa** con el asistente en Chainlit (puerto 8000)
2. **Usuario evalúa respuesta** con thumbs up/down y opcionalmente agrega comentario
3. **Chainlit guarda automáticamente** el feedback en PostgreSQL
4. **Prisma Studio** permite visualizar y analizar el feedback (puerto 5555)

---

## 📊 Estructura de la Base de Datos

### Modelo Feedback (Prisma Schema)

El feedback se almacena en la tabla `Feedback` con la siguiente estructura:

```prisma
model Feedback {
    id        String   @id @default(dbgenerated("gen_random_uuid()"))
    createdAt DateTime @default(now())
    updatedAt DateTime @default(now()) @updatedAt

    stepId String?
    Step   Step?   @relation(fields: [stepId], references: [id])

    name  String   // Nombre del feedback (ej: "user_feedback")
    value Float    // Valor: 1.0 (thumbs up) o 0.0 (thumbs down)
    comment String? // Comentario opcional del usuario

    @@index(createdAt)
    @@index(name)
    @@index(stepId)
    @@index(value)
    @@index([name, value])
}
```

### Campos Explicados

- **`id`**: UUID único del feedback
- **`createdAt`**: Fecha y hora de creación (automático)
- **`updatedAt`**: Fecha y hora de última actualización (automático)
- **`stepId`**: ID del paso (Step) asociado al feedback (opcional)
- **`name`**: Nombre del feedback (típicamente "user_feedback")
- **`value`**: Valor numérico del feedback
  - `1.0` = Thumbs Up (👍) - Respuesta útil
  - `0.0` = Thumbs Down (👎) - Respuesta no útil
- **`comment`**: Comentario opcional del usuario (puede ser `null`)

### Relación con Steps

El feedback está relacionado con `Step`, que representa cada paso en una conversación:

```prisma
model Step {
    id        String   @id @default(dbgenerated("gen_random_uuid()"))
    // ... otros campos
    Feedback Feedback[]
}
```

Cada `Step` puede tener múltiples `Feedback` asociados.

---

## 🔧 Configuración

### Variables de Entorno

El sistema requiere las siguientes variables de entorno:

```bash
# PostgreSQL para Chainlit Datalayer
DATABASE_URL=postgresql://root:root@localhost:5432/postgres
```

### Configuración de Chainlit

Chainlit detecta automáticamente la variable `DATABASE_URL` y configura el data layer si está presente. No se requiere configuración adicional en el código de la aplicación.

---

## 🚀 Inicio del Sistema

### Inicio Automático

El sistema de feedback se inicia automáticamente cuando ejecutas:

```bash
./rag_system.sh start
```

Esto inicia:
1. **PostgreSQL** (puerto 5432) - Base de datos
2. **LocalStack** (puerto 4566) - Almacenamiento de elementos
3. **Prisma Studio** (puerto 5555) - Interfaz de visualización

### Inicio Manual

```bash
# Iniciar solo el Datalayer Service
./rag_system.sh start datalayer
```

Esto ejecuta:
1. `docker-compose up -d` en `/root/chainlit-datalayer`
2. `npx prisma migrate deploy` (aplica migraciones)
3. `npx prisma studio --port 5555 --hostname 0.0.0.0` (inicia Prisma Studio)

---

## 📺 Visualización del Feedback

### Prisma Studio

Prisma Studio es la interfaz web para visualizar y gestionar el feedback:

**URL**: http://161.132.45.154:5555/

**Características**:
- ✅ Visualización de todas las tablas (Feedback, Step, Thread, User, Element)
- ✅ Filtrado y búsqueda de feedback
- ✅ Edición de registros (si es necesario)
- ✅ Visualización de relaciones entre tablas

### Acceso

```bash
# Ver logs del Datalayer
./rag_system.sh logs datalayer

# O acceder directamente a Prisma Studio
# http://161.132.45.154:5555/
```

---

## 📊 Modelos de Datos Relacionados

### Thread (Conversación)

```prisma
model Thread {
    id        String    @id @default(dbgenerated("gen_random_uuid()"))
    createdAt DateTime  @default(now())
    updatedAt DateTime  @default(now()) @updatedAt
    deletedAt DateTime?

    name     String?
    metadata Json
    tags     String[] @default([])

    elements Element[]
    userId   String?
    User     User?     @relation(fields: [userId], references: [id])
    steps    Step[]
}
```

Representa una conversación completa entre el usuario y el asistente.

### Step (Paso)

```prisma
model Step {
    id        String   @id @default(dbgenerated("gen_random_uuid()"))
    createdAt DateTime @default(now())
    updatedAt DateTime @default(now()) @updatedAt
    parentId  String?
    threadId  String?

    input     String?
    metadata  Json
    name      String?
    output    String?
    type      StepType
    showInput String?  @default("json")
    isError   Boolean? @default(false)

    startTime DateTime
    endTime   DateTime

    elements Element[]
    parent   Step?      @relation("ParentChild", fields: [parentId], references: [id])
    children Step[]     @relation("ParentChild")
    thread   Thread?    @relation(fields: [threadId], references: [id])
    Feedback Feedback[]
}
```

Representa cada paso en una conversación (mensaje del usuario, respuesta del asistente, etc.).

### User (Usuario)

```prisma
model User {
    id         String   @id @default(dbgenerated("gen_random_uuid()"))
    createdAt  DateTime @default(now())
    updatedAt  DateTime @default(now()) @updatedAt
    metadata   Json
    identifier String
    threads    Thread[]

    @@unique([identifier])
    @@index([identifier])
}
```

Representa un usuario del sistema.

---

## 🔍 Consultas Útiles

### Ver Feedback Reciente

En Prisma Studio, puedes filtrar por:
- **Fecha de creación**: `createdAt` (últimos 7 días, etc.)
- **Valor**: `value` (1.0 para thumbs up, 0.0 para thumbs down)
- **Paso asociado**: `stepId`

### Estadísticas de Feedback

Puedes consultar directamente en PostgreSQL:

```sql
-- Total de feedback
SELECT COUNT(*) FROM "Feedback";

-- Thumbs up vs thumbs down
SELECT 
    CASE 
        WHEN value = 1.0 THEN 'Thumbs Up'
        WHEN value = 0.0 THEN 'Thumbs Down'
        ELSE 'Otro'
    END as tipo,
    COUNT(*) as cantidad
FROM "Feedback"
GROUP BY tipo;

-- Feedback con comentarios
SELECT COUNT(*) 
FROM "Feedback" 
WHERE comment IS NOT NULL AND comment != '';

-- Feedback por fecha
SELECT 
    DATE("createdAt") as fecha,
    COUNT(*) as cantidad
FROM "Feedback"
GROUP BY DATE("createdAt")
ORDER BY fecha DESC;
```

---

## 🔄 Migraciones de Base de Datos

### Aplicar Migraciones

Las migraciones de Prisma se aplican automáticamente al iniciar el datalayer:

```bash
cd /root/chainlit-datalayer
export DATABASE_URL="postgresql://root:root@localhost:5432/postgres"
npx prisma migrate deploy
```

### Migraciones Existentes

El proyecto incluye las siguientes migraciones:

1. **`20250103173917_init_data_layer`**: Migración inicial que crea todas las tablas
2. **`20250108095538_add_tags_to_thread`**: Agrega campo `tags` a Thread

---

## 📝 Uso del Feedback en la Interfaz

### Desde la Interfaz de Chainlit

1. **Usuario hace una pregunta** al asistente
2. **Asistente responde** con información relevante
3. **Usuario puede hacer clic** en:
   - 👍 **Thumbs Up**: Indica que la respuesta fue útil
   - 👎 **Thumbs Down**: Indica que la respuesta no fue útil
4. **Opcionalmente, el usuario puede agregar un comentario** explicando su evaluación
5. **El feedback se guarda automáticamente** en PostgreSQL

### Ejemplo de Feedback

```
Usuario pregunta: "¿Cuál es el artículo 49 de la Ley 29783?"
Asistente responde: [Respuesta con información relevante]

Usuario:
  - Hace clic en 👍 (Thumbs Up)
  - Agrega comentario: "Muy útil, encontré exactamente lo que necesitaba"
  
Resultado: Se guarda en PostgreSQL con value=1.0 y comment="Muy útil..."
```

---

## 🛠️ Gestión del Sistema

### Ver Estado del Datalayer

```bash
# Ver estado completo del sistema
./rag_system.sh status

# Verificar específicamente el Datalayer
./rag_system.sh check
```

### Ver Logs

```bash
# Ver logs del Datalayer Service
./rag_system.sh logs datalayer
```

### Reiniciar Datalayer

```bash
# Reiniciar solo el Datalayer
./rag_system.sh stop
./rag_system.sh start datalayer

# O reiniciar todo el sistema
./rag_system.sh restart
```

---

## 🔐 Seguridad y Acceso

### Acceso a Prisma Studio

- **URL Local**: http://localhost:5555/
- **URL Externa**: http://161.132.45.154:5555/
- **Puerto**: 5555
- **Hostname**: 0.0.0.0 (accesible desde cualquier IP)

**Nota**: Prisma Studio no tiene autenticación por defecto. En producción, considera:
- Restringir acceso mediante firewall
- Usar un proxy reverso con autenticación
- Acceso solo desde red interna

### Acceso a PostgreSQL

- **Puerto**: 5432
- **Usuario**: `root` (configurado en `compose.yaml`)
- **Contraseña**: `root` (configurado en `compose.yaml`)
- **Base de datos**: `postgres`

**Nota**: En producción, usa credenciales seguras.

---

## 📊 Análisis de Feedback

### Métricas Útiles

1. **Tasa de Thumbs Up**: % de respuestas con thumbs up
2. **Tasa de Comentarios**: % de feedback con comentarios
3. **Feedback por Tipo de Pregunta**: Análisis por tipo (factual, interpretative, etc.)
4. **Tendencias Temporales**: Feedback a lo largo del tiempo

### Exportar Datos

Puedes exportar datos de feedback desde Prisma Studio o directamente desde PostgreSQL:

```bash
# Exportar desde PostgreSQL
psql -h localhost -U root -d postgres -c "SELECT * FROM \"Feedback\";" > feedback_export.csv
```

---

## ⚠️ Solución de Problemas

### Error: "Prisma Studio no inicia"

```bash
# Verificar que PostgreSQL esté corriendo
./rag_system.sh start postgresql

# Verificar que las migraciones estén aplicadas
cd /root/chainlit-datalayer
export DATABASE_URL="postgresql://root:root@localhost:5432/postgres"
npx prisma migrate deploy

# Reiniciar Prisma Studio
./rag_system.sh start datalayer
```

### Error: "No se puede conectar a PostgreSQL"

```bash
# Verificar que PostgreSQL esté activo
docker ps | grep postgres

# Verificar conectividad
pg_isready -h localhost -p 5432

# Ver logs de PostgreSQL
docker logs chainlit-datalayer-postgres
```

### Error: "Las migraciones fallan"

```bash
# Verificar que DATABASE_URL esté configurado
echo $DATABASE_URL

# Aplicar migraciones manualmente
cd /root/chainlit-datalayer
export DATABASE_URL="postgresql://root:root@localhost:5432/postgres"
npx prisma migrate deploy

# Si hay errores, verificar el schema
npx prisma validate
```

### Feedback no se guarda

1. **Verificar que DATABASE_URL esté configurado** en el entorno de Chainlit
2. **Verificar que PostgreSQL esté accesible** desde la aplicación
3. **Verificar logs de Chainlit** para errores de conexión
4. **Verificar que las migraciones estén aplicadas**

---

## 📝 Notas Importantes

1. **El feedback se guarda automáticamente**: Chainlit maneja el guardado automáticamente cuando `DATABASE_URL` está configurado.

2. **Los datos persisten en PostgreSQL**: El feedback se almacena permanentemente en la base de datos.

3. **Prisma Studio es solo para visualización**: No modifiques datos directamente desde Prisma Studio en producción.

4. **El feedback está relacionado con Steps**: Cada feedback está asociado a un paso específico en la conversación.

5. **Los comentarios son opcionales**: Los usuarios pueden dar feedback sin comentario.

---

## 🔗 Integración con el Sistema

### Dependencias

El sistema de feedback requiere:
- ✅ **PostgreSQL** (puerto 5432) - Base de datos
- ✅ **LocalStack** (puerto 4566) - Almacenamiento de elementos (opcional)
- ✅ **Prisma** - ORM para gestión de base de datos
- ✅ **Chainlit** - Framework que maneja el feedback automáticamente

### Inicio Automático

El feedback se configura automáticamente cuando:
1. `DATABASE_URL` está configurado en el entorno
2. Las migraciones de Prisma están aplicadas
3. Chainlit detecta la configuración y activa el data layer

---

## 📚 Referencias

- **Documentación de Chainlit Data Layer**: https://docs.chainlit.io/data-layer/overview
- **Prisma Schema**: `/root/chainlit-datalayer/prisma/schema.prisma`
- **Docker Compose**: `/root/chainlit-datalayer/compose.yaml`
- **Script de Gestión**: `rag_system.sh`
- **Documentación de Puertos**: `docs/PUERTOS_SERVICIOS.md`

---

**Última Actualización:** 2025-01-05

