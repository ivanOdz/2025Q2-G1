# Lambdas que se Comunican con SNS

## 📊 Resumen

**4 Lambdas** se comunican con SNS (Simple Notification Service):

1. ✅ **`packages_handler.py`** - **PUBLICA** eventos
2. ✅ **`tracks_handler.py`** - **PUBLICA** eventos  
3. ✅ **`images_handler.py`** - **PUBLICA** eventos
4. ✅ **`notifications_handler.py`** - **RECIBE** eventos (vía SQS) y también puede publicar

---

## 🔄 Flujo de Notificaciones

```
┌─────────────────────┐
│ packages_handler    │───┐
│ (crea paquete)      │   │
└─────────────────────┘   │
                          │
┌─────────────────────┐   │    ┌──────────────────┐
│ tracks_handler      │───┼───▶│  SNS Topic       │
│ (actualiza track)   │   │    │  (Principal)      │
└─────────────────────┘   │    └────────┬─────────┘
                          │             │
┌─────────────────────┐   │             │ (SNS → SQS)
│ images_handler      │───┘             ▼
│ (sube imagen)       │          ┌──────────────┐
└─────────────────────┘          │  SQS Queue   │
                                 └──────┬───────┘
                                        │
                                        ▼
                          ┌─────────────────────────┐
                          │ notifications_handler    │
                          │ (procesa mensajes)      │
                          └───────┬─────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
          ┌──────────────────┐      ┌─────────────────────┐
          │  SendGrid Email  │      │  WebSocket          │
          │  (notificaciones)│      │  (updates real-time) │
          └──────────────────┘      └─────────────────────┘
```

---

## 📝 Detalles por Lambda

### 1. **packages_handler.py** 📦

**Rol:** **PUBLICA** eventos a SNS

**Operaciones SNS:**
- ✅ `sns.publish()` - Publica evento `package_created`
- ✅ `sns.create_topic()` - Crea topics por email (legacy, no usado actualmente)
- ✅ `sns.subscribe()` - Suscribe emails a topics (legacy, no usado actualmente)

**Cuándo se ejecuta:**
- Cuando se crea un nuevo paquete (`POST /packages`)

**Mensaje publicado:**
```python
{
    'action': 'package_created',
    'package_id': '...',
    'code': '10000001',
    'user_id': '...',
    'timestamp': '2025-01-20T10:00:00'
}
```

**Topic usado:**
- `SNS_TOPIC_ARN` (topic principal centralizado)

**Código relevante:**
```python
# Línea ~262-280
if SNS_TOPIC_ARN:
    sns_message = {
        'action': 'package_created',
        'package_id': package_id,
        'code': package_code,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat()
    }
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(sns_message),
        Subject='Package Created'
    )
```

---

### 2. **tracks_handler.py** 🚚

**Rol:** **PUBLICA** eventos a SNS

**Operaciones SNS:**
- ✅ `sns.publish()` - Publica evento `package_track_updated`
- ✅ `sns.create_topic()` - Crea topics por email (legacy, no usado actualmente)
- ✅ `sns.subscribe()` - Suscribe emails a topics (legacy, no usado actualmente)

**Cuándo se ejecuta:**
- Cuando se crea un nuevo track (actualización de estado del paquete)
- `POST /packages/{package_id}/tracks`

**Mensaje publicado:**
```python
{
    'action': 'package_track_updated',
    'code': '10000001',
    'track_action': 'SEND_DEPOT',
    'new_state': 'IN_TRANSIT',
    'timestamp': '2025-01-20T10:00:00'
}
```

**Topic usado:**
- `SNS_TOPIC_ARN` (topic principal centralizado)

**Código relevante:**
```python
# Línea ~327-347
if SNS_TOPIC_ARN:
    sns_message = {
        'action': 'package_track_updated',
        'code': package_code,
        'track_action': action,
        'new_state': new_state,
        'timestamp': datetime.utcnow().isoformat()
    }
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(sns_message),
        Subject='Package Track Updated'
    )
```

---

### 3. **images_handler.py** 📸

**Rol:** **PUBLICA** eventos a SNS

**Operaciones SNS:**
- ✅ `sns.publish()` - Publica evento `image_uploaded` (3 veces)

**Cuándo se ejecuta:**
1. Cuando se sube una imagen nueva (`POST /packages/{package_id}/images`)
2. Cuando se actualiza el estado de una imagen (`PUT /packages/{package_id}/images/{image_id}`)
3. Cuando se aprueba/rechaza una imagen (`PUT /packages/{package_id}/images/{image_id}/approve` o `/reject`)

**Mensaje publicado:**
```python
{
    'action': 'image_uploaded',
    'package_id': '...',
    'code': '10000001',
    'image_id': '...',
    's3_key': '...',
    'purpose': 'CREATION',
    'user_id': '...',
    'timestamp': '2025-01-20T10:00:00'
}
```

**Topic usado:**
- `os.environ['SNS_TOPIC_ARN']` (topic principal centralizado)

**Código relevante:**
```python
# Línea ~240-256 (upload)
# Línea ~438-456 (update)
# Línea ~525-543 (approve/reject)
sns.publish(
    TopicArn=os.environ['SNS_TOPIC_ARN'],
    Message=json.dumps(sns_message),
    Subject='Package Image Uploaded'
)
```

---

### 4. **notifications_handler.py** 🔔

**Rol:** **RECIBE** eventos de SNS (vía SQS) y también puede **PUBLICAR**

**Operaciones SNS:**

#### A. **RECIBE mensajes** (Principal)
- ✅ Procesa mensajes de SQS que vienen del SNS Topic
- ✅ Lee el body del mensaje SQS que contiene el mensaje SNS
- ✅ Procesa según `action`: `package_created`, `package_track_updated`, `image_uploaded`

**Cuándo se ejecuta:**
- Cuando SQS recibe un mensaje del SNS Topic (trigger automático)
- Procesa eventos de:
  - `package_created` → Envía email + WebSocket broadcast
  - `package_track_updated` → Envía email + WebSocket broadcast
  - `image_uploaded` → WebSocket broadcast

**Flujo:**
```
SNS Topic → SQS Queue → notifications_handler (lambda trigger)
```

**Código relevante:**
```python
# Línea ~79-104
def handle_sqs_event(event, context):
    """Handle SQS messages from SNS Topic"""
    for record in event['Records']:
        # Parse SNS message
        sns_message = json.loads(record['body'])
        message_data = json.loads(sns_message['Message'])
        
        action = message_data.get('action')
        if action == 'package_created':
            handle_package_created_notification(message_data)
        elif action == 'package_track_updated':
            handle_track_updated_notification(message_data)
        elif action == 'image_uploaded':
            handle_image_uploaded_notification(message_data)
```

#### B. **PUBLICA mensajes** (Legacy/Secundario)
- ✅ `sns.create_topic()` - Crea topics por email (legacy)
- ✅ `sns.subscribe()` - Suscribe emails a topics (legacy)
- ✅ `sns.publish()` - Publica a topics por email (legacy, no usado actualmente)
- ✅ `sns.list_subscriptions_by_topic()` - Lista suscripciones

**Nota:** Estas funciones legacy (`send_email_via_sns`) existen pero **no se usan**. El sistema actual usa **SendGrid** directamente.

**Código relevante (legacy, no usado):**
```python
# Línea ~330-427
def get_or_create_topic_for_email(email):
    topic_name = f"{SNS_TOPIC_PREFIX}{normalize_email_for_topic(email)}"
    create_response = sns.create_topic(Name=topic_name)
    # ...

def send_email_via_sns(email, subject, message_body):
    topic_arn = get_or_create_topic_for_email(email)
    sns.subscribe(TopicArn=topic_arn, Protocol='email', Endpoint=email)
    sns.publish(TopicArn=topic_arn, Subject=subject, Message=message_body)
```

---

## 🎯 Tipos de Eventos Publicados

| Lambda | Evento | Descripción |
|--------|--------|-------------|
| `packages_handler` | `package_created` | Nuevo paquete creado |
| `tracks_handler` | `package_track_updated` | Estado del paquete actualizado |
| `images_handler` | `image_uploaded` | Nueva imagen subida |

---

## 🔗 Configuración

**Variable de entorno requerida:**
- `SNS_TOPIC_ARN` - ARN del topic principal de SNS

**Topic principal:**
- Un solo topic centralizado (`SNS_TOPIC_ARN`)
- Este topic está suscrito a una **SQS Queue**
- La SQS Queue tiene un trigger a `notifications_handler`

**Arquitectura:**
```
Producer Lambdas → SNS Topic → SQS Queue → notifications_handler → SendGrid/WebSocket
```

---

## 📋 Resumen de Operaciones SNS

| Lambda | Operación | Frecuencia | Propósito |
|--------|-----------|------------|------------|
| `packages_handler` | `publish()` | Al crear paquete | Notificar creación |
| `tracks_handler` | `publish()` | Al actualizar track | Notificar cambio de estado |
| `images_handler` | `publish()` | Al subir/actualizar imagen | Notificar imagen |
| `notifications_handler` | `create_topic()` | Legacy (no usado) | Crear topics por email |
| `notifications_handler` | `subscribe()` | Legacy (no usado) | Suscribir emails |
| `notifications_handler` | `publish()` | Legacy (no usado) | Enviar emails vía SNS |
| `notifications_handler` | **Recibe vía SQS** | Automático | Procesar notificaciones |

---

## ✅ Conclusión

**Lambdas que PUBLICAN a SNS:**
1. ✅ `packages_handler.py`
2. ✅ `tracks_handler.py`
3. ✅ `images_handler.py`

**Lambdas que RECIBEN de SNS:**
1. ✅ `notifications_handler.py` (vía SQS)

**Lambdas con código legacy (no usado):**
- `notifications_handler.py` tiene funciones para crear topics por email, pero **no se usan**. El sistema actual usa SendGrid directamente.

