import json
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Table references
tracks_table = dynamodb.Table('package-tracking-tracks')
packages_table = dynamodb.Table('package-tracking-packages')
depots_table = dynamodb.Table('package-tracking-depots')

def lambda_handler(event, context):
    """
    Handle track-related API requests
    Routes: GET /packages/{code}/tracks/, POST /packages/{code}/tracks/, GET /packages/{code}/tracks/latest/
    """
    
    try:
        # Extract user information from Cognito JWT
        user_id = event['requestContext']['authorizer']['claims']['sub']
        user_email = event['requestContext']['authorizer']['claims']['email']
        user_role = event['requestContext']['authorizer']['claims'].get('custom:role', 'user')
        
        # Parse HTTP method and path
        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})
        
        # Get package code from path
        package_code = path_parameters.get('code')
        if not package_code:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Package code is required'})
            }
        
        # Route to appropriate handler
        if http_method == 'GET' and 'latest' in event.get('path', ''):
            return get_latest_track(package_code, user_id, user_role)
        elif http_method == 'GET':
            return get_tracks_list(package_code, user_id, user_role)
        elif http_method == 'POST':
            return create_track(package_code, json.loads(event['body']), user_id, user_role)
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Error in tracks_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_tracks_list(package_code, user_id, user_role):
    """Get complete track history for a package"""
    try:
        # First, get the package to verify access
        package = get_package_by_code(package_code, user_id, user_role)
        if package['statusCode'] != 200:
            return package
        
        package_data = json.loads(package['body'])
        package_id = package_data['package_id']
        
        # Get all tracks for this package
        response = tracks_table.query(
            IndexName='package-index',
            KeyConditionExpression='package_id = :package_id',
            ExpressionAttributeValues={':package_id': package_id}
        )
        
        tracks = response['Items']
        
        # Sort by timestamp
        tracks.sort(key=lambda x: x['timestamp'])
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(tracks)
        }
        
    except Exception as e:
        print(f"Error getting tracks list: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to retrieve tracks'})
        }

def get_latest_track(package_code, user_id, user_role):
    """Get the latest track for a package"""
    try:
        # First, get the package to verify access
        package = get_package_by_code(package_code, user_id, user_role)
        if package['statusCode'] != 200:
            return package
        
        package_data = json.loads(package['body'])
        package_id = package_data['package_id']
        
        # Get all tracks for this package
        response = tracks_table.query(
            IndexName='package-index',
            KeyConditionExpression='package_id = :package_id',
            ExpressionAttributeValues={':package_id': package_id}
        )
        
        tracks = response['Items']
        
        if not tracks:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No tracks found for this package'})
            }
        
        # Get the latest track
        latest_track = max(tracks, key=lambda x: x['timestamp'])
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(latest_track)
        }
        
    except Exception as e:
        print(f"Error getting latest track: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to retrieve latest track'})
        }

def create_track(package_code, track_data, user_id, user_role):
    """Create a new track event"""
    try:
        # First, get the package to verify access
        package = get_package_by_code(package_code, user_id, user_role)
        if package['statusCode'] != 200:
            return package
        
        package_data = json.loads(package['body'])
        package_id = package_data['package_id']
        current_state = package_data['state']
        
        # Validate required fields
        if 'action' not in track_data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Action is required'})
            }
        
        action = track_data['action']
        
        # Validate state transition
        can_transition, message = can_transition_to(current_state, action)
        if not can_transition:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': message})
            }
        
        # Create track item
        track_id = str(uuid.uuid4())
        track_item = {
            'track_id': track_id,
            'package_id': package_id,
            'action': action,
            'depot_id': track_data.get('depot_id'),
            'comment': track_data.get('comment', ''),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save track to DynamoDB
        tracks_table.put_item(Item=track_item)
        
        # Update package state
        new_state = get_new_state(current_state, action)
        packages_table.update_item(
            Key={'package_id': package_id},
            UpdateExpression='SET #state = :state, updated_at = :updated_at',
            ExpressionAttributeNames={'#state': 'state'},
            ExpressionAttributeValues={
                ':state': new_state,
                ':updated_at': datetime.utcnow().isoformat()
            }
        )
        
        # Publish to SNS for notifications
        sns_message = {
            'package_id': package_id,
            'code': package_code,
            'track_id': track_id,
            'action': action,
            'new_state': new_state,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=json.dumps(sns_message),
            Subject='Package Track Updated'
        )
        
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(track_item)
        }
        
    except Exception as e:
        print(f"Error creating track: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Failed to create track'})
        }

def get_package_by_code(package_code, user_id, user_role):
    """Get package by code with access control"""
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

def can_transition_to(current_state, action):
    """Validate if state transition is allowed"""
    transitions = {
        'CREATED': ['SEND_DEPOT', 'SEND_FINAL', 'CANCEL'],
        'IN_TRANSIT': ['ARRIVED_DEPOT', 'ARRIVED_FINAL', 'CANCEL'],
        'ON_HOLD': ['SEND_FINAL', 'SEND_DEPOT', 'CANCEL'],
        'DELIVERED': [],
        'CANCELLED': []
    }
    
    if current_state not in transitions:
        return False, "Invalid current state"
    
    if action not in transitions[current_state]:
        if current_state == 'DELIVERED':
            return False, "The package has already been delivered"
        elif current_state == 'CANCELLED':
            return False, "No transitions are allowed for cancelled packages"
        else:
            return False, f"Invalid transition from {current_state} to {action}"
    
    return True, "Valid transition"

def get_new_state(current_state, action):
    """Get new state based on action"""
    state_mapping = {
        'SEND_DEPOT': 'IN_TRANSIT',
        'ARRIVED_DEPOT': 'ON_HOLD',
        'SEND_FINAL': 'IN_TRANSIT',
        'ARRIVED_FINAL': 'DELIVERED',
        'CANCEL': 'CANCELLED'
    }
    
    return state_mapping.get(action, current_state)
