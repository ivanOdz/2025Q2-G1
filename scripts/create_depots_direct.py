#!/usr/bin/env python3
"""
Script para crear 3 depots con direcciones completas usando AWS SDK directamente
Ejecutar desde el directorio raíz del proyecto
"""

import boto3
import uuid
import os
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

def get_aws_session():
    """Obtener sesión de AWS con validación de credenciales"""
    try:
        # Intentar crear una sesión
        session = boto3.Session()
        
        # Verificar que las credenciales estén disponibles
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✅ Credenciales AWS válidas encontradas")
        print(f"   Account ID: {identity['Account']}")
        print(f"   User/Role: {identity['Arn']}")
        print(f"   Region: {session.region_name or 'No especificada'}")
        
        return session
        
    except NoCredentialsError:
        print("❌ Error: No se encontraron credenciales de AWS")
        print("\n📋 Opciones para configurar credenciales:")
        print("   1. Variables de entorno:")
        print("      export AWS_ACCESS_KEY_ID='tu-access-key'")
        print("      export AWS_SECRET_ACCESS_KEY='tu-secret-key'")
        print("      export AWS_DEFAULT_REGION='us-east-1'")
        print("\n   2. AWS CLI:")
        print("      aws configure")
        print("\n   3. Perfil específico:")
        print("      export AWS_PROFILE='mi-perfil'")
        return None
        
    except ClientError as e:
        print(f"❌ Error de credenciales AWS: {str(e)}")
        return None

# Configuración de AWS
print("🔐 Verificando credenciales AWS...")
session = get_aws_session()

if not session:
    print("\n❌ No se pueden obtener credenciales válidas. Abortando.")
    exit(1)

dynamodb = session.resource('dynamodb')

# Referencias a las tablas
addresses_table = dynamodb.Table('package-tracking-addresses')
depots_table = dynamodb.Table('package-tracking-depots')

def get_or_create_address_direct(address_data):
    """Crear una dirección directamente en DynamoDB, o devolverla si ya existe"""
    try:
        # Buscar si ya existe una dirección con estos datos
        response = addresses_table.scan(
            FilterExpression='street = :street AND #number = :number AND apartment = :apartment AND city = :city AND province = :province AND zip_code = :zip_code',
            ExpressionAttributeNames={'#number': 'number'},
            ExpressionAttributeValues={
                ':street': address_data['street'],
                ':number': address_data['number'],
                ':apartment': address_data.get('apartment'),
                ':city': address_data['city'],
                ':province': address_data['province'],
                ':zip_code': address_data['zip_code']
            }
        )
        
        if response['Items']:
            # La dirección ya existe
            existing_address = response['Items'][0]
            print(f"   ⚠️  Dirección ya existe: {existing_address['address_id']}")
            return existing_address, False
        
        # Crear nueva dirección
        address_id = str(uuid.uuid4())
        address_item = {
            'address_id': address_id,
            'street': address_data['street'],
            'number': address_data['number'],
            'apartment': address_data.get('apartment'),
            'city': address_data['city'],
            'province': address_data['province'],
            'zip_code': address_data['zip_code'],
            'details': address_data.get('details'),
            'created_at': datetime.utcnow().isoformat()
        }
        
        addresses_table.put_item(Item=address_item)
        return address_item, True
        
    except Exception as e:
        print(f"Error creando/buscando dirección: {str(e)}")
        return None, False

def get_or_create_depot_direct(depot_data):
    """Crear un depot directamente en DynamoDB, o devolverlo si ya existe"""
    try:
        # Buscar si ya existe un depot con este nombre
        response = depots_table.scan(
            FilterExpression='#name = :name',
            ExpressionAttributeNames={'#name': 'name'},
            ExpressionAttributeValues={':name': depot_data['name']}
        )
        
        if response['Items']:
            # El depot ya existe
            existing_depot = response['Items'][0]
            print(f"   ⚠️  Depot ya existe: {existing_depot['depot_id']}")
            return existing_depot, False
        
        # Crear nuevo depot
        depot_id = str(uuid.uuid4())
        depot_item = {
            'depot_id': depot_id,
            'name': depot_data['name'],
            'address_id': depot_data['address_id'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        depots_table.put_item(Item=depot_item)
        return depot_item, True
        
    except Exception as e:
        print(f"Error creando/buscando depot: {str(e)}")
        return None, False

def main():
    """Función principal para crear los depots"""
    
    print("🚀 Iniciando creación de depots (modo directo DynamoDB)...")
    
    # Datos de los 3 depots con sus direcciones (basado en el comando Django)
    depots_data = [
        {
            "name": "Av. Libertador",
            "address": {
                "street": "Av. Libertador",
                "number": "1234",
                "apartment": "1",
                "city": "CABA",
                "province": "CABA",
                "zip_code": "1234",
                "details": "depot location"
            }
        },
        {
            "name": "La Libertad",
            "address": {
                "street": "La Libertad",
                "number": "1234",
                "apartment": "1",
                "city": "CABA",
                "province": "CABA",
                "zip_code": "1234",
                "details": "depot location"
            }
        },
        {
            "name": "Av. Anza",
            "address": {
                "street": "Av. Anza",
                "number": "1234",
                "apartment": "1",
                "city": "CABA",
                "province": "CABA",
                "zip_code": "1234",
                "details": "depot location"
            }
        }
    ]
    
    created_addresses = []
    created_depots = []
    
    try:
        # Crear direcciones
        print("🏠 Creando direcciones...")
        for i, depot_info in enumerate(depots_data, 1):
            print(f"\n📦 Procesando depot {i}/3: {depot_info['name']}")
            
            # 1. Crear o obtener la dirección
            print(f"   🏠 Procesando dirección...")
            address, address_created = get_or_create_address_direct(depot_info['address'])
            
            if not address:
                print(f"   ❌ Error procesando dirección para {depot_info['name']}")
                continue
            
            if address_created:
                print(f"   ✅ Dirección creada: {address['address_id']}")
            else:
                print(f"   ✅ Dirección encontrada: {address['address_id']}")
            
            created_addresses.append(address)
            
            # 2. Crear o obtener el depot
            print(f"   🏢 Procesando depot...")
            depot_data = {
                "name": depot_info['name'],
                "address_id": address['address_id']
            }
            
            depot, depot_created = get_or_create_depot_direct(depot_data)
            
            if not depot:
                print(f"   ❌ Error procesando depot {depot_info['name']}")
                continue
            
            if depot_created:
                print(f"   ✅ Depot creado: {depot['depot_id']}")
            else:
                print(f"   ✅ Depot encontrado: {depot['depot_id']}")
            
            created_depots.append({
                "depot": depot,
                "address": address,
                "created": depot_created
            })
    
        # Resumen final
        print(f"\n🎉 Resumen de creación:")
        print(f"   ✅ Direcciones procesadas: {len(created_addresses)}/3")
        print(f"   ✅ Depots procesados: {len(created_depots)}/3")
        
        if created_depots:
            print(f"\n📋 Detalles de los depots:")
            for i, item in enumerate(created_depots, 1):
                depot = item['depot']
                address = item['address']
                created = item['created']
                status = "🆕 Creado" if created else "♻️  Existía"
                
                print(f"\n   Depot {i}: {depot['name']} ({status})")
                print(f"   ├─ Depot ID: {depot['depot_id']}")
                print(f"   ├─ Address ID: {address['address_id']}")
                print(f"   ├─ Dirección: {address['street']} {address['number']}")
                print(f"   ├─ Apartamento: {address['apartment']}")
                print(f"   ├─ Ciudad: {address['city']}, {address['province']}")
                print(f"   ├─ Código Postal: {address['zip_code']}")
                print(f"   └─ Detalles: {address['details']}")
        
        print(f"\n✨ Script completado!")
        
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {str(e)}")
        print("   Algunos depots pueden haberse creado parcialmente.")

if __name__ == "__main__":
    main()
