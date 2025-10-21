#!/bin/bash

GIT_REPO_URL="https://github.com/julietaTechenski/CLOUD-TP-frontend"
FRONTEND_DIR="CLOUD-TP-frontend" 

FRONTEND_BUCKET_NAME=$1
API_URL=$2

if [ -z "$FRONTEND_BUCKET_NAME" ] || [ -z "$API_URL" ]; then
    echo "Error: Faltan argumentos. Se requiere el nombre del bucket y la URL del API Gateway."
    exit 1
fi

echo "-> 1. Verificando y obteniendo la aplicación Frontend desde Git..."

if [ -d "$FRONTEND_DIR" ]; then
    rm -rf $FRONTEND_DIR
fi

git clone $GIT_REPO_URL || { echo "Error: Falló el git clone. Abortando."; exit 1; }
cd $FRONTEND_DIR || { echo "Error fatal: No se pudo acceder al directorio clonado. Abortando."; exit 1; }


echo "-> 2. Inyectando URL de API Gateway en .env.production..."
ENV_FILE=".env.production"
TEMP_FILE=$(mktemp)

grep -v "^REACT_APP_API_URL=" $ENV_FILE > "$TEMP_FILE"
echo "REACT_APP_API_URL=${API_URL}/api" >> "$TEMP_FILE"
mv "$TEMP_FILE" $ENV_FILE


echo "-> 3. Instalando dependencias y construyendo la aplicación (React)..."
npm install
npm run build || { echo "Error: Falló la construcción del Frontend. Abortando."; exit 1; }


echo "-> 4. Sincronizando el contenido de 'build/' con s3://$FRONTEND_BUCKET_NAME..."
aws s3 sync build/ s3://$FRONTEND_BUCKET_NAME --delete
SYNC_STATUS=$?


echo "-> 5. Limpieza de archivos locales..."
cd ..
rm -rf $FRONTEND_DIR

if [ $SYNC_STATUS -eq 0 ]; then
    echo "Despliegue de Frontend en S3 completado en s3://$FRONTEND_BUCKET_NAME"
    echo "Limpieza de archivos locales completada."
    exit 0
else
    echo "Error en el despliegue a S3. Revisa tus credenciales y permisos."
    exit 1
fi