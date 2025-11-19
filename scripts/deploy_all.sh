#!/bin/bash

# =================================================================
# USO: Se debe ejecutar desde la Carpeta Raíz del Proyecto:
#      ./scripts/deploy_all.sh <dev|prod>
# =================================================================

# Don't use set -e here, we'll handle errors manually in functions

if [ -z "$1" ]; then
    echo "Error: Debe especificar el entorno (dev o prod) como argumento."
    echo "Uso: ./scripts/deploy_all.sh <dev|prod>"
    exit 1
fi

ENV=$1
TERRAFORM_DIR="envs/$ENV" 
TFVARS_FILE="$ENV.tfvars" 

PACKAGE_SCRIPT_DIR="lambdas"
PACKAGE_SCRIPT_NAME="script.py"
DEPLOY_FRONTEND_SCRIPT="./scripts/deploy_frontend.sh"

LAYER_ROOT="lambdas/layer"
LAYER_ZIP="lambdas/layer/sendgrid-layer.zip"
SITE_PACKAGES="lambdas/layer/python/lib/python3.11/site-packages"

# Verify we're in the project root
if [ ! -d "lambdas" ] || [ ! -d "envs" ]; then
    echo "Error: Este script debe ejecutarse desde la raíz del proyecto"
    exit 1
fi

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Error: Directorio de Terraform para el entorno '$ENV' no encontrado en: $TERRAFORM_DIR"
    echo "Asegúrate de que tus archivos de configuración (.tf) estén en la carpeta '$ENV/'."
    exit 1
fi

# =================================================================
# 1. BUILD LAYER (SendGrid + Deps)
# =================================================================
build_layer() {
    echo ""
    echo "=== BUILDING LAMBDA LAYER ==="

    # Save current directory
    ORIGINAL_DIR=$(pwd)

    # Clean previous layer
    if [ -d "$LAYER_ROOT" ]; then
        echo "→ Cleaning old layer directory..."
        rm -rf "$LAYER_ROOT"
    fi

    echo "→ Creating layer directory: $SITE_PACKAGES"
    mkdir -p "$SITE_PACKAGES"

    # Install dependencies into site-packages
    echo "→ Installing sendgrid==6.12.4 into layer..."
    echo "  Target directory: $SITE_PACKAGES"
    if ! python3 -m pip install --quiet --disable-pip-version-check sendgrid==6.12.4 --target "$SITE_PACKAGES" 2>&1; then
        echo "❌ Error: Failed to install sendgrid"
        cd "$ORIGINAL_DIR" || exit 1
        exit 1
    fi
    echo "  ✅ SendGrid installed successfully"

    # Remove dist-info and test folders
    echo "→ Cleaning unnecessary metadata..."
    find "$SITE_PACKAGES" -type d \( -name "*.dist-info" -o -name "*.egg-info" -o -name "tests" \) -exec rm -rf {} + 2>/dev/null || true

    # Create ZIP
    echo "→ Creating layer ZIP: $LAYER_ZIP"
    mkdir -p "$(dirname "$LAYER_ZIP")"

    if [ -f "$LAYER_ZIP" ]; then
        echo "  Removing existing ZIP file..."
        rm -f "$LAYER_ZIP"
    fi

    # Verify python folder exists before zipping
    if [ ! -d "$LAYER_ROOT/python" ]; then
        echo "❌ Error: Python folder not found at $LAYER_ROOT/python"
        cd "$ORIGINAL_DIR" || exit 1
        exit 1
    fi

    # Create zip from layer directory, only including the python folder
    cd "$LAYER_ROOT" || { echo "❌ Error: Could not change to $LAYER_ROOT"; cd "$ORIGINAL_DIR"; exit 1; }
    
    echo "  Zipping python folder..."
    if ! zip -r "../sendgrid-layer.zip" python > /dev/null 2>&1; then
        echo "❌ Error: Failed to create ZIP file"
        cd "$ORIGINAL_DIR" || exit 1
        exit 1
    fi
    
    cd "$ORIGINAL_DIR" || exit 1
    
    # Move the zip to the correct location
    TEMP_ZIP="$LAYER_ROOT/../sendgrid-layer.zip"
    if [ -f "$TEMP_ZIP" ]; then
        mv "$TEMP_ZIP" "$LAYER_ZIP"
        if [ -f "$LAYER_ZIP" ]; then
            ZIP_SIZE=$(du -h "$LAYER_ZIP" | cut -f1)
            echo "✅ Layer ZIP created successfully: $LAYER_ZIP ($ZIP_SIZE)"
        else
            echo "❌ Error: Failed to move ZIP file to final location"
            exit 1
        fi
    else
        echo "❌ Error: Failed to create layer ZIP - file not found after creation"
        echo "  Expected location: $TEMP_ZIP"
        exit 1
    fi

    echo "✅ Layer built successfully → $LAYER_ZIP"
}

# =================================================================
# 2. PACKAGE LAMBDAS
# =================================================================
build_lambdas() {
    echo ""
    echo "=== PACKAGING LAMBDA FUNCTIONS ==="

    echo "Cambiando directorio temporalmente a: $PACKAGE_SCRIPT_DIR"
    (
        cd "$PACKAGE_SCRIPT_DIR" || { echo "Error fatal: No se pudo cambiar al directorio $PACKAGE_SCRIPT_DIR. Abortando."; exit 1; }
        python3 "$PACKAGE_SCRIPT_NAME"
    )

    if [ $? -ne 0 ]; then
        echo "Error: Falló el empaquetado de las funciones Lambda."
        exit 1
    fi
}

# =================================================================
# MAIN EXECUTION
# =================================================================
echo ""
echo "======================================="
echo "🚀 DEPLOYING ENVIRONMENT: $ENV"
echo "======================================="
echo ""

build_layer
build_lambdas


# =================================================================
# 3. TERRAFORM DEPLOY
# =================================================================
echo ""
echo "=== TERRAFORM DEPLOY ==="
echo "Cambiando directorio de trabajo a: $TERRAFORM_DIR"

cd "$TERRAFORM_DIR" || { echo "Error fatal: No se pudo cambiar al directorio $TERRAFORM_DIR. Abortando."; exit 1; }

echo "→ terraform init"
terraform init
if [ $? -ne 0 ]; then
    echo "Error: Falló el 'terraform init'."
    cd ../..
    exit 1
fi

echo "→ terraform apply"
terraform apply -auto-approve -var-file="$TFVARS_FILE"

if [ $? -ne 0 ]; then
    echo "Proceso detenido: Falló el 'terraform apply'."
    cd ../..
    exit 1
fi

# Get outputs
FRONTEND_BUCKET_NAME=$(terraform output -raw frontend_bucket_name)
API_URL=$(terraform output -raw api_gateway_invoke_url)
COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
WEBSOCKET_URL=$(terraform output -raw websocket_api_endpoint 2>/dev/null || echo "")

if [ $? -ne 0 ]; then
    echo "Error: No se pudieron obtener los outputs de terraform."
    cd ../..
    exit 1
fi

echo ""
echo "--- Terraform Outputs ---"
echo "bucket: $FRONTEND_BUCKET_NAME"
echo "api_url: $API_URL"
echo "pool_id: $COGNITO_USER_POOL_ID"
echo "client_id: $COGNITO_CLIENT_ID"
[ -n "$WEBSOCKET_URL" ] && echo "websocket_url: $WEBSOCKET_URL"

cd ../..

if [ -z "$FRONTEND_BUCKET_NAME" ] || [ -z "$API_URL" ] || [ -z "$COGNITO_USER_POOL_ID" ] || [ -z "$COGNITO_CLIENT_ID" ]; then
    echo "Proceso detenido: Faltan Outputs. Revisa la definición de 'frontend_bucket_name', 'api_gateway_invoke_url', 'cognito_user_pool_id' y 'cognito_user_pool_client_id'."
    exit 1
fi

# =================================================================
# 4. DEPLOY FRONTEND
# =================================================================
echo ""
echo "=== FRONTEND DEPLOY ==="

# Check if websocket URL is available and pass it if it exists
if [ -n "$WEBSOCKET_URL" ]; then
    sh "$DEPLOY_FRONTEND_SCRIPT" "$FRONTEND_BUCKET_NAME" "$API_URL" "$COGNITO_USER_POOL_ID" "$COGNITO_CLIENT_ID" "$WEBSOCKET_URL"
else
    sh "$DEPLOY_FRONTEND_SCRIPT" "$FRONTEND_BUCKET_NAME" "$API_URL" "$COGNITO_USER_POOL_ID" "$COGNITO_CLIENT_ID"
fi

if [ $? -ne 0 ]; then
    echo "🚨 Proceso detenido: Falló el despliegue del frontend."
    exit 1
fi

echo "✅ Frontend deployment complete."

echo ""
echo "=========================================="
echo "🎉 Deployment for environment '$ENV' COMPLETED"
echo "=========================================="
echo ""