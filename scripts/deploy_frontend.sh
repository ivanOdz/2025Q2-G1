#!/bin/bash

# =================================================================
# USO: Reescrito del script Python.
#      Requiere el nombre del bucket S3 y el ARN o URL base del API Gateway.
#      ./scripts/deploy_frontend.sh <BUCKET_NAME> <API_ARN_O_URL>

GIT_REPO_URL="https://github.com/julietaTechenski/CLOUD-TP-frontend"
FRONTEND_DIR="CLOUD-TP-frontend"

FRONTEND_BUCKET_NAME=$1
API_ARN_O_URL=$2


convert_arn_to_url() {
    local arn="$1"
    
    if [[ "$arn" == arn:aws:execute-api:* ]]; then
        REGION=$(echo "$arn" | cut -d':' -f4)
        ARN_SUFFIX=$(echo "$arn" | cut -d':' -f6)
        API_ID=$(echo "$ARN_SUFFIX" | cut -d'/' -f1)

        API_URL="http://${API_ID}.execute-api.${REGION}.amazonaws.com"
        echo "$API_URL"
    else
        echo "$arn"
    fi
}

safe_remove_directory() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        return 0 # Ya no existe
    fi
    
    echo "-> Eliminando directorio: $dir_path"
    if ! rm -rf "$dir_path"; then
        echo "Advertencia: Falló la eliminación con rm -rf. Esto puede ser normal en sistemas con archivos bloqueados."
        return 1
    fi
    return 0
}


if [ -z "$FRONTEND_BUCKET_NAME" ] || [ -z "$API_ARN_O_URL" ]; then
    echo "Error: Faltan argumentos. Se requiere el nombre del bucket y la URL/ARN del API Gateway."
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
safe_remove_directory "$FRONTEND_DIR" || exit 1
git clone "$GIT_REPO_URL" || { echo "Error: Falló el git clone. Abortando."; exit 1; }
cd "$FRONTEND_DIR" || { echo "Error fatal: No se pudo acceder al directorio clonado. Abortando."; exit 1; }


echo "-> 2. Inyectando URL de API Gateway en .env.production..."
ENV_FILE=".env.production"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: No se encontró el archivo $ENV_FILE"
    cd ..
    exit 1
fi


TEMP_FILE=$(mktemp)

grep -v "^REACT_APP_API_URL=" "$ENV_FILE" > "$TEMP_FILE"
echo "REACT_APP_API_URL=$FINAL_API_URL" >> "$TEMP_FILE"
mv "$TEMP_FILE" "$ENV_FILE"

echo "Escribiendo en $ENV_FILE: REACT_APP_API_URL=$FINAL_API_URL"


echo "-> 3. Instalando dependencias y construyendo la aplicación (React)..."
npm install || { echo "Error: Falló la instalación de dependencias. Abortando."; cd ..; exit 1; }

npm run build || { echo "Error: Falló la construcción del Frontend. Abortando."; cd ..; exit 1; }



echo "-> 4. Sincronizando el contenido de 'build/' con s3://$FRONTEND_BUCKET_NAME..."
aws s3 sync build/ "s3://$FRONTEND_BUCKET_NAME" --delete
SYNC_STATUS=$?



echo "-> 5. Limpieza de archivos locales..."
cd ..

safe_remove_directory "$FRONTEND_DIR"

if [ $SYNC_STATUS -eq 0 ]; then
    echo "Despliegue de Frontend en S3 completado en s3://$FRONTEND_BUCKET_NAME"
    echo "Limpieza de archivos locales completada."
    exit 0
else
    echo "Error en el despliegue a S3 (Código de estado $SYNC_STATUS). Revisa tus credenciales y permisos de AWS CLI."
    exit 1
fi