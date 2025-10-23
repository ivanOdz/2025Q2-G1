import boto3
import requests
import getpass
import sys
import json
import subprocess
import os
from botocore.exceptions import ClientError, NoCredentialsError

# --- Configuración
AWS_REGION = "us-east-1"
API_NAME = "fast-track-delivery-serverless-api"
ROLE_TO_SET = "admin"


def get_terraform_output(output_name, env_dir="envs/dev"):
    """
    Get a Terraform output value - compatible with Windows, Mac, and Linux
    """
    try:
        # Get the script directory and build terraform path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        terraform_dir = os.path.join(project_root, env_dir)
        
        if not os.path.exists(terraform_dir):
            print(f"❌ ERROR: Terraform directory '{terraform_dir}' not found.", file=sys.stderr)
            return None
            
        # Run terraform output command - cross-platform compatible
        cmd = ["terraform", "output", "-raw", output_name]
        
        # Use shell=True on Windows for better compatibility
        shell_mode = os.name == 'nt'  # 'nt' = Windows
        
        result = subprocess.run(
            cmd,
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=True,
            shell=shell_mode
        )
        
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Failed to get Terraform output '{output_name}': {e.stderr}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("❌ ERROR: Terraform not found. Make sure Terraform is installed and in your PATH.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ ERROR: Unexpected error getting Terraform output: {e}", file=sys.stderr)
        return None


def main():
    print("--- Script de Promoción de Admin (Python) ---")
    print()

    try:
        user_email = input("Email del usuario a promover: ")
        user_password = getpass.getpass("Password del usuario (no se mostrará): ")
        
        # Automatically get Cognito Client ID from Terraform outputs
        print("\nObteniendo Cognito Client ID desde Terraform...")
        cognito_client_id = get_terraform_output("cognito_user_pool_client_id")
        
        if not cognito_client_id:
            print("❌ ERROR: No se pudo obtener el Cognito Client ID desde Terraform.", file=sys.stderr)
            print("Asegúrate de que:", file=sys.stderr)
            print("  - El entorno 'dev' esté desplegado (terraform apply)", file=sys.stderr)
            print("  - Terraform esté instalado y en tu PATH", file=sys.stderr)
            print("  - Tengas permisos para ejecutar terraform output", file=sys.stderr)
            sys.exit(1)
            
        print(f"✅ Cognito Client ID obtenido: {cognito_client_id}")

        if not all([user_email, user_password]):
            print("\n❌ ERROR: Email y Password son obligatorios.", file=sys.stderr)
            sys.exit(1)

        # --- 2. Encontrar el API ID automáticamente ---
        print(f"\nBuscando API ID para '{API_NAME}' en la región {AWS_REGION}...")
        apigw_client = boto3.client('apigateway', region_name=AWS_REGION)

        api_id = None
        paginator = apigw_client.get_paginator('get_rest_apis')
        for page in paginator.paginate():
            for item in page.get('items', []):
                if item['name'] == API_NAME:
                    api_id = item['id']
                    break
            if api_id:
                break

        if not api_id:
            print(f"❌ ERROR: No se pudo encontrar el API Gateway con el nombre '{API_NAME}'.", file=sys.stderr)
            print("Verifica el nombre de la API o la región.", file=sys.stderr)
            sys.exit(1)

        print(f"✅ API ID encontrado: {api_id}")

        # --- 3. Obtener el IdToken ---
        print("\nAutenticando con Cognito para obtener el IdToken...")
        cognito_client = boto3.client('cognito-idp', region_name=AWS_REGION)

        # Usamos 'initiate_auth' como lo pediste
        auth_response = cognito_client.initiate_auth(
            ClientId=cognito_client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': user_email,
                'PASSWORD': user_password
            }
        )

        id_token = auth_response.get('AuthenticationResult', {}).get('IdToken')

        if not id_token:
            print("❌ ERROR: No se pudo obtener el IdToken.", file=sys.stderr)
            sys.exit(1)

        print("✅ IdToken obtenido.")

        # --- 4. Llamar al endpoint para cambiar el rol ---
        api_url = f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/api/change-role"
        headers = {
            'Authorization': f'Bearer {id_token}',
            'Content-Type': 'application/json'
        }
        payload = {'role': ROLE_TO_SET}

        print(f"\nLlamando al endpoint para cambiar el rol a '{ROLE_TO_SET}'...")

        response = requests.post(api_url, headers=headers, data=json.dumps(payload))

        # --- 5. Verificar el resultado ---
        response.raise_for_status()  # Lanza un error si el HTTP status es 4xx o 5xx

        print(f"\n🎉 ¡ÉXITO! (HTTP {response.status_code})")
        print(f"El rol del usuario {user_email} fue cambiado a '{ROLE_TO_SET}'.")

    except ClientError as e:
        # Manejo de errores comunes de AWS
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'NotAuthorizedException':
            print("\n❌ ERROR DE AUTENTICACIÓN: Password o Email incorrecto.", file=sys.stderr)
        elif error_code == 'UserNotFoundException':
            print(f"\n❌ ERROR DE USUARIO: El usuario '{user_email}' no existe.", file=sys.stderr)
        else:
            print(f"\n❌ ERROR DE AWS (Boto3): {e}", file=sys.stderr)
        sys.exit(1)

    except NoCredentialsError:
        print("\n❌ ERROR: No se encontraron credenciales de AWS.", file=sys.stderr)
        print("Por favor, ejecuta 'aws configure' primero.", file=sys.stderr)
        sys.exit(1)

    except requests.exceptions.HTTPError as e:
        # Manejo de errores de la API (4xx, 5xx)
        print(f"\n❌ ¡ERROR! El servidor respondió con HTTP {e.response.status_code}.", file=sys.stderr)
        print(f"Respuesta: {e.response.text}", file=sys.stderr)
        print("Revisa los logs de CloudWatch para la Lambda.", file=sys.stderr)
        sys.exit(1)

    except requests.exceptions.RequestException as e:
        # Manejo de errores de red (ej. no se puede conectar)
        print(f"\n❌ ERROR DE RED: No se pudo conectar a la API. {e}", file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
        sys.exit(1)


if __name__ == "__main__":
    main()