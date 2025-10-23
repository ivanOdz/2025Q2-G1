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
    Routes: GET /depots/, GET /depots/{id}/
    """
    
    try:
        print(f"DEBUG: Received event: {json.dumps(event, default=str)}")
        
        # Extract user information from Cognito JWT
        if not event.get('requestContext', {}).get('authorizer'):
            print("ERROR: No authorizer found in request context")
            return cors_response(401, {'error': 'Authentication required'})
        
        claims = event['requestContext']['authorizer']['claims']
        user_id = claims.get('sub')
        user_email = claims.get('email')
        user_role = claims.get('custom:role', 'user')
        
        print(f"DEBUG: User info - ID: {user_id}, Email: {user_email}, Role: {user_role}")
        
        # Parse HTTP method and path
        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})
        
        print(f"DEBUG: HTTP Method: {http_method}, Path Parameters: {path_parameters}")
        
        # Route to appropriate handler
        if http_method == 'GET' and not path_parameters:
            print("DEBUG: Routing to get_depots_list")
            return get_depots_list()
        elif http_method == 'GET' and path_parameters.get('id'):
            print(f"DEBUG: Routing to get_depot_by_id with ID: {path_parameters['id']}")
            return get_depot_by_id(path_parameters['id'])
        else:
            print(f"DEBUG: No matching route for {http_method} with path_parameters: {path_parameters}")
            return cors_response(405, {'error': 'Method not allowed'})
            
    except Exception as e:
        print(f"ERROR: Unexpected error in lambda_handler: {str(e)}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})

def get_depots_list():
    """Get list of all depots with address details"""
    try:
        print("DEBUG: Starting get_depots_list")
        
        # Check if tables exist and are accessible
        try:
            response = depots_table.scan()
            print(f"DEBUG: Depots table scan successful, found {len(response['Items'])} items")
        except Exception as table_error:
            print(f"ERROR: Failed to scan depots table: {str(table_error)}")
            return cors_response(500, {'error': f'Database error: {str(table_error)}'})
        
        depots = response['Items']
        
        # Enrich with address details
        enriched_depots = []
        for depot in depots:
            if depot.get('address_id'):
                try:
                    address_response = addresses_table.get_item(
                        Key={'address_id': depot['address_id']}
                    )
                    if 'Item' in address_response:
                        depot['address_detail'] = address_response['Item']
                        print(f"DEBUG: Added address details for depot {depot.get('name', 'unknown')}")
                    else:
                        print(f"WARNING: Address not found for depot {depot.get('name', 'unknown')} with address_id {depot['address_id']}")
                except Exception as addr_error:
                    print(f"ERROR: Failed to get address for depot {depot.get('name', 'unknown')}: {str(addr_error)}")
                    # Continue without address details rather than failing completely
            
            enriched_depots.append(depot)
        
        print(f"DEBUG: Returning {len(enriched_depots)} enriched depots")
        return cors_response(200, enriched_depots)
        
    except Exception as e:
        print(f"ERROR: Unexpected error in get_depots_list: {str(e)}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})


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
