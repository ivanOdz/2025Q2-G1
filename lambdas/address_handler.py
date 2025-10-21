import json
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Table references
addresses_table = dynamodb.Table('package-tracking-addresses')

def lambda_handler(event, context):
    """
    Handle address-related API requests
    Routes: GET /addresses/, POST /addresses/, GET /addresses/{id}/
    """
    
    try:
        # Extract user information from Cognito JWT
        user_id = event['requestContext']['authorizer']['claims']['sub']
        user_email = event['requestContext']['authorizer']['claims']['email']
        user_role = event['requestContext']['authorizer']['claims'].get('custom:role', 'user')
        
        # Parse HTTP method and path
        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})
        
        # Route to appropriate handler
        if http_method == 'GET' and not path_parameters:
            return get_addresses_list()
        elif http_method == 'POST' and not path_parameters:
            return create_address(json.loads(event['body']))
        elif http_method == 'GET' and path_parameters.get('id'):
            return get_address_by_id(path_parameters['id'])
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Error in address_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_addresses_list():
    """Get list of all addresses"""
    try:
        response = addresses_table.scan()
        addresses = response['Items']
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(addresses)
        }
        
    except Exception as e:
        print(f"Error getting addresses list: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to retrieve addresses'})
        }

def create_address(address_data):
    """Create a new address"""
    try:
        # Validate required fields
        required_fields = ['street', 'number', 'city', 'province', 'zip_code']
        for field in required_fields:
            if field not in address_data:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Create address item
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
        
        # Save to DynamoDB
        addresses_table.put_item(Item=address_item)
        
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(address_item)
        }
        
    except Exception as e:
        print(f"Error creating address: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to create address'})
        }

def get_address_by_id(address_id):
    """Get address details by ID"""
    try:
        response = addresses_table.get_item(
            Key={'address_id': address_id}
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Address not found'})
            }
        
        address = response['Item']
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(address)
        }
        
    except Exception as e:
        print(f"Error getting address by ID: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to retrieve address'})
        }
