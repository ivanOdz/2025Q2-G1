#!/bin/bash

# =================================================================
# USO: Reescrito del script Python.
#      Requiere el nombre del bucket S3 y el ARN o URL base del API Gateway.
#      ./scripts/deploy_frontend.sh <BUCKET_NAME> <API_ARN_O_URL>

GIT_REPO_URL="https://github.com/julietaTechenski/CLOUD-TP-frontend"
FRONTEND_DIR="CLOUD-TP-frontend"

FRONTEND_BUCKET_NAME=$1
API_ARN_O_URL=$2
COGNITO_USER_POOL_ID=$3
COGNITO_CLIENT_ID=$4


# Función: Convierte un ARN de API Gateway a una URL base.
convert_arn_to_url() {
    local arn="$1"
    
    if [[ "$arn" == arn:aws:execute-api:* ]]; then
        # Extraer región (campo 4) y el sufijo ARN (campo 6)
        REGION=$(echo "$arn" | cut -d':' -f4)
        ARN_SUFFIX=$(echo "$arn" | cut -d':' -f6)
        
        # Extraer API ID (primera parte del sufijo, antes de '/')
        API_ID=$(echo "$ARN_SUFFIX" | cut -d'/' -f1)

        # Construir la URL base
        # Nota: Usamos HTTPS, ya que es el estándar para API Gateway
        API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com"
    else
        # Si no es un ARN, lo devolvemos tal cual.
        echo "$arn"
    fi
}

# Función: Elimina un directorio de forma segura y verifica su existencia.
safe_remove_directory() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        return 0 # Ya no existe, éxito.
    fi
    
    echo "-> Limpiando directorio existente: $dir_path"
    # Usar 'rm -rf' para eliminación forzada. En Bash no necesitamos el manejador de permisos de Python/Windows.
    if ! rm -rf "$dir_path"; then
        echo "Error CRÍTICO: Falló la eliminación del directorio $dir_path."
        return 1
    fi
    return 0
}

if [ -z "$FRONTEND_BUCKET_NAME" ] || [ -z "$API_ARN_O_URL" ] || [ -z "$COGNITO_USER_POOL_ID" ] || [ -z "$COGNITO_CLIENT_ID" ]; then
    echo "Error: Faltan argumentos. Se requieren 4:"
    echo "Uso: $0 <BUCKET_NAME> <API_ARN_O_URL> <USER_POOL_ID> <CLIENT_ID>"
    exit 1
fi

API_BASE_URL=$(convert_arn_to_url "$API_ARN_O_URL")

if [ "$API_BASE_URL" != "$API_ARN_O_URL" ]; then
    echo "ARN convertido a URL: $API_ARN_O_URL -> $API_BASE_URL"
else
    echo "Usando URL directamente: $API_BASE_URL"
fi

FINAL_API_URL="${API_BASE_URL}/api"


echo "-> 1. Verificando y obteniendo la aplicación Frontend desde Git..."
safe_remove_directory "$FRONTEND_DIR" || { echo "🚨 Error: No se pudo limpiar el directorio existente. Abortando."; exit 1; }
git clone "$GIT_REPO_URL" || { echo "Error: Falló el git clone. Abortando."; exit 1; }
cd "$FRONTEND_DIR" || { echo "Error fatal: No se pudo acceder al directorio clonado. Abortando."; exit 1; }


echo "-> 2. Inyectando variables de entorno en .env.production..."
ENV_FILE=".env.production"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: No se encontró el archivo $ENV_FILE"
    cd ..
    exit 1
fi

TEMP_FILE=$(mktemp)

grep -v "^REACT_APP_API_URL=" "$ENV_FILE" \
    | grep -v "^REACT_APP_COGNITO_USER_POOL_ID=" \
    | grep -v "^REACT_APP_COGNITO_CLIENT_ID=" \
    > "$TEMP_FILE"

echo "REACT_APP_API_URL=$FINAL_API_URL" >> "$TEMP_FILE"
echo "REACT_APP_COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID" >> "$TEMP_FILE"
echo "REACT_APP_COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID" >> "$TEMP_FILE"

mv "$TEMP_FILE" "$ENV_FILE"

echo "Escribiendo en $ENV_FILE:"
echo "  REACT_APP_API_URL=$FINAL_API_URL"
echo "  REACT_APP_COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID"
echo "  REACT_APP_COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID"


echo "-> 3. Instalando dependencias y construyendo la aplicación (React)..."
npm install || { echo "Error: Falló la instalación de dependencias. Abortando."; cd ..; exit 1; }
npm run build || { echo "Error: Falló la construcción del Frontend. Abortando."; cd ..; exit 1; }


echo "-> 4. Sincronizando el contenido de 'build/' con s3://$FRONTEND_BUCKET_NAME..."
aws s3 sync build/ "s3://$FRONTEND_BUCKET_NAME" --delete
SYNC_STATUS=$?


echo "-> 5. Limpieza de archivos locales..."
cd ..

safe_remove_directory "$FRONTEND_DIR" || echo "Advertencia: No se pudo eliminar completamente el directorio clonado."


if [ $SYNC_STATUS -eq 0 ]; then
    echo "🎉 Despliegue de Frontend en S3 completado en s3://$FRONTEND_BUCKET_NAME"
    echo "Limpieza de archivos locales completada."
    exit 0
else
    echo "🚨 Error en el despliegue a S3 (Código de estado $SYNC_STATUS). Revisa tus credenciales y permisos de AWS CLI."
    exit 1
fi