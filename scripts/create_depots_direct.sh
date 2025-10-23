#!/bin/bash

# Script para crear depots - Versión directa DynamoDB
# Asegúrate de tener AWS CLI configurado con las credenciales correctas

echo "🚀 Creando depots usando DynamoDB directamente..."

# Verificar que AWS CLI esté configurado
echo "🔐 Verificando credenciales AWS..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ Error: AWS CLI no está configurado o las credenciales no son válidas"
    echo ""
    echo "📋 Opciones para configurar credenciales:"
    echo "   1. AWS CLI (recomendado):"
    echo "      aws configure"
    echo ""
    echo "   2. Variables de entorno:"
    echo "      export AWS_ACCESS_KEY_ID='tu-access-key'"
    echo "      export AWS_SECRET_ACCESS_KEY='tu-secret-key'"
    echo "      export AWS_DEFAULT_REGION='us-east-1'"
    echo ""
    echo "   3. Perfil específico:"
    echo "      export AWS_PROFILE='mi-perfil'"
    exit 1
fi

# Mostrar información de la cuenta actual
echo "✅ Credenciales AWS válidas encontradas:"
aws sts get-caller-identity --query 'Account' --output text | sed 's/^/   Account ID: /'
aws sts get-caller-identity --query 'Arn' --output text | sed 's/^/   User/Role: /'
aws configure get region | sed 's/^/   Region: /'

# Verificar que las tablas existan
echo "🔍 Verificando tablas de DynamoDB..."
if ! aws dynamodb describe-table --table-name package-tracking-addresses > /dev/null 2>&1; then
    echo "❌ Error: Tabla 'package-tracking-addresses' no existe"
    exit 1
fi

if ! aws dynamodb describe-table --table-name package-tracking-depots > /dev/null 2>&1; then
    echo "❌ Error: Tabla 'package-tracking-depots' no existe"
    exit 1
fi

echo "✅ Tablas verificadas correctamente"

# Ejecutar el script Python
echo ""
echo "📦 Ejecutando script de creación de depots..."
echo "   Los siguientes depots se crearán:"
echo "   ├─ Av. Libertador (Av. Libertador 1234, Apartamento 1, CABA)"
echo "   ├─ La Libertad (La Libertad 1234, Apartamento 1, CABA)"
echo "   └─ Av. Anza (Av. Anza 1234, Apartamento 1, CABA)"
echo ""

if python3 scripts/create_depots_direct.py; then
    echo ""
    echo "✅ Script completado exitosamente!"
else
    echo ""
    echo "❌ El script falló. Revisa los errores arriba."
    exit 1
fi
