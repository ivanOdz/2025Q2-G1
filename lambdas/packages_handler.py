import json
import boto3
import uuid
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from botocore.exceptions import ClientError
import os
from email_templates import get_package_created_template

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# SNS Topic prefix for email-specific topics
SNS_TOPIC_PREFIX = 'fast-track-delivery-notifications-'

# Table references
packages_table = dynamodb.Table('package-tracking-packages')
tracks_table = dynamodb.Table('package-tracking-tracks')
addresses_table = dynamodb.Table('package-tracking-addresses')
users_table = dynamodb.Table('package-tracking-users')

ALLOWED_PRIORITIES = {"NORMAL", "PRIORITY", "HIGH_PRIORITY"}

def normalize_email_for_topic(email):
    """
    Normalize email to create a valid SNS topic name
    SNS topic names can only contain alphanumeric characters, hyphens, and underscores
    """
    # Replace @ with -at- and . with -dot-
    normalized = email.lower().replace('@', '-at-').replace('.', '-dot-')
    normalized = ''.join(c if c.isalnum() or c in ['-', '_'] else '-' for c in normalized)
    return normalized

def get_or_create_topic_for_email(email):
    """
    Get or create a unique SNS topic for a specific email address
    SNS create_topic is idempotent - if topic exists, it returns the existing one
    """
    try:
        if not email or '@' not in email:
            print(f"Invalid email: {email}")
            return None
        
        # Normalize email to create topic name
        topic_name = f"{SNS_TOPIC_PREFIX}{normalize_email_for_topic(email)}"
        
        # SNS create_topic is idempotent - if topic exists, returns existing ARN
        try:
            create_response = sns.create_topic(Name=topic_name)
            topic_arn = create_response['TopicArn']
            print(f"Topic for {email}: {topic_arn}")
            return topic_arn
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'InvalidParameter':
                # Topic name might be too long or invalid, try with hash
                email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
                topic_name = f"{SNS_TOPIC_PREFIX}{email_hash}"
                create_response = sns.create_topic(Name=topic_name)
                topic_arn = create_response['TopicArn']
                print(f"Created topic (with hash) for {email}: {topic_arn}")
                return topic_arn
            else:
                print(f"Error creating topic: {str(e)}")
                return None
        
    except Exception as e:
        print(f"Error getting/creating topic for {email}: {str(e)}")
        return None

def subscribe_email_to_topic(email, topic_arn):
    """
    Subscribe email to SNS topic if not already subscribed
    """
    try:
        # Check if already subscribed
        subscriptions_response = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        already_subscribed = any(
            sub['Protocol'] == 'email' and sub['Endpoint'] == email 
            for sub in subscriptions_response.get('Subscriptions', [])
        )
        
        if not already_subscribed:
            sns.subscribe(
                TopicArn=topic_arn,
                Protocol='email',
                Endpoint=email
            )
            print(f"📧 Subscription request sent to {email}")
        else:
            print(f"✅ {email} is already subscribed")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code not in ['SubscriptionLimitExceeded', 'InvalidParameter']:
            print(f"Warning: Error subscribing email: {str(e)}")

def normalize_priority(value):
    """Normalize priority to canonical values; return None if invalid."""
    if not value:
        return None
    text = str(value).strip().replace("-", "_").upper()
    # common aliases
    aliases = {
        "HIGH PRIORITY": "HIGH_PRIORITY",
        "HIGHPRIORITY": "HIGH_PRIORITY",
    }
    text = aliases.get(text, text)
    return text if text in ALLOWED_PRIORITIES else None

def convert_decimals_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj

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
        body = convert_decimals_to_float(body)
        response['body'] = json.dumps(body)

    return response
    
def lambda_handler(event, context):
    """
    Handle package-related API requests
    Routes: GET /packages/, POST /packages/, GET /packages/{code}/
    """
    
    try:
        user_id = None
        user_role = 'anon'

        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})

        if event.get('requestContext', {}).get('authorizer'):
            claims = event['requestContext']['authorizer']['claims']
            user_id = claims.get('sub')
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
            return create_package(json.loads(event['body']), user_id)

        elif http_method == 'GET' and path_parameters.get('code'):
            # public endpoint
            return get_package_by_code(path_parameters['code'], user_id, user_role)
        
        elif http_method in ('PATCH', 'PUT') and path_parameters.get('code'):
            if user_role == 'anon':
                return cors_response(401, {'error': 'Authentication required'})
            body = json.loads(event.get('body') or '{}')
            return update_package_priority(path_parameters['code'], body, user_id, user_role)

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

def create_package(package_data, user_id):
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
            'priority': normalize_priority(package_data.get('priority')) or 'NORMAL',
            'state': 'CREATED',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Save to DynamoDB
        packages_table.put_item(Item=package_item)
        
        track_item = {
            'track_id': str(uuid.uuid4()),
            'package_id': package_id,
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'CREATE',
            'depot_id': None,
            'comment': "Package created"
        }

        tracks_table.put_item(Item=track_item)

        # Publish to SNS topic specific to receiver email
        receiver_email = package_data['receiver_email']
        if receiver_email and '@' in receiver_email:
            topic_arn = get_or_create_topic_for_email(receiver_email)
            if topic_arn:
                # Subscribe email to topic if not already subscribed
                subscribe_email_to_topic(receiver_email, topic_arn)
                
                # Get frontend URL for tracking link
                frontend_url = os.environ.get('FRONTEND_URL', '')
                tracking_link = f"{frontend_url}/track/{package_code}" if frontend_url else f"Track your package using code: {package_code}"
                
                # Get email template
                subject, message_body = get_package_created_template(
                    receiver_name=package_data.get('receiver_name', ''),
                    package_code=package_code,
                    tracking_link=tracking_link,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                sns.publish(
                    TopicArn=topic_arn,
                    Subject=subject,
                    Message=message_body
                )
                print(f"Notification sent to {receiver_email} for package {package_code}")
            else:
                print(f"Could not create/get topic for {receiver_email}")
        else:
            print(f"Invalid receiver_email: {receiver_email}")
        
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

def update_package_priority(package_code, body, user_id, user_role):
    """Update only the priority of a package (sender or admin)"""
    try:
        # Fetch package (with access check)
        pkg_resp = packages_table.query(
            IndexName='code-index',
            KeyConditionExpression='code = :code',
            ExpressionAttributeValues={':code': package_code}
        )
        if not pkg_resp['Items']:
            return cors_response(404, {'error': 'Package not found'})
        package = pkg_resp['Items'][0]

        # Authorization: admin or sender
        if user_role != 'admin' and package.get('sender_id') != user_id:
            return cors_response(403, {'error': 'Access denied'})

        # Validate priority
        new_priority = normalize_priority(body.get('priority'))
        if not new_priority:
            return cors_response(400, {'error': 'Invalid priority. Allowed: NORMAL, PRIORITY, HIGH_PRIORITY'})

        packages_table.update_item(
            Key={'package_id': package['package_id']},
            UpdateExpression='SET #priority = :priority, updated_at = :updated_at',
            ExpressionAttributeNames={'#priority': 'priority'},
            ExpressionAttributeValues={
                ':priority': new_priority,
                ':updated_at': datetime.utcnow().isoformat()
            }
        )

        package['priority'] = new_priority
        return cors_response(200, {'message': 'Priority updated', 'package': package})

    except Exception as e:
        print(f"Error updating package priority: {str(e)}")
        return cors_response(500, {'error': 'Failed to update package priority'})

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
