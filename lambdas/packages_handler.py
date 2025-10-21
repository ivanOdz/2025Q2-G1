import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Table references
packages_table = dynamodb.Table('package-tracking-packages')
addresses_table = dynamodb.Table('package-tracking-addresses')
users_table = dynamodb.Table('package-tracking-users')

def lambda_handler(event, context):
    """
    Handle package-related API requests
    Routes: GET /packages/, POST /packages/, GET /packages/{code}/
    """
    
    try:
        # Extract user information from Cognito JWT
        user_id = event['requestContext']['authorizer']['claims']['sub']
        user_email = event['requestContext']['authorizer']['claims']['email']
        user_role = event['requestContext']['authorizer']['claims'].get('custom:role', 'user')
        
        # Parse HTTP method and path
        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {})
        
        # Route to appropriate handler
        if http_method == 'GET' and not path_parameters:
            return get_packages_list(query_parameters, user_id, user_role)
        elif http_method == 'POST' and not path_parameters:
            return create_package(json.loads(event['body']), user_id, user_email)
        elif http_method == 'GET' and path_parameters.get('code'):
            return get_package_by_code(path_parameters['code'], user_id, user_role)
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Error in packages_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }

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
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(packages)
        }
        
    except Exception as e:
        print(f"Error getting packages list: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to retrieve packages'})
        }

def create_package(package_data, user_id, user_email):
    """Create a new package"""
    try:
        # Validate required fields
        required_fields = ['origin', 'destination', 'receiver_name', 'receiver_email']
        for field in required_fields:
            if field not in package_data:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
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
        
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(package_item)
        }
        
    except Exception as e:
        print(f"Error creating package: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to create package'})
        }

def get_package_by_code(package_code, user_id, user_role):
    """Get package details by code"""
    try:
        response = packages_table.query(
            IndexName='code-index',
            KeyConditionExpression='code = :code',
            ExpressionAttributeValues={':code': package_code}
        )
        
        if not response['Items']:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Package not found'})
            }
        
        package = response['Items'][0]
        
        # Check if user has access to this package
        if user_role != 'admin' and package['sender_id'] != user_id:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Access denied'})
            }
        
        # Convert Decimal to float for response
        if package.get('weight'):
            package['weight'] = float(package['weight'])
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(package)
        }
        
    except Exception as e:
        print(f"Error getting package by code: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to retrieve package'})
        }

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
