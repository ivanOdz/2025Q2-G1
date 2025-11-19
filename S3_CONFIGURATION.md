# Configuración de S3 - Documentación Completa

## 📊 Resumen

Este proyecto utiliza **3 buckets S3** con diferentes propósitos y configuraciones:

1. **Lambda Code Bucket** - Almacena código de Lambda y layers
2. **Images Bucket** - Almacena imágenes de paquetes
3. **Frontend Bucket** - Hosting estático del frontend React

---

## 🗂️ Buckets S3

### 1. **Lambda Code Bucket** 📦

**Propósito:** Almacenar artefactos de despliegue de Lambda (ZIP files y layers)

**Configuración:**
```hcl
module "lambda_code_bucket" {
  source = "../../modules/s3-bucket"
  
  bucket_name       = var.code_bucket
  tags              = local.common_tags
  versioning_enabled = true          # ✅ Versionado habilitado
  encryption_algorithm = "AES256"    # Encriptación server-side
}
```

**Características:**
- ✅ **Versionado habilitado** - Permite mantener versiones históricas de código
- ✅ **Encriptación AES256** - Encriptación server-side automática
- ✅ **Acceso privado** - Solo accesible por AWS services (Lambda, Terraform)
- ✅ **Sin CORS** - No necesita CORS (no acceso desde navegador)
- ✅ **Sin lifecycle rules** - Los artefactos se mantienen indefinidamente

**Estructura de objetos:**
```
lambda_code_bucket/
├── lambda/
│   ├── packages_handler.zip
│   ├── tracks_handler.zip
│   ├── images_handler.zip
│   ├── notifications_handler.zip
│   └── ...
└── layer/
    └── sendgrid-layer.zip
```

**Uso:**
- Terraform sube los ZIP files al bucket
- Lambda functions se despliegan desde estos objetos S3
- Lambda layers también se almacenan aquí

**Permisos:**
- Lambda execution role necesita `s3:GetObject` en este bucket
- Terraform necesita `s3:PutObject`, `s3:GetObject`, `s3:ListBucket`

---

### 2. **Images Bucket** 🖼️

**Propósito:** Almacenar imágenes de paquetes (fotos de creación, entrega, etc.)

**Configuración:**
```hcl
module "images_bucket" {
  source = "../../modules/s3-bucket"
  
  bucket_name = var.images_bucket
  tags        = local.common_tags
  
  # Seguridad - Bloqueo de acceso público
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
  
  # Encriptación
  encryption_algorithm = "AES256"
  
  # Versionado deshabilitado (no necesario para imágenes)
  versioning_enabled = false
  
  # CORS - Permite uploads desde frontend
  cors_rules = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "PUT", "POST", "DELETE"]
      allowed_origins = ["*"]  # ⚠️ Permite cualquier origen
      expose_headers  = ["ETag"]
      max_age_seconds = 3000
    }
  ]
  
  # Lifecycle rules - Optimización de costos
  lifecycle_rules = [
    {
      # Eliminar uploads multipart incompletos después de 7 días
      id = "delete-incomplete-multipart-uploads"
      abort_incomplete_multipart_upload = {
        days_after_initiation = 7
      }
    },
    {
      # Transición de storage class para ahorrar costos
      id = "transition-old-images"
      transitions = [
        {
          days          = 90
          storage_class = "STANDARD_IA"  # Infrequent Access
        },
        {
          days          = 365
          storage_class = "GLACIER_IR"   # Glacier Instant Retrieval
        }
      ]
    }
  ]
}
```

**Características:**
- ✅ **Privado por defecto** - No acceso público directo
- ✅ **CORS habilitado** - Permite uploads desde frontend
- ✅ **Lifecycle rules** - Optimización automática de costos
- ✅ **Event notifications** - Dispara Lambda al subir imágenes
- ✅ **Presigned URLs** - Acceso temporal seguro a imágenes

**Estructura de objetos:**
```
images_bucket/
└── packages/
    └── {package_code}/
        ├── {image_id}.jpg
        ├── {image_id}.png
        └── {image_id}.gif
```

**Flujo de uso:**

#### A. **Upload de Imagen (Presigned URL)**

```
1. Cliente → API Gateway → Lambda (images_handler)
   POST /packages/{code}/images
   
2. Lambda genera presigned URL:
   s3.generate_presigned_url(
       'put_object',
       Params={
           'Bucket': S3_BUCKET_NAME,
           'Key': f'packages/{package_code}/{image_id}.jpg',
           'ContentType': 'image/jpeg'
       },
       ExpiresIn=3600  # 1 hora
   )
   
3. Lambda guarda metadata en DynamoDB:
   - image_id
   - package_id
   - s3_key
   - status: 'PENDING'
   
4. Lambda retorna presigned URL al cliente:
   {
     "upload_url": "https://bucket.s3.amazonaws.com/packages/...?X-Amz-Signature=...",
     "image_id": "abc123",
     "expires_in": 3600
   }
   
5. Cliente sube imagen directamente a S3 usando presigned URL
   
6. S3 dispara evento → Lambda (images_handler)
   - Actualiza status a 'APPROVED' o 'PENDING_REVIEW'
   - Publica a SNS
```

#### B. **Download de Imagen (Presigned URL)**

```
1. Cliente → API Gateway → Lambda (images_handler)
   GET /packages/{code}/images
   
2. Lambda genera presigned URL para cada imagen:
   s3.generate_presigned_url(
       'get_object',
       Params={
           'Bucket': S3_BUCKET_NAME,
           'Key': image['s3_key']
       },
       ExpiresIn=3600  # 1 hora
   )
   
3. Cliente usa presigned URL para descargar imagen
```

**Event Notifications:**
```hcl
resource "aws_s3_bucket_notification" "images_bucket_notification" {
  bucket = module.images_bucket.bucket_id

  # Dispara Lambda cuando se sube .jpg
  lambda_function {
    lambda_function_arn = module.lambdas["images"].function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "packages/"
    filter_suffix       = ".jpg"
  }
  
  # Dispara Lambda cuando se sube .png
  lambda_function {
    lambda_function_arn = module.lambdas["images"].function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "packages/"
    filter_suffix       = ".png"
  }
  
  # Dispara Lambda cuando se sube .gif
  lambda_function {
    lambda_function_arn = module.lambdas["images"].function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "packages/"
    filter_suffix       = ".gif"
  }
}
```

**Lifecycle Rules explicadas:**

1. **Eliminar multipart incompletos (7 días)**
   - Si un upload multipart se interrumpe, se elimina automáticamente
   - Evita costos de almacenamiento de partes incompletas

2. **Transición a STANDARD_IA (90 días)**
   - Imágenes no accedidas en 90 días → Infrequent Access
   - Costo: ~50% menos que STANDARD
   - Acceso: Mismo rendimiento

3. **Transición a GLACIER_IR (365 días)**
   - Imágenes no accedidas en 1 año → Glacier Instant Retrieval
   - Costo: ~68% menos que STANDARD
   - Acceso: Instantáneo (milisegundos)

**CORS Configuration:**
```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

**⚠️ Nota de seguridad:** `allowed_origins = ["*"]` permite cualquier origen. Para producción, debería ser:
```hcl
allowed_origins = [
  "https://fast-track-delivery-dev-frontend-2025-ddjvi-vitel-tone.s3-website-us-east-1.amazonaws.com",
  "https://yourdomain.com"
]
```

**Permisos:**
- Lambda execution role necesita:
  - `s3:PutObject` - Para generar presigned URLs de upload
  - `s3:GetObject` - Para generar presigned URLs de download
  - `s3:ListBucket` - Para listar objetos (opcional)
- S3 necesita permiso para invocar Lambda (event notifications)

---

### 3. **Frontend Bucket** 🌐

**Propósito:** Hosting estático del frontend React (Single Page Application)

**Configuración:**
```hcl
module "frontend_bucket" {
  source = "../../modules/s3-bucket"
  
  bucket_name = var.frontend_bucket
  tags        = local.common_tags
  
  # Acceso público habilitado (necesario para website hosting)
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
  
  # Website configuration
  website_configuration = {
    index_document = "index.html"
    error_document = "index.html"  # SPA - todas las rutas van a index.html
    routing_rules  = null
  }
}

# Bucket policy para acceso público de lectura
resource "aws_s3_bucket_policy" "frontend_bucket_policy" {
  bucket = module.frontend_bucket.bucket_id
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "PublicReadGetObject",
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:GetObject",
        Resource  = [format("%s/*", module.frontend_bucket.bucket_arn)]
      }
    ]
  })
}
```

**Características:**
- ✅ **Website hosting habilitado** - S3 actúa como servidor web estático
- ✅ **Acceso público** - Cualquiera puede leer objetos (necesario para website)
- ✅ **Error document = index.html** - Soporte para SPA (React Router)
- ✅ **Sin versionado** - No necesario para frontend
- ✅ **Sin encriptación** - Contenido estático público (opcional)

**Estructura de objetos:**
```
frontend_bucket/
├── index.html
├── static/
│   ├── css/
│   │   └── main.abc123.css
│   ├── js/
│   │   └── main.def456.js
│   └── media/
│       └── logo.xyz789.png
└── favicon.ico
```

**URL de acceso:**
```
http://{bucket-name}.s3-website-{region}.amazonaws.com
```

**Ejemplo:**
```
http://fast-track-delivery-dev-frontend-2025-ddjvi-vitel-tone.s3-website-us-east-1.amazonaws.com
```

**Despliegue:**
- Script `deploy_frontend.py` construye React app y sincroniza a S3
- Usa `aws s3 sync` para subir archivos
- Inyecta variables de entorno en `.env.production`

**Bucket Policy explicada:**
```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",  // Cualquiera
      "Action": "s3:GetObject",  // Solo lectura
      "Resource": "arn:aws:s3:::bucket-name/*"  // Todos los objetos
    }
  ]
}
```

**⚠️ Nota:** El bucket policy permite acceso público, pero el Public Access Block está deshabilitado. Esto es necesario para website hosting.

**Permisos:**
- Deploy script necesita:
  - `s3:PutObject`
  - `s3:PutObjectAcl`
  - `s3:DeleteObject`
  - `s3:ListBucket`
- Público necesita:
  - `s3:GetObject` (concedido por bucket policy)

---

## 🔐 Seguridad y Encriptación

### **Encriptación Server-Side**

Todos los buckets usan **AES256** (encriptación server-side de AWS):

```hcl
encryption_algorithm = "AES256"
```

**¿Qué significa?**
- Los objetos se encriptan automáticamente al guardarse
- AWS maneja las claves de encriptación
- Sin costo adicional
- Transparente para la aplicación

**Alternativa (no usada):**
- `aws:kms` - Usa AWS KMS para gestión de claves
- Más control, pero con costo adicional

### **Public Access Block**

**Images Bucket (Privado):**
```hcl
block_public_acls       = true   # Bloquea ACLs públicas
block_public_policy     = true   # Bloquea políticas públicas
ignore_public_acls      = true   # Ignora ACLs públicas existentes
restrict_public_buckets = true   # Restringe acceso público
```

**Frontend Bucket (Público):**
```hcl
block_public_acls       = false  # Permite ACLs públicas
block_public_policy     = false  # Permite políticas públicas
ignore_public_acls      = false # No ignora ACLs
restrict_public_buckets = false  # No restringe acceso
```

**Lambda Code Bucket:**
- Usa defaults del módulo (todos `true` = privado)

---

## 📋 Lifecycle Rules (Images Bucket)

### **Regla 1: Eliminar Multipart Incompletos**

```hcl
{
  id = "delete-incomplete-multipart-uploads"
  abort_incomplete_multipart_upload = {
    days_after_initiation = 7
  }
}
```

**Propósito:**
- Limpia uploads multipart que no se completaron
- Evita costos de almacenamiento de partes huérfanas

**Cuándo se aplica:**
- Si un upload multipart se inicia pero no se completa en 7 días
- S3 elimina automáticamente todas las partes

### **Regla 2: Transición de Storage Class**

```hcl
{
  id = "transition-old-images"
  transitions = [
    {
      days          = 90
      storage_class = "STANDARD_IA"  # Infrequent Access
    },
    {
      days          = 365
      storage_class = "GLACIER_IR"   # Glacier Instant Retrieval
    }
  ]
}
```

**Storage Classes:**

| Clase | Costo (GB/mes) | Acceso | Uso |
|-------|----------------|--------|-----|
| **STANDARD** | $0.023 | Instantáneo | Imágenes recientes (< 90 días) |
| **STANDARD_IA** | $0.0125 | Instantáneo | Imágenes antiguas (90-365 días) |
| **GLACIER_IR** | $0.004 | Instantáneo | Imágenes muy antiguas (> 365 días) |

**Cálculo de ahorro:**
- Imagen de 1 MB después de 90 días: $0.0125 vs $0.023 = **45% ahorro**
- Imagen de 1 MB después de 365 días: $0.004 vs $0.023 = **83% ahorro**

**Nota:** Las transiciones son automáticas y transparentes. No afectan el acceso a las imágenes.

---

## 🔔 Event Notifications (Images Bucket)

**Configuración:**
```hcl
resource "aws_s3_bucket_notification" "images_bucket_notification" {
  bucket = module.images_bucket.bucket_id

  lambda_function {
    lambda_function_arn = module.lambdas["images"].function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "packages/"
    filter_suffix       = ".jpg"
  }
  # ... mismo para .png y .gif
}
```

**Eventos soportados:**
- `s3:ObjectCreated:*` - Cualquier creación (PUT, POST, COPY, multipart)
- `s3:ObjectCreated:Put` - Solo PUT directo
- `s3:ObjectCreated:Post` - Solo POST
- `s3:ObjectCreated:Copy` - Solo COPY
- `s3:ObjectCreated:CompleteMultipartUpload` - Solo multipart completo

**Filtros:**
- `filter_prefix = "packages/"` - Solo objetos que empiezan con "packages/"
- `filter_suffix = ".jpg"` - Solo objetos que terminan con ".jpg"

**Flujo:**
```
1. Cliente sube imagen a S3 (usando presigned URL)
2. S3 detecta ObjectCreated
3. S3 invoca Lambda (images_handler)
4. Lambda procesa la imagen:
   - Actualiza status en DynamoDB
   - Publica a SNS
   - Notifica vía WebSocket
```

**Permisos requeridos:**
```hcl
resource "aws_lambda_permission" "allow_s3_images_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.lambdas["images"].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = module.images_bucket.bucket_arn
}
```

---

## 🌐 CORS Configuration (Images Bucket)

**Configuración:**
```hcl
cors_rules = [
  {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE"]
    allowed_origins = ["*"]  # ⚠️ Permite cualquier origen
    expose_headers  = ["ETag"]
    max_age_seconds = 3000  # 50 minutos
  }
]
```

**¿Qué es CORS?**
- Cross-Origin Resource Sharing
- Permite que navegadores hagan requests a S3 desde diferentes dominios

**Parámetros:**
- `allowed_headers` - Headers que el cliente puede enviar
- `allowed_methods` - Métodos HTTP permitidos
- `allowed_origins` - Dominios permitidos (⚠️ `["*"]` = cualquier dominio)
- `expose_headers` - Headers que el cliente puede leer
- `max_age_seconds` - Tiempo de cache del preflight request

**⚠️ Recomendación para producción:**
```hcl
allowed_origins = [
  "https://fast-track-delivery-dev-frontend-2025-ddjvi-vitel-tone.s3-website-us-east-1.amazonaws.com",
  "https://yourdomain.com"
]
```

---

## 📊 Resumen de Configuraciones

| Característica | Lambda Code | Images | Frontend |
|----------------|-------------|--------|----------|
| **Versionado** | ✅ Enabled | ❌ Disabled | ❌ Disabled |
| **Encriptación** | ✅ AES256 | ✅ AES256 | ❌ None |
| **Public Access** | ❌ Blocked | ❌ Blocked | ✅ Allowed |
| **CORS** | ❌ No | ✅ Yes | ❌ No |
| **Lifecycle** | ❌ No | ✅ Yes | ❌ No |
| **Events** | ❌ No | ✅ Yes | ❌ No |
| **Website** | ❌ No | ❌ No | ✅ Yes |
| **Bucket Policy** | ❌ No | ❌ No | ✅ Yes |

---

## 🔗 Integraciones

### **S3 → Lambda (Event Notifications)**
- Images bucket dispara `images_handler` cuando se suben imágenes
- Permite procesamiento automático (validación, thumbnails, etc.)

### **Lambda → S3 (Presigned URLs)**
- `images_handler` genera presigned URLs para upload/download
- Permite acceso temporal seguro sin exponer credenciales

### **Terraform → S3 (Deployment)**
- Sube código Lambda al code bucket
- Sincroniza frontend al frontend bucket

---

## 💰 Optimización de Costos

### **Lifecycle Rules (Images Bucket)**
- **STANDARD → STANDARD_IA (90 días):** 45% ahorro
- **STANDARD → GLACIER_IR (365 días):** 83% ahorro

### **Eliminación de Multipart Incompletos**
- Evita costos de almacenamiento de partes huérfanas
- Limpieza automática después de 7 días

### **Versionado**
- **Lambda Code:** Habilitado (necesario para rollbacks)
- **Images:** Deshabilitado (no necesario, ahorra espacio)
- **Frontend:** Deshabilitado (no necesario)

---

## ⚠️ Consideraciones de Seguridad

### **Images Bucket**
1. ✅ **Privado por defecto** - No acceso público directo
2. ⚠️ **CORS muy permisivo** - `allowed_origins = ["*"]` debería ser específico
3. ✅ **Presigned URLs** - Acceso temporal y controlado
4. ✅ **Encriptación** - AES256 habilitado

### **Frontend Bucket**
1. ⚠️ **Acceso público** - Necesario para website hosting
2. ✅ **Solo lectura pública** - Policy solo permite `s3:GetObject`
3. ⚠️ **Sin encriptación** - Contenido estático (opcional)

### **Lambda Code Bucket**
1. ✅ **Completamente privado** - Solo acceso por AWS services
2. ✅ **Versionado** - Permite auditoría y rollbacks
3. ✅ **Encriptación** - AES256 habilitado

---

## 📝 Checklist de Mejoras Recomendadas

### Prioridad Alta
- [ ] Restringir CORS en images bucket a dominios específicos
- [ ] Habilitar encriptación en frontend bucket (opcional pero recomendado)
- [ ] Agregar logging de acceso S3 (opcional)

### Prioridad Media
- [ ] Considerar KMS para encriptación en images bucket (más control)
- [ ] Agregar lifecycle rule para eliminar imágenes muy antiguas (> 2 años)
- [ ] Implementar versionado en images bucket si se necesita auditoría

### Prioridad Baja
- [ ] Configurar replication cross-region (disaster recovery)
- [ ] Habilitar S3 Object Lock (compliance)
- [ ] Configurar S3 Inventory (reporting)

---

## 🔗 Referencias

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [S3 Lifecycle Rules](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [S3 CORS Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cors.html)
- [S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html)
- [S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [S3 Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)

