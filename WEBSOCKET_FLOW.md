# WebSocket API Gateway - Flujo Completo de Mensajería en Tiempo Real

## 📚 ¿Qué es WebSocket API Gateway?

**API Gateway WebSocket** es un servicio de AWS que permite establecer conexiones **bidireccionales persistentes** entre clientes y servidores. A diferencia de HTTP REST (request/response), WebSocket mantiene la conexión abierta, permitiendo:

- ✅ **Comunicación en tiempo real** (real-time)
- ✅ **Baja latencia** (sin overhead de HTTP headers en cada mensaje)
- ✅ **Push notifications** del servidor al cliente
- ✅ **Conexión persistente** (no necesita reconectar para cada mensaje)

---

## 🏗️ Arquitectura en Este Proyecto

```
┌─────────────┐
│   Cliente   │ (Frontend React)
│  (Browser)  │
└──────┬──────┘
       │
       │ wss://...execute-api...amazonaws.com/websocket
       │
       ▼
┌─────────────────────────────────────┐
│  API Gateway WebSocket              │
│  - Route: $connect                 │
│  - Route: $disconnect              │
│  - Route: $default                 │
└──────┬──────────────────────────────┘
       │
       │ Invoca Lambda
       │
       ▼
┌─────────────────────────────────────┐
│  Lambda: notifications_handler      │
│  - Maneja conexiones                │
│  - Procesa mensajes                 │
│  - Envía mensajes vía Management API│
└──────┬───────────────────────────────┘
       │
       │ Almacena conexiones
       │
       ▼
┌─────────────────────────────────────┐
│  DynamoDB: websocket_connections    │
│  - connection_id (PK)              │
│  - user_id                          │
│  - package_code                     │
│  - ttl (auto-expiración)            │
└─────────────────────────────────────┘
```

---

## 🔧 Configuración en Terraform

### 1. **WebSocket API Gateway**

```hcl
resource "aws_apigatewayv2_api" "websocket_api" {
  name          = "${local.base_name}-websocket-api"
  protocol_type = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
  tags          = local.common_tags
}
```

**Parámetros clave:**
- `protocol_type = "WEBSOCKET"` - Define que es un API WebSocket
- `route_selection_expression = "$request.body.action"` - **Cómo se selecciona la ruta**
  - Lee el campo `action` del body del mensaje
  - Ejemplo: `{"action": "subscribe"}` → busca ruta con `route_key = "subscribe"`
  - Si no encuentra ruta específica, usa `$default`

### 2. **Lambda Integration**

```hcl
resource "aws_apigatewayv2_integration" "websocket_lambda" {
  api_id           = aws_apigatewayv2_api.websocket_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = module.lambdas["notifications"].function_invoke_arn
}
```

**Parámetros clave:**
- `integration_type = "AWS_PROXY"` - Proxy directo a Lambda (sin transformación)
- `integration_uri` - ARN de la Lambda que maneja WebSocket

### 3. **Rutas (Routes)**

#### A. **$connect** - Conexión Inicial

```hcl
resource "aws_apigatewayv2_route" "connect" {
  api_id    = aws_apigatewayv2_api.websocket_api.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.websocket_lambda.id}"
}
```

**Cuándo se ejecuta:**
- Cuando el cliente establece la conexión WebSocket
- **Automático** - No requiere mensaje del cliente

**Propósito:**
- Autenticar (opcional)
- Registrar la conexión en DynamoDB
- Extraer información del usuario (query params)

#### B. **$disconnect** - Desconexión

```hcl
resource "aws_apigatewayv2_route" "disconnect" {
  api_id    = aws_apigatewayv2_api.websocket_api.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.websocket_lambda.id}"
}
```

**Cuándo se ejecuta:**
- Cuando el cliente cierra la conexión
- Cuando la conexión expira o falla
- **Automático** - No requiere mensaje del cliente

**Propósito:**
- Limpiar la conexión de DynamoDB
- Liberar recursos

#### C. **$default** - Mensajes del Cliente

```hcl
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.websocket_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.websocket_lambda.id}"
}
```

**Cuándo se ejecuta:**
- Cuando el cliente envía un mensaje que **no coincide** con ninguna ruta específica
- En este proyecto, **todos los mensajes** van a `$default` porque no hay rutas personalizadas

**Mensajes soportados:**
- `{"action": "subscribe", "package_code": "10000001"}`
- `{"action": "unsubscribe", "package_code": "10000001"}`
- `{"action": "ping"}`

### 4. **Stage y Deployment**

```hcl
resource "aws_apigatewayv2_stage" "websocket_stage" {
  api_id      = aws_apigatewayv2_api.websocket_api.id
  name        = "websocket"
  auto_deploy = true
  tags        = local.common_tags
}
```

**Parámetros clave:**
- `name = "websocket"` - Nombre del stage (aparece en la URL)
- `auto_deploy = true` - Despliega automáticamente cuando cambian las rutas

**URL resultante:**
```
wss://{api_id}.execute-api.{region}.amazonaws.com/websocket
```

### 5. **Permisos Lambda**

```hcl
resource "aws_lambda_permission" "websocket_lambda_permission" {
  statement_id  = "AllowExecutionFromWebSocketAPI"
  action        = "lambda:InvokeFunction"
  function_name = module.lambdas["notifications"].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket_api.execution_arn}/*/*"
}
```

**Propósito:**
- Permite que API Gateway invoque la Lambda
- Sin esto, API Gateway no puede llamar a la Lambda

---

## 🔄 Flujo Completo de Conexión y Mensajería

### **Fase 1: Conexión ($connect)**

```
1. Cliente (Frontend)
   └─> new WebSocket("wss://...amazonaws.com/websocket?user_id=xxx")
   
2. API Gateway WebSocket
   └─> Detecta conexión nueva
   └─> Ejecuta ruta $connect
   └─> Invoca Lambda: notifications_handler
   
3. Lambda: handle_websocket_connect()
   ├─> Extrae connection_id del event
   ├─> Extrae user_id de queryStringParameters
   ├─> Guarda en DynamoDB:
   │   {
   │     connection_id: "abc123",
   │     user_id: "user-xxx",
   │     connected_at: "2025-01-20T10:00:00Z",
   │     ttl: 1737360000  // 1 hora
   │   }
   └─> Retorna: {'statusCode': 200}
   
4. API Gateway
   └─> Acepta conexión
   └─> Conexión establecida ✅
```

**Event recibido por Lambda:**
```json
{
  "requestContext": {
    "routeKey": "$connect",
    "connectionId": "abc123xyz",
    "eventType": "CONNECT",
    "connectedAt": 1737360000000,
    "requestTime": "20/Jan/2025:10:00:00 +0000"
  },
  "queryStringParameters": {
    "user_id": "64c85418-a001-7033-1780-cd3bd4c11133"
  }
}
```

---

### **Fase 2: Suscripción a Paquete**

```
1. Cliente (Frontend)
   └─> ws.send(JSON.stringify({
         action: "subscribe",
         package_code: "10000001"
       }))
   
2. API Gateway WebSocket
   └─> Recibe mensaje
   └─> route_selection_expression = "$request.body.action"
   └─> Busca ruta con route_key = "subscribe"
   └─> No encuentra → usa $default
   └─> Invoca Lambda: notifications_handler
   
3. Lambda: handle_websocket_message()
   ├─> Parsea body: {"action": "subscribe", "package_code": "10000001"}
   ├─> Llama: handle_subscribe_to_package(connection_id, "10000001")
   │   ├─> Actualiza DynamoDB:
   │   │   UPDATE websocket_connections
   │   │   SET package_code = "10000001"
   │   │   WHERE connection_id = "abc123"
   │   │
   │   └─> Envía confirmación vía Management API:
   │       send_websocket_message(connection_id, {
   │         action: "subscribed",
   │         package_code: "10000001"
   │       })
   └─> Retorna: {'statusCode': 200}
   
4. Cliente
   └─> Recibe mensaje: {"action": "subscribed", "package_code": "10000001"}
   └─> Suscripción confirmada ✅
```

**Mensaje del cliente:**
```json
{
  "action": "subscribe",
  "package_code": "10000001",
  "user_id": "64c85418-a001-7033-1780-cd3bd4c11133"
}
```

**Event recibido por Lambda:**
```json
{
  "requestContext": {
    "routeKey": "$default",
    "connectionId": "abc123xyz",
    "eventType": "MESSAGE"
  },
  "body": "{\"action\":\"subscribe\",\"package_code\":\"10000001\"}"
}
```

---

### **Fase 3: Envío de Actualizaciones (Push desde Backend)**

```
1. Backend (otra Lambda, ej: tracks_handler)
   └─> Actualiza estado de paquete
   └─> Publica a SNS: {
         action: "package_track_updated",
         code: "10000001",
         new_state: "IN_TRANSIT"
       }
   
2. SNS Topic → SQS Queue → notifications_handler
   └─> handle_track_updated_notification()
   └─> Llama: broadcast_to_subscribers("10000001", message)
   
3. Lambda: broadcast_to_subscribers()
   ├─> Busca en DynamoDB:
   │   SCAN websocket_connections
   │   WHERE package_code = "10000001"
   │
   ├─> Para cada conexión encontrada:
   │   └─> send_websocket_message(connection_id, message)
   │       ├─> Usa API Gateway Management API
   │       ├─> boto3.client('apigatewaymanagementapi')
   │       │   endpoint_url = WEBSOCKET_API_ENDPOINT
   │       │
   │       └─> ws.post_to_connection(
   │             ConnectionId=connection_id,
   │             Data=json.dumps(message).encode('utf-8')
   │           )
   │
   └─> API Gateway envía mensaje al cliente
   
4. Cliente (Frontend)
   └─> ws.onmessage = (event) => {
         const data = JSON.parse(event.data);
         // data = {
         //   action: "package_track_updated",
         //   package_code: "10000001",
         //   new_state: "IN_TRANSIT",
         //   timestamp: "2025-01-20T10:05:00Z"
         // }
         updateUI(data);
       }
   └─> UI actualizada en tiempo real ✅
```

**Mensaje enviado al cliente:**
```json
{
  "action": "package_track_updated",
  "package_code": "10000001",
  "track_action": "SEND_DEPOT",
  "new_state": "IN_TRANSIT",
  "timestamp": "2025-01-20T10:05:00Z",
  "message": "Package 10000001 status updated to IN_TRANSIT"
}
```

---

### **Fase 4: Desconexión ($disconnect)**

```
1. Cliente cierra conexión
   └─> ws.close()
   
2. API Gateway WebSocket
   └─> Detecta desconexión
   └─> Ejecuta ruta $disconnect
   └─> Invoca Lambda: notifications_handler
   
3. Lambda: handle_websocket_disconnect()
   ├─> Extrae connection_id
   └─> DELETE de DynamoDB:
       DELETE websocket_connections
       WHERE connection_id = "abc123"
   
4. Conexión limpiada ✅
```

**Event recibido por Lambda:**
```json
{
  "requestContext": {
    "routeKey": "$disconnect",
    "connectionId": "abc123xyz",
    "eventType": "DISCONNECT"
  }
}
```

---

## 🔑 Conceptos Clave

### 1. **Route Selection Expression**

```hcl
route_selection_expression = "$request.body.action"
```

**Cómo funciona:**
- API Gateway lee el campo `action` del body del mensaje
- Busca una ruta con `route_key` igual a ese valor
- Si no encuentra, usa `$default`

**Ejemplo:**
```json
// Mensaje del cliente
{"action": "subscribe", "package_code": "10000001"}

// API Gateway busca ruta con route_key = "subscribe"
// No encuentra → usa $default
```

**Nota:** En este proyecto, **todas las rutas personalizadas van a $default** porque no hay rutas específicas definidas. Esto es válido y funciona bien.

### 2. **API Gateway Management API**

**¿Qué es?**
- API especial de AWS para **enviar mensajes** a conexiones WebSocket activas
- **No se puede usar HTTP normal** para enviar mensajes
- Requiere el **endpoint específico** del WebSocket API

**Configuración:**
```python
# En Lambda
endpoint = os.environ.get('WEBSOCKET_API_ENDPOINT')
# Ejemplo: https://abc123.execute-api.us-east-1.amazonaws.com/websocket

ws_client = boto3.client(
    'apigatewaymanagementapi',
    endpoint_url=endpoint  # ⚠️ CRÍTICO: debe ser el endpoint HTTP (https://), no wss://
)
```

**Uso:**
```python
ws_client.post_to_connection(
    ConnectionId=connection_id,
    Data=json.dumps(message).encode('utf-8')  # ⚠️ Debe ser bytes en Python 3
)
```

**Endpoint URL:**
- **WebSocket URL (cliente):** `wss://...amazonaws.com/websocket`
- **Management API URL (Lambda):** `https://...amazonaws.com/websocket` (mismo endpoint, pero HTTP)

### 3. **Connection ID**

**¿Qué es?**
- Identificador único de cada conexión WebSocket
- Generado por API Gateway al conectar
- **Necesario** para enviar mensajes a esa conexión específica

**Formato:**
```
abc123xyz456def789
```

**Almacenamiento:**
- Se guarda en DynamoDB como `connection_id` (PK)
- Se usa para:
  - Enviar mensajes a esa conexión
  - Identificar qué usuario está conectado
  - Limpiar conexiones expiradas

### 4. **Respuestas de Lambda**

**Reglas importantes:**

#### ✅ **$connect y $disconnect:**
```python
# ✅ CORRECTO
return {'statusCode': 200}

# ❌ INCORRECTO (rompe la conexión)
return {
    'statusCode': 200,
    'body': json.dumps({'message': 'Connected'})  # NO permitido
}
```

**Razón:** API Gateway espera solo `statusCode` para estas rutas.

#### ✅ **$default (mensajes):**
```python
# ✅ CORRECTO
return {'statusCode': 200}

# ⚠️ Puedes enviar mensajes vía Management API, pero NO en el body de la respuesta
send_websocket_message(connection_id, {'action': 'subscribed'})
return {'statusCode': 200}
```

**Códigos de estado:**
- `200` - Éxito
- `400+` - Error (API Gateway puede cerrar la conexión)
- `500` - Error del servidor

### 5. **TTL (Time To Live) en DynamoDB**

```python
ttl = int((datetime.now(timezone.utc).timestamp() + 3600))  # 1 hora
```

**Propósito:**
- Limpia automáticamente conexiones expiradas
- Evita acumulación de conexiones "zombie"
- DynamoDB elimina el item cuando `ttl < timestamp actual`

**Configuración en Terraform:**
```hcl
ttl_enabled = true
ttl_attribute_name = "ttl"
```

---

## 📤 Tipos de Mensajes

### **Del Cliente al Servidor:**

| Acción | Body | Propósito |
|--------|------|-----------|
| `subscribe` | `{"action": "subscribe", "package_code": "10000001"}` | Suscribirse a actualizaciones de un paquete |
| `unsubscribe` | `{"action": "unsubscribe", "package_code": "10000001"}` | Cancelar suscripción |
| `ping` | `{"action": "ping"}` | Mantener conexión viva (heartbeat) |

### **Del Servidor al Cliente:**

| Acción | Body | Cuándo se envía |
|--------|------|-----------------|
| `subscribed` | `{"action": "subscribed", "package_code": "10000001"}` | Confirmación de suscripción |
| `unsubscribed` | `{"action": "unsubscribed", "package_code": "10000001"}` | Confirmación de cancelación |
| `pong` | `{"action": "pong", "timestamp": "..."}` | Respuesta a ping |
| `package_created` | `{"action": "package_created", "package_code": "...", ...}` | Nuevo paquete creado |
| `package_track_updated` | `{"action": "package_track_updated", "new_state": "...", ...}` | Estado de paquete actualizado |
| `image_uploaded` | `{"action": "image_uploaded", "package_code": "...", ...}` | Nueva imagen subida |
| `echo` | `{"action": "echo", "received": {...}}` | Mensaje desconocido (debug) |

---

## 🔐 Seguridad y Autenticación

### **Autenticación en $connect:**

**Opción 1: Query Parameters (Actual)**
```javascript
// Frontend
const userId = getUserIdFromToken();
const ws = new WebSocket(
  `wss://...amazonaws.com/websocket?user_id=${userId}`
);
```

```python
# Backend
query_params = event.get('queryStringParameters', {})
user_id = query_params.get('user_id', 'anonymous')
```

**Opción 2: Headers (Más seguro)**
```hcl
# En Terraform - agregar authorizer
resource "aws_apigatewayv2_authorizer" "websocket_authorizer" {
  api_id           = aws_apigatewayv2_api.websocket_api.id
  authorizer_type = "REQUEST"
  authorizer_uri  = aws_lambda_function.authorizer.invoke_arn
  identity_sources = ["$request.header.Authorization"]
}
```

**Recomendación:**
- Para producción, usar **Lambda authorizer** en `$connect`
- Validar token JWT antes de aceptar conexión

---

## ⚠️ Limitaciones y Consideraciones

### 1. **Límites de API Gateway WebSocket**

- **Conexiones simultáneas:** 10,000 por región (soft limit, puede aumentar)
- **Tamaño de mensaje:** 32 KB máximo
- **Timeout de conexión inactiva:** 10 minutos (configurable)
- **Costo:** $1.00 por millón de mensajes + $0.25 por millón de minutos de conexión

### 2. **Manejo de Errores**

**GoneException:**
```python
try:
    ws.post_to_connection(ConnectionId=connection_id, Data=...)
except ClientError as e:
    if e.response['Error']['Code'] == 'GoneException':
        # Conexión cerrada, limpiar de DynamoDB
        websocket_connections_table.delete_item(Key={'connection_id': connection_id})
```

**Razón:** La conexión puede cerrarse sin disparar `$disconnect` (timeout, red, etc.)

### 3. **Escalabilidad**

**Problema actual:**
```python
# ❌ INEFICIENTE con muchas conexiones
response = websocket_connections_table.scan(
    FilterExpression=Attr('package_code').eq(package_code)
)
```

**Solución recomendada:**
```hcl
# Agregar GSI en DynamoDB
global_secondary_indexes = [
  {
    name = "package-code-index"
    hash_key = "package_code"
    projection_type = "ALL"
  }
]
```

```python
# ✅ EFICIENTE
response = websocket_connections_table.query(
    IndexName='package-code-index',
    KeyConditionExpression='package_code = :code',
    ExpressionAttributeValues={':code': package_code}
)
```

---

## 🎯 Resumen del Flujo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO COMPLETO DE WEBSOCKET                  │
└─────────────────────────────────────────────────────────────────┘

1. CONEXIÓN
   Cliente → API Gateway ($connect) → Lambda → DynamoDB (guardar)

2. SUSCRIPCIÓN
   Cliente → API Gateway ($default) → Lambda → DynamoDB (actualizar)
   Lambda → Management API → Cliente (confirmación)

3. ACTUALIZACIÓN (Push)
   Backend → SNS → SQS → Lambda → DynamoDB (buscar suscriptores)
   Lambda → Management API → Cliente (mensaje)

4. DESCONEXIÓN
   Cliente cierra → API Gateway ($disconnect) → Lambda → DynamoDB (eliminar)
```

---

## 📝 Checklist de Implementación

- ✅ WebSocket API Gateway creado
- ✅ Rutas: $connect, $disconnect, $default
- ✅ Lambda integration configurada
- ✅ Permisos Lambda otorgados
- ✅ DynamoDB table para conexiones
- ✅ TTL habilitado en DynamoDB
- ✅ Management API client inicializado con endpoint correcto
- ✅ Manejo de GoneException
- ✅ Broadcast a suscriptores implementado
- ⚠️ GSI para búsqueda eficiente (recomendado)
- ⚠️ Authorizer en $connect (recomendado para producción)

---

## 🔗 Referencias

- [AWS API Gateway WebSocket Docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
- [API Gateway Management API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-how-to-call-websocket-api-connections.html)
- [Terraform aws_apigatewayv2_api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_api)

