#!/usr/bin/env python3

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

GIT_REPO_URL = "https://github.com/julietaTechenski/CLOUD-TP-frontend"
FRONTEND_DIR = "CLOUD-TP-frontend"

def handle_remove_read_only(func, path, exc):
    # Verifica si la función es de eliminación (os.rmdir o os.remove) y si el archivo/directorio es de solo lectura.
    if func in (os.rmdir, os.remove) and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR) # Cambiar permisos a escritura para el usuario
        try:
            func(path) # Reintentar la función de eliminación
        except Exception:
            # Si el reintento falla, que el código llamador lo maneje.
            raise
    else:
        raise # Volver a lanzar el error si es otro tipo de problema

def safe_remove_directory(dir_path):
    """Elimina un directorio de manera segura, usando un controlador de errores para solucionar problemas de permisos en Windows."""
    if not os.path.exists(dir_path):
        return True
    
    try:
        # Usar el controlador de errores para gestionar archivos de solo lectura
        shutil.rmtree(dir_path, onerror=handle_remove_read_only)
        return True
    except Exception as e:
        print(f"Error CRÍTICO al eliminar {dir_path}: {e}")
        # Si falla incluso con el manejador de errores, salimos con una advertencia severa.
        return False

def main():
    if len(sys.argv) != 3:
        print("Error: Faltan argumentos. Se requiere el nombre del bucket y la URL del API Gateway.")
        sys.exit(1)

    frontend_bucket_name = sys.argv[1]
    api_arn = sys.argv[2]
    
    # Convertir ARN de API Gateway a URL HTTP
    # Formato ARN: arn:aws:execute-api:region:account:api-id/*
    # Formato URL: https://api-id.execute-api.region.amazonaws.com/stage
    if api_arn.startswith("arn:aws:execute-api:"):
        parts = api_arn.split(":")
        region = parts[3]
        account = parts[4]
        api_id = parts[5].split("/")[0]  # Tomar solo la parte antes del /
        api_url = f"http://{api_id}.execute-api.{region}.amazonaws.com"
        print(f"ARN convertido a URL: {api_arn} -> {api_url}")
    else:
        # Si ya es una URL, usarla tal como está
        api_url = api_arn
        print(f"Usando URL directamente: {api_url}")

    if not frontend_bucket_name or not api_url:
        print("Error: Faltan argumentos. Se requiere el nombre del bucket y la URL del API Gateway.")
        sys.exit(1)

    print("-> 1. Verificando y obteniendo la aplicación Frontend desde Git...")

    # Eliminar directorio si existe (con manejo de errores de Windows)
    safe_remove_directory(FRONTEND_DIR)

    # Clonar el repositorio
    result = subprocess.run(["git", "clone", GIT_REPO_URL], check=False, shell=True)
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
    
    # Construir la URL final para el frontend
    final_api_url = f"{api_url}/api"
    filtered_lines.append(f"REACT_APP_API_URL={final_api_url}\n")
    
    print(f"Escribiendo en {env_file}: REACT_APP_API_URL={final_api_url}")

    # Escribir el archivo modificado
    with open(env_file, 'w') as f:
        f.writelines(filtered_lines)

    print("-> 3. Instalando dependencias y construyendo la aplicación (React)...")
    
    # Instalar dependencias
    result = subprocess.run(["npm", "install"], check=False, shell=True)
    if result.returncode != 0:
        print("Error: Falló la instalación de dependencias.")
        os.chdir(original_dir)
        sys.exit(1)

    # Construir la aplicación
    result = subprocess.run(["npm", "run", "build"], check=False, shell=True)
    if result.returncode != 0:
        print("Error: Falló la construcción del Frontend. Abortando.")
        os.chdir(original_dir)
        sys.exit(1)

    print(f"-> 4. Sincronizando el contenido de 'build/' con s3://{frontend_bucket_name}...")
    
    # Sincronizar con S3
    result = subprocess.run(["aws", "s3", "sync", "build/", f"s3://{frontend_bucket_name}", "--delete"], check=False, shell=True)
    sync_status = result.returncode

    print("-> 5. Limpieza de archivos locales...")
    
    os.chdir(original_dir)
    
    if not safe_remove_directory(FRONTEND_DIR):
        print(f"ERROR: No se pudo eliminar completamente el directorio clonado: {FRONTEND_DIR}")

    if sync_status == 0:
        print(f"Despliegue de Frontend en S3 completado en s3://{frontend_bucket_name}")
        print("Limpieza de archivos locales completada.")
        sys.exit(0)
    else:
        print("Error en el despliegue a S3. Revisa tus credenciales y permisos.")
        sys.exit(1)

if __name__ == "__main__":
    main()
