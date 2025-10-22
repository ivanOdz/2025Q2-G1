#!/bin/bash

# =================================================================
# USO: Se debe ejecutar desde la Carpeta Raíz del Proyecto:
#      ./scripts/main_deploy.sh <dev|prod>
#


if [ -z "$1" ]; then
    echo "Error: Debe especificar el entorno (dev o prod) como argumento."
    echo "Uso: ./scripts/main_deploy.sh <dev|prod>"
    exit 1
fi

ENV=$1
TERRAFORM_DIR="envs/$ENV" 
TFVARS_FILE="$ENV.tfvars" 

PACKAGE_SCRIPT_DIR="lambdas"
PACKAGE_SCRIPT_NAME="script.py"
DEPLOY_FRONTEND_SCRIPT="./scripts/deploy_frontend.py"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Error: Directorio de Terraform para el entorno '$ENV' no encontrado en: $TERRAFORM_DIR"
    echo "Asegúrate de que tus archivos de configuración (.tf) estén en la carpeta '$ENV/'."
    exit 1
fi


echo "=== 1. PREPARACIÓN: Empaquetado del Backend (Lambda) ==="

echo "Cambiando directorio temporalmente a: $PACKAGE_SCRIPT_DIR"
(
    cd "$PACKAGE_SCRIPT_DIR" || { echo "Error fatal: No se pudo cambiar al directorio $PACKAGE_SCRIPT_DIR. Abortando."; exit 1; }
    python3 "$PACKAGE_SCRIPT_NAME"
)

if [ $? -ne 0 ]; then
    echo "Error: Falló el empaquetado de las funciones Lambda."
    exit 1
fi


echo -e "\n=== 2. DESPLIEGUE DE INFRAESTRUCTURA (Terraform) ==="
echo "Cambiando directorio de trabajo a: $TERRAFORM_DIR"

cd "$TERRAFORM_DIR" || { echo "Error fatal: No se pudo cambiar al directorio $TERRAFORM_DIR. Abortando."; exit 1; }

echo "Ejecutando 'terraform init'..."
terraform init
if [ $? -ne 0 ]; then
    echo "Error: Falló el 'terraform init'."
    cd ..
    exit 1
fi

echo "Ejecutando 'terraform apply'..."
terraform apply -auto-approve -var-file="$TFVARS_FILE"

if [ $? -ne 0 ]; then
    echo "Proceso detenido: Falló el 'terraform apply'."
    cd ..
    exit 1
fi


FRONTEND_BUCKET_NAME=$(terraform output -raw frontend_bucket_name)
API_URL=$(terraform output -raw api_gateway_execution_arn)
COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)

if [ $? -ne 0 ]; then
    echo "Error: No se pudieron obtener los outputs de terraform."
    cd ..
    exit 1
fi

echo "FRONTEND_BUCKET_NAME: $FRONTEND_BUCKET_NAME"
echo "API_URL: $API_URL"
echo "COGNITO_USER_POOL_ID: $COGNITO_USER_POOL_ID"
echo "COGNITO_CLIENT_ID: $COGNITO_CLIENT_ID"

cd ..
if [ -z "$FRONTEND_BUCKET_NAME" ] || [ -z "$API_URL" ] || [ -z "$COGNITO_USER_POOL_ID" ] || [ -z "$COGNITO_CLIENT_ID" ]; then
    echo "Proceso detenido: Faltan Outputs. Revisa la definición de 'frontend_bucket_name', 'api_gateway_execution_arn', 'cognito_user_pool_id' y 'cognito_user_pool_client_id'."
    exit 1
fi


echo -e "\n=== 3. DESPLIEGUE DEL CONTENIDO (Frontend S3) ==="
python3 "$DEPLOY_FRONTEND_SCRIPT" "$FRONTEND_BUCKET_NAME" "$API_URL" "$COGNITO_USER_POOL_ID" "$COGNITO_CLIENT_ID" 

if [ $? -ne 0 ]; then
    echo "🚨 Proceso detenido: Falló el despliegue del frontend."
    exit 1
fi


echo -e "\n=========================================="
echo "🎉 Despliegue de Entorno $ENV COMPLETADO 🎉"
echo "=========================================="