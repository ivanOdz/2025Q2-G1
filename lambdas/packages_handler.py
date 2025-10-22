import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError
import os

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Table references
packages_table = dynamodb.Table('package-tracking-packages')
addresses_table = dynamodb.Table('package-tracking-addresses')
users_table = dynamodb.Table('package-tracking-users')

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
        response['body'] = json.dumps(body) if isinstance(body, dict) else str(body)
    
    return response

def lambda_handler(event, context):
    """
    Handle package-related API requests
    Routes: GET /packages/, POST /packages/, GET /packages/{code}/
    """
    
    try:
        user_id = None
        user_email = None
        user_role = 'anon'

        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})

        if event.get('requestContext', {}).get('authorizer'):
            claims = event['requestContext']['authorizer']['claims']
            user_id = claims.get('sub')
            user_email = claims.get('email')
            user_role = claims.get('custom:role', 'user')

        query_parameters = event.get('queryStringParameters', {})
        
        # Route to appropriate handler
        if http_method == 'GET' and not path_parameters:
            if user_role == 'anon':
                return cors_response(401, {'error': 'Authentication required'})
            return get_packages_list(query_parameters, user_id, user_role)

        elif http_method == 'POST' and not path_parameters:
            if user_role == 'anon':
                return cors_response(401, {'error': 'Authentication required'})
            return create_package(json.loads(event['body']), user_id, user_email)

        elif http_method == 'GET' and path_parameters.get('code'):
            # public endpoint
            return get_package_by_code(path_parameters['code'], user_id, user_role)

        else:
            return cors_response(405, {'error': 'Method not allowed'})

    except Exception as e:
        print(f"Error in packages_handler: {str(e)}")
        return cors_response(500, {'error': 'Internal server error'})

def get_packages_list(query_params, user_id, user_role):
    """Get list of packages with optional filtering"""
    try:
        # If user is not admin, only show their packages
        if user_role != 'admin':
            response = packages_table.query(
                IndexName='sender-index',
                KeyConditionExpression='sender_id = :sender_id',
                ExpressionAttributeValues={':sender_id': user_id}
            )
        else:
            # Admin can see all packages
            response = packages_table.scan()
        
        packages = response['Items']
        
        # Convert Decimal to float for JSON serialization
        for package in packages:
            if 'weight' in package and package['weight']:
                package['weight'] = float(package['weight'])
        
        return cors_response(200, packages)
        
    except Exception as e:
        print(f"Error getting packages list: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve packages'})

def create_package(package_data, user_id, user_email):
    """Create a new package"""
    try:
        # Validate required fields
        required_fields = ['origin', 'destination', 'receiver_name', 'receiver_email']
        for field in required_fields:
            if field not in package_data:
                return cors_response(400, {'error': f'Missing required field: {field}'})
        
        # Generate unique package code
        package_code = generate_package_code()
        
        # Create package item
        package_id = str(uuid.uuid4())
        package_item = {
            'package_id': package_id,
            'code': package_code,
            'origin': package_data['origin'],
            'destination': package_data['destination'],
            'sender_id': user_id,
            'receiver_name': package_data['receiver_name'],
            'receiver_email': package_data['receiver_email'],
            'size': package_data.get('size'),
            'weight': Decimal(str(package_data['weight'])) if package_data.get('weight') else None,
            'state': 'CREATED',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Save to DynamoDB
        packages_table.put_item(Item=package_item)
        
        # Publish to SNS for notifications
        sns_message = {
            'package_id': package_id,
            'code': package_code,
            'user_id': user_id,
            'action': 'package_created',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=json.dumps(sns_message),
            Subject='Package Created'
        )
        
        # Convert Decimal to float for response
        if package_item['weight']:
            package_item['weight'] = float(package_item['weight'])
        
        return cors_response(201, package_item)
        
    except Exception as e:
        print(f"Error creating package: {str(e)}")
        return cors_response(500, {'error': str(e)})

def get_package_by_code(package_code, user_id, user_role):
    """Get package details by code"""
    try:
        response = packages_table.query(
            IndexName='code-index',
            KeyConditionExpression='code = :code',
            ExpressionAttributeValues={':code': package_code}
        )
        
        if not response['Items']:
            return cors_response(404, {'error': 'Package not found'})
        
        package = response['Items'][0]

        # check access permissions if user is not 'anon'
        if user_role != 'anon':
            # Check if user has access to this package
            if user_role != 'admin' and package['sender_id'] != user_id:
                return cors_response(403, {'error': 'Access denied'})

        # Convert Decimal to float for response
        if package.get('weight'):
            package['weight'] = float(package['weight'])
        
        return cors_response(200, package)
        
    except Exception as e:
        print(f"Error getting package by code: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve package'})

def generate_package_code():
    """Generate unique 8-digit package code"""
    try:
        # Get the last package to determine next code
        response = packages_table.scan(
            ProjectionExpression='code',
            Limit=1
        )
        
        if not response['Items']:
            # First package
            return '10000000'
        
        # Find the highest code
        max_code = 10000000
        for item in response['Items']:
            try:
                code_num = int(item['code'])
                if code_num > max_code:
                    max_code = code_num
            except ValueError:
                continue
        
        # Generate next code
        next_code = max_code + 1
        
        # Verify code doesn't exist (handle race conditions)
        while True:
            code_str = str(next_code).zfill(8)
            check_response = packages_table.query(
                IndexName='code-index',
                KeyConditionExpression='code = :code',
                ExpressionAttributeValues={':code': code_str}
            )
            
            if not check_response['Items']:
                return code_str
            
            next_code += 1
            
    except Exception as e:
        print(f"Error generating package code: {str(e)}")
        # Fallback to UUID-based code
        return str(uuid.uuid4())[:8].upper()
