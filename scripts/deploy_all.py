#!/usr/bin/env python3

import sys
import os
import subprocess
from pathlib import Path

# =================================================================
# USO: Se debe ejecutar desde la Carpeta Raíz del Proyecto:
#      python scripts/deploy_all.py <dev|prod>

def main():
    if len(sys.argv) != 2:
        print("Error: Debe especificar el entorno (dev o prod) como argumento.")
        print("Uso: python scripts/deploy_all.py <dev|prod>")
        sys.exit(1)

    env = sys.argv[1]
    terraform_dir = f"envs/{env}"
    tfvars_file = f"{env}.tfvars"

    deploy_frontend_script = "./scripts/deploy_frontend.py"

    if not os.path.isdir(terraform_dir):
        print(f"Error: Directorio de Terraform para el entorno '{env}' no encontrado en: {terraform_dir}")
        print(f"Asegúrate de que tus archivos de configuración (.tf) estén en la carpeta '{env}/'.")
        sys.exit(1)

    print("=== 1. PREPARACIÓN: Empaquetado del Backend (Lambda) ===")
    
    # Cambiar al directorio 'lambdas', ejecutar el empaquetado y volver al original
    original_dir = os.getcwd()
    try:
        os.chdir("lambdas")
        result = subprocess.run(["python", "script.py"], check=False)
    finally:
        os.chdir(original_dir)
    if result.returncode != 0:
        print("Error: Falló el empaquetado de las funciones Lambda.")
        sys.exit(1)

    print("\n=== 2. DESPLIEGUE DE INFRAESTRUCTURA (Terraform) ===")
    print(f"Cambiando directorio de trabajo a: {terraform_dir}")
    
    # Cambiar al directorio de terraform
    original_dir = os.getcwd()
    try:
        os.chdir(terraform_dir)
    except OSError:
        print(f"Error fatal: No se pudo cambiar al directorio {terraform_dir}. Abortando.")
        sys.exit(1)

    print("Ejecutando 'terraform init'...")
    result = subprocess.run(["terraform", "init"], check=False, shell=True)
    if result.returncode != 0:
        print("Error: Falló el 'terraform init'.")
        os.chdir(original_dir)
        sys.exit(1)

    print("Ejecutando 'terraform apply'...")
    result = subprocess.run(["terraform", "apply", "-auto-approve", f"-var-file={tfvars_file}"], check=False, shell=True)
    if result.returncode != 0:
        print("Proceso detenido: Falló el 'terraform apply'.")
        os.chdir(original_dir)
        sys.exit(1)

    # Obtener outputs de terraform
    try:
        frontend_bucket_result = subprocess.run(["terraform", "output", "-raw", "frontend_bucket_name"], 
                                              capture_output=True, text=True, check=True, shell=True)
        frontend_bucket_name = frontend_bucket_result.stdout.strip()
        
        api_url_result = subprocess.run(["terraform", "output", "-raw", "api_gateway_execution_arn"], 
                                      capture_output=True, text=True, check=True, shell=True)
        api_url = api_url_result.stdout.strip()
        
        cognito_user_pool_id_result = subprocess.run(["terraform", "output", "-raw", "cognito_user_pool_id"], 
                                                    capture_output=True, text=True, check=True, shell=True)
        cognito_user_pool_id = cognito_user_pool_id_result.stdout.strip()
        
        cognito_client_id_result = subprocess.run(["terraform", "output", "-raw", "cognito_user_pool_client_id"], 
                                                capture_output=True, text=True, check=True, shell=True)
        cognito_client_id = cognito_client_id_result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: No se pudieron obtener los outputs de terraform.")
        os.chdir(original_dir)
        sys.exit(1)

    print(f"FRONTEND_BUCKET_NAME: {frontend_bucket_name}")
    print(f"API_URL: {api_url}")
    print(f"COGNITO_USER_POOL_ID: {cognito_user_pool_id}")
    print(f"COGNITO_CLIENT_ID: {cognito_client_id}")

    # Volver al directorio original
    os.chdir(original_dir)

    if not frontend_bucket_name or not api_url or not cognito_user_pool_id or not cognito_client_id:
        print("Proceso detenido: Faltan Outputs. Revisa la definición de 'frontend_bucket_name', 'api_gateway_execution_arn', 'cognito_user_pool_id' y 'cognito_user_pool_client_id'.")
        sys.exit(1)

    print("\n=== 3. DESPLIEGUE DEL CONTENIDO (Frontend S3) ===")
    result = subprocess.run(["python", deploy_frontend_script, frontend_bucket_name, api_url, cognito_user_pool_id, cognito_client_id], check=False, shell=True)
    if result.returncode != 0:
        print("🚨 Proceso detenido: Falló el despliegue del frontend.")
        sys.exit(1)

    print("\n==========================================")
    print(f"🎉 Despliegue de Entorno {env} COMPLETADO 🎉")
    print("==========================================")

if __name__ == "__main__":
    main()
