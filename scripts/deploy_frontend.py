#!/usr/bin/env python3

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

GIT_REPO_URL = "https://github.com/julietaTechenski/CLOUD-TP-frontend"
FRONTEND_DIR = "CLOUD-TP-frontend"

def main():
    if len(sys.argv) != 3:
        print("Error: Faltan argumentos. Se requiere el nombre del bucket y la URL del API Gateway.")
        sys.exit(1)

    frontend_bucket_name = sys.argv[1]
    api_url = sys.argv[2]

    if not frontend_bucket_name or not api_url:
        print("Error: Faltan argumentos. Se requiere el nombre del bucket y la URL del API Gateway.")
        sys.exit(1)

    print("-> 1. Verificando y obteniendo la aplicación Frontend desde Git...")

    # Eliminar directorio si existe
    if os.path.exists(FRONTEND_DIR):
        shutil.rmtree(FRONTEND_DIR)

    # Clonar el repositorio
    result = subprocess.run(["git", "clone", GIT_REPO_URL], check=False)
    if result.returncode != 0:
        print("Error: Falló el git clone. Abortando.")
        sys.exit(1)

    # Cambiar al directorio clonado
    original_dir = os.getcwd()
    try:
        os.chdir(FRONTEND_DIR)
    except OSError:
        print("Error fatal: No se pudo acceder al directorio clonado. Abortando.")
        sys.exit(1)

    print("-> 2. Inyectando URL de API Gateway en .env.production...")
    env_file = ".env.production"
    
    # Leer el archivo .env.production
    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {env_file}")
        os.chdir(original_dir)
        sys.exit(1)

    # Filtrar líneas que no contengan REACT_APP_API_URL y agregar la nueva
    filtered_lines = [line for line in lines if not line.startswith("REACT_APP_API_URL=")]
    filtered_lines.append(f"REACT_APP_API_URL={api_url}/api\n")

    # Escribir el archivo modificado
    with open(env_file, 'w') as f:
        f.writelines(filtered_lines)

    print("-> 3. Instalando dependencias y construyendo la aplicación (React)...")
    
    # Instalar dependencias
    result = subprocess.run(["npm", "install"], check=False)
    if result.returncode != 0:
        print("Error: Falló la instalación de dependencias.")
        os.chdir(original_dir)
        sys.exit(1)

    # Construir la aplicación
    result = subprocess.run(["npm", "run", "build"], check=False)
    if result.returncode != 0:
        print("Error: Falló la construcción del Frontend. Abortando.")
        os.chdir(original_dir)
        sys.exit(1)

    print(f"-> 4. Sincronizando el contenido de 'build/' con s3://{frontend_bucket_name}...")
    
    # Sincronizar con S3
    result = subprocess.run(["aws", "s3", "sync", "build/", f"s3://{frontend_bucket_name}", "--delete"], check=False)
    sync_status = result.returncode

    print("-> 5. Limpieza de archivos locales...")
    
    # Volver al directorio original
    os.chdir(original_dir)
    
    # Eliminar el directorio clonado
    shutil.rmtree(FRONTEND_DIR)

    if sync_status == 0:
        print(f"Despliegue de Frontend en S3 completado en s3://{frontend_bucket_name}")
        print("Limpieza de archivos locales completada.")
        sys.exit(0)
    else:
        print("Error en el despliegue a S3. Revisa tus credenciales y permisos.")
        sys.exit(1)

if __name__ == "__main__":
    main()
