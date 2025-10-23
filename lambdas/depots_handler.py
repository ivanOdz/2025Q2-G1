import json
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Table references
depots_table = dynamodb.Table('package-tracking-depots')
addresses_table = dynamodb.Table('package-tracking-addresses')

def cors_response(status_code, body=None):
    """
    Create a CORS-enabled response
    """
    response = {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
    }
    
    if body is not None:
        response['body'] = json.dumps(body)
    
    return response

def lambda_handler(event, context):
    """
    Handle depot-related API requests
    Routes: GET /depots/, POST /depots/, GET /depots/{id}/
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
            return get_depots_list()
        elif http_method == 'POST' and not path_parameters:
            return create_depot(json.loads(event['body']))
        elif http_method == 'GET' and path_parameters.get('id'):
            return get_depot_by_id(path_parameters['id'])
        else:
            return cors_response(405, {'error': 'Method not allowed'})
            
    except Exception as e:
        print(f"Error in depots_handler: {str(e)}")
        return cors_response(500, {'error': 'Internal server error'})

def get_depots_list():
    """Get list of all depots with address details"""
    try:
        response = depots_table.scan()
        depots = response['Items']
        
        # Enrich with address details
        enriched_depots = []
        for depot in depots:
            if depot.get('address_id'):
                address_response = addresses_table.get_item(
                    Key={'address_id': depot['address_id']}
                )
                if 'Item' in address_response:
                    depot['address_detail'] = address_response['Item']
            
            enriched_depots.append(depot)
        
        return cors_response(200, enriched_depots)
        
    except Exception as e:
        print(f"Error getting depots list: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve depots'})

def create_depot(depot_data):
    """Create a new depot"""
    try:
        # Validate required fields
        required_fields = ['name', 'address_id']
        for field in required_fields:
            if field not in depot_data:
                return cors_response(400, {'error': f'Missing required field: {field}'})
        
        # Verify address exists
        address_response = addresses_table.get_item(
            Key={'address_id': depot_data['address_id']}
        )
        
        if 'Item' not in address_response:
            return cors_response(400, {'error': 'Address not found'})
        
        # Create depot item
        depot_id = str(uuid.uuid4())
        depot_item = {
            'depot_id': depot_id,
            'name': depot_data['name'],
            'address_id': depot_data['address_id'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Save to DynamoDB
        depots_table.put_item(Item=depot_item)
        
        # Add address details to response
        depot_item['address_detail'] = address_response['Item']
        
        return cors_response(201, depot_item)
        
    except Exception as e:
        print(f"Error creating depot: {str(e)}")
        return cors_response(500, {'error': 'Failed to create depot'})

def get_depot_by_id(depot_id):
    """Get depot details by ID"""
    try:
        response = depots_table.get_item(
            Key={'depot_id': depot_id}
        )
        
        if 'Item' not in response:
            return cors_response(404, {'error': 'Depot not found'})
        
        depot = response['Item']
        
        # Add address details
        if depot.get('address_id'):
            address_response = addresses_table.get_item(
                Key={'address_id': depot['address_id']}
            )
            if 'Item' in address_response:
                depot['address_detail'] = address_response['Item']
        
        return cors_response(200, depot)
        
    except Exception as e:
        print(f"Error getting depot by ID: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve depot'})
