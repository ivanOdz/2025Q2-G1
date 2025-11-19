# DynamoDB Architecture Documentation

## 📊 Overview

Este proyecto usa **8 tablas DynamoDB** con un diseño de **tablas separadas por entidad** (multi-table design). Todas las tablas usan **PAY_PER_REQUEST** (on-demand billing).

---

## 🗂️ Tablas y Estructura

### 1. **package-tracking-packages** (Tabla Principal)

**Propósito:** Almacena información de paquetes

**Claves:**
- **Partition Key (PK):** `package_id` (String) - UUID único
- **Sort Key:** ❌ No tiene

**Índices Globales Secundarios (GSI):**
1. **`code-index`**
   - Hash Key: `code` (código de tracking público, ej: "10000001")
   - Proyección: ALL
   - **Uso:** Búsqueda por código de tracking (endpoint público)

2. **`sender-index`**
   - Hash Key: `sender_id` (ID del usuario que creó el paquete)
   - Proyección: ALL
   - **Uso:** Listar paquetes de un usuario específico

3. **`state-index`**
   - Hash Key: `state` (CREATED, IN_TRANSIT, DELIVERED, etc.)
   - Proyección: ALL
   - **Uso:** Filtrar paquetes por estado

**Atributos Principales:**
- `package_id`, `code`, `origin`, `destination`, `sender_id`
- `receiver_name`, `receiver_email`, `state`, `priority`
- `weight`, `size`, `created_at`, `updated_at`

**Patrones de Acceso:**
- ✅ `get_item(package_id)` - Obtener por ID
- ✅ `query(code-index, code = X)` - Buscar por código público
- ✅ `query(sender-index, sender_id = X)` - Paquetes de un usuario
- ✅ `query(state-index, state = X)` - Filtrar por estado
- ⚠️ `scan()` - Usado para listar todos (ineficiente)

---

### 2. **package-tracking-tracks**

**Propósito:** Historial de eventos de tracking (timeline)

**Claves:**
- **Partition Key (PK):** `track_id` (String) - UUID único
- **Sort Key:** ❌ No tiene

**Índices Globales Secundarios (GSI):**
1. **`package-index`**
   - Hash Key: `package_id`
   - Proyección: ALL
   - **Uso:** Obtener todos los tracks de un paquete (timeline)

**Atributos Principales:**
- `track_id`, `package_id`, `timestamp`, `action`
- `depot_id`, `depot_name`, `comment`

**Patrones de Acceso:**
- ✅ `query(package-index, package_id = X)` - Timeline de un paquete
- ✅ `put_item()` - Crear nuevo track

---

### 3. **package-tracking-addresses**

**Propósito:** Direcciones reutilizables (origen/destino)

**Claves:**
- **Partition Key (PK):** `address_id` (String) - UUID único
- **Sort Key:** ❌ No tiene
- **Índices:** ❌ Ninguno

**Atributos Principales:**
- `address_id`, `street`, `city`, `province`, `postal_code`, `country`

**Patrones de Acceso:**
- ✅ `get_item(address_id)` - Obtener dirección por ID
- ⚠️ `scan()` - Listar todas las direcciones (ineficiente)

---

### 4. **package-tracking-depots**

**Propósito:** Depósitos/distribuidores

**Claves:**
- **Partition Key (PK):** `depot_id` (String) - UUID único
- **Sort Key:** ❌ No tiene
- **Índices:** ❌ Ninguno

**Atributos Principales:**
- `depot_id`, `name`, `address_id`, `phone`, `email`

**Patrones de Acceso:**
- ✅ `get_item(depot_id)` - Obtener depósito por ID
- ⚠️ `scan()` - Listar todos los depósitos (ineficiente)

---

### 5. **package-tracking-images**

**Propósito:** Metadatos de imágenes de paquetes

**Claves:**
- **Partition Key (PK):** `image_id` (String) - UUID único
- **Sort Key:** ❌ No tiene

**Índices Globales Secundarios (GSI):**
1. **`package-index`**
   - Hash Key: `package_id`
   - Proyección: ALL
   - **Uso:** Obtener todas las imágenes de un paquete

**Atributos Principales:**
- `image_id`, `package_id`, `s3_key`, `purpose`, `status`
- `uploaded_at`, `created_at`

**Patrones de Acceso:**
- ✅ `get_item(image_id)` - Obtener imagen por ID
- ✅ `query(package-index, package_id = X)` - Imágenes de un paquete
- ✅ `put_item()` - Subir nueva imagen

---

### 6. **package-tracking-users**

**Propósito:** Información adicional de usuarios (complementa Cognito)

**Claves:**
- **Partition Key (PK):** `email` (String)
- **Sort Key:** ❌ No tiene
- **Índices:** ❌ Ninguno

**Atributos Principales:**
- `email`, `user_id` (Cognito ID), `first_name`, `last_name`, `role`

**Patrones de Acceso:**
- ✅ `get_item(email)` - Obtener usuario por email
- ✅ `put_item()` - Crear/actualizar usuario

---

### 7. **package-tracking-websocket-connections**

**Propósito:** Gestión de conexiones WebSocket activas

**Claves:**
- **Partition Key (PK):** `connection_id` (String) - ID de API Gateway
- **Sort Key:** ❌ No tiene

**Índices Globales Secundarios (GSI):**
1. **`user-id-index`**
   - Hash Key: `user_id`
   - Proyección: ALL
   - **Uso:** Encontrar conexiones de un usuario (no usado actualmente)

**Atributos Principales:**
- `connection_id`, `user_id`, `package_code` (cuando está suscrito)
- `connected_at`, `ttl` (para auto-expiración)

**TTL (Time To Live):** ✅ Habilitado en atributo `ttl` (1 hora)

**Patrones de Acceso:**
- ✅ `put_item()` - Registrar nueva conexión
- ✅ `get_item(connection_id)` - Obtener conexión
- ✅ `update_item()` - Actualizar suscripción a paquete
- ✅ `delete_item(connection_id)` - Desconectar
- ⚠️ `scan(FilterExpression=package_code=X)` - Buscar suscriptores (ineficiente)

---

### 8. **{base_name}-table** (Tabla Genérica)

**Propósito:** Tabla genérica con patrón PK/SK (no usada activamente)

**Claves:**
- **Partition Key (PK):** `PK` (String)
- **Sort Key:** `SK` (String)

**Índices Globales Secundarios (GSI):**
1. **`GSI1`**
   - Hash Key: `GSI1PK`
   - Sort Key: `GSI1SK`
   - Proyección: ALL

**Estado:** ⚠️ Definida pero no usada en el código

---

## 📈 Patrones de Acceso por Tabla

| Tabla | Operación Principal | Método | Eficiencia |
|-------|-------------------|--------|------------|
| **packages** | Buscar por código | `query(code-index)` | ✅ Eficiente |
| **packages** | Listar por usuario | `query(sender-index)` | ✅ Eficiente |
| **packages** | Listar todos | `scan()` | ❌ Ineficiente |
| **tracks** | Timeline de paquete | `query(package-index)` | ✅ Eficiente |
| **images** | Imágenes de paquete | `query(package-index)` | ✅ Eficiente |
| **websocket** | Buscar suscriptores | `scan(FilterExpression)` | ❌ Ineficiente |
| **addresses** | Listar todos | `scan()` | ❌ Ineficiente |
| **depots** | Listar todos | `scan()` | ❌ Ineficiente |

---

## ✅ Pros (Ventajas)

### 1. **Simplicidad y Claridad**
- ✅ Tablas separadas por entidad = fácil de entender
- ✅ Cada tabla tiene un propósito claro
- ✅ Estructura predecible

### 2. **Escalabilidad**
- ✅ PAY_PER_REQUEST = auto-scaling automático
- ✅ Sin preocuparse por capacidad provisionada
- ✅ Bueno para cargas variables

### 3. **Índices Bien Diseñados**
- ✅ GSI para búsquedas comunes (code-index, package-index)
- ✅ Proyección ALL = no necesita fetch adicional
- ✅ Consultas eficientes para casos de uso principales

### 4. **TTL Automático**
- ✅ WebSocket connections se limpian automáticamente
- ✅ Reduce costos y mantenimiento

### 5. **Flexibilidad**
- ✅ Fácil agregar nuevos atributos sin migración
- ✅ No hay esquema rígido

---

## ❌ Cons (Desventajas)

### 1. **Uso de SCAN (Ineficiente y Costoso)**

**Problemas:**
- ❌ `packages_table.scan()` - Lee TODA la tabla
- ❌ `addresses_table.scan()` - Lee TODA la tabla
- ❌ `depots_table.scan()` - Lee TODA la tabla
- ❌ `websocket_connections_table.scan(FilterExpression=...)` - Lee TODA la tabla

**Impacto:**
- 💰 **Costo:** Escala linealmente con el tamaño de la tabla
- ⏱️ **Performance:** Lento con muchas entradas
- 📊 **Límites:** Máximo 1MB por scan, requiere paginación

**Solución Recomendada:**
- Usar GSI o LSI para queries
- Implementar paginación si es necesario
- Considerar cache (ElastiCache) para listas frecuentes

### 2. **Falta de Índices para Algunos Accesos**

**Problemas:**
- ❌ No hay índice para buscar suscriptores WebSocket por `package_code`
- ❌ No hay índice para listar direcciones/depósitos ordenados
- ❌ Scan con FilterExpression es ineficiente

**Solución:**
- Agregar GSI en `websocket_connections` con `package_code` como hash key
- Considerar índices compuestos para queries complejas

### 3. **Diseño Multi-Table vs Single-Table**

**Problemas:**
- ❌ Más tablas = más complejidad operacional
- ❌ No hay transacciones cross-table nativas
- ❌ Más costos de gestión

**Alternativa:**
- Single-table design con PK/SK compuestos
- Más eficiente pero más complejo de entender

### 4. **Falta de LSI (Local Secondary Index)**

**Problemas:**
- ❌ No hay ordenamiento alternativo en la misma partición
- ❌ Ejemplo: Tracks ordenados por timestamp dentro de un package_id

**Solución:**
- Agregar LSI en tracks con `timestamp` como sort key
- O usar GSI con `package_id#timestamp` como sort key

### 5. **Sin Point-in-Time Recovery**

**Problemas:**
- ❌ `point_in_time_recovery_enabled = false` en todas las tablas
- ❌ No hay backup automático
- ❌ Riesgo de pérdida de datos

**Solución:**
- Habilitar PITR para tablas críticas (packages, tracks)

### 6. **Sin Encriptación en Algunas Tablas**

**Problemas:**
- ❌ `encryption_enabled = false` en la mayoría
- ❌ Datos sensibles (emails, direcciones) sin encriptar

**Solución:**
- Habilitar encriptación server-side (SSE)

### 7. **Tabla Genérica No Usada**

**Problemas:**
- ⚠️ `{base_name}-table` está definida pero nunca se usa
- ❌ Desperdicio de recursos

**Solución:**
- Eliminar si no se va a usar
- O documentar su propósito futuro

---

## 🔧 Recomendaciones de Mejora

### Prioridad Alta

1. **Agregar GSI en websocket_connections:**
   ```hcl
   {
     name = "package-code-index"
     hash_key = "package_code"
     projection_type = "ALL"
   }
   ```
   Cambiar `scan(FilterExpression)` por `query(package-code-index)`

2. **Eliminar scans innecesarios:**
   - Implementar paginación con límites
   - Considerar cache para listas estáticas (depots, addresses)

3. **Habilitar PITR en tablas críticas:**
   - `packages`, `tracks`, `images`

### Prioridad Media

4. **Agregar LSI en tracks:**
   - Sort key: `timestamp` para ordenamiento eficiente

5. **Habilitar encriptación:**
   - Especialmente en `packages` (datos sensibles)

6. **Eliminar tabla genérica:**
   - Si no se va a usar

### Prioridad Baja

7. **Considerar single-table design:**
   - Solo si el proyecto crece significativamente
   - Requiere refactorización mayor

---

## 📊 Resumen de Tablas

| Tabla | PK | SK | GSI | LSI | TTL | Uso Principal |
|-------|----|----|-----|-----|-----|---------------|
| packages | package_id | - | 3 | - | ❌ | Almacenar paquetes |
| tracks | track_id | - | 1 | - | ❌ | Timeline de eventos |
| addresses | address_id | - | - | - | ❌ | Direcciones |
| depots | depot_id | - | - | - | ❌ | Depósitos |
| images | image_id | - | 1 | - | ❌ | Metadatos de imágenes |
| users | email | - | - | - | ❌ | Info de usuarios |
| websocket | connection_id | - | 1 | - | ✅ | Conexiones WebSocket |
| {base}-table | PK | SK | 1 | - | ❌ | No usada |

---

## 💡 Conclusión

**Fortalezas:**
- ✅ Diseño simple y mantenible
- ✅ Índices bien pensados para casos de uso principales
- ✅ Auto-scaling con PAY_PER_REQUEST

**Debilidades:**
- ❌ Uso excesivo de SCAN (costoso e ineficiente)
- ❌ Falta de índices para algunos accesos
- ❌ Sin backups automáticos (PITR)

**Veredicto:** 
Buen diseño para un proyecto pequeño/mediano, pero necesita optimizaciones para escalar. Los SCANs son el mayor problema a resolver.

