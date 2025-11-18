import json
import boto3
import uuid
import os
import hashlib
from datetime import datetime
from botocore.exceptions import ClientError
from email_templates import (
    get_package_delivered_template,
    get_package_cancelled_template,
    get_package_status_update_template
)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# SNS Topic prefix for email-specific topics
SNS_TOPIC_PREFIX = 'fast-track-delivery-notifications-'

# Table references
tracks_table = dynamodb.Table('package-tracking-tracks')
packages_table = dynamodb.Table('package-tracking-packages')
depots_table = dynamodb.Table('package-tracking-depots')
addresses_table = dynamodb.Table('package-tracking-addresses')

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
        
        topic_name = f"{SNS_TOPIC_PREFIX}{normalize_email_for_topic(email)}"
        
        # SNS create_topic is idempotent - if topic exists, returns existing ARN
        try:
            create_response = sns.create_topic(Name=topic_name)
            topic_arn = create_response['TopicArn']
            print(f"✅ Topic for {email}: {topic_arn}")
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
            print(f"Subscription request sent to {email}")
        else:
            print(f"{email} is already subscribed")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code not in ['SubscriptionLimitExceeded', 'InvalidParameter']:
            print(f"Warning: Error subscribing email: {str(e)}")

def normalize_priority(value):
    if not value:
        return None
    text = str(value).strip().replace("-", "_").upper()
    aliases = {
        "HIGH PRIORITY": "HIGH_PRIORITY",
        "HIGHPRIORITY": "HIGH_PRIORITY",
    }
    text = aliases.get(text, text)
    return text if text in ALLOWED_PRIORITIES else None

def convert_decimals_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    from decimal import Decimal
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
    Handle track-related API requests
    Routes: GET /packages/{code}/tracks/, POST /packages/{code}/tracks/, GET /packages/{code}/tracks/latest/
    """
    
    try:
        # Extract user information from Cognito JWT (if available)
        user_id = None
        user_email = None
        user_role = 'anon'
        
        if event.get('requestContext', {}).get('authorizer'):
            claims = event['requestContext']['authorizer']['claims']
            user_id = claims.get('sub')
            user_email = claims.get('email')
            user_role = claims.get('custom:role', 'user')
        
        # Parse HTTP method and path
        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})
        
        # Get package code from path
        package_code = path_parameters.get('code')
        if not package_code:
            return cors_response(400, {'error': 'Package code is required'})
        
        # Route to appropriate handler
        if 'scan' in event.get('path', ''):
            if http_method == 'GET':
                # GET scan info requires authentication (to check if user is admin)
                if user_role == 'anon':
                    return cors_response(401, {'error': 'Authentication required'})
                return get_scan_info(package_code)
            elif http_method == 'POST':
                # POST scan requires authentication and admin role
                if user_role == 'anon':
                    return cors_response(401, {'error': 'Authentication required'})
                return handle_qr_scan(package_code, user_id, user_role)
            else:
                return cors_response(405, {'error': 'Method not allowed'})
        elif http_method == 'GET' and 'latest' in event.get('path', ''):
            return get_latest_track(package_code, user_id, user_role)
        elif http_method == 'GET':
            return get_tracks_list(package_code, user_id, user_role)
        elif http_method == 'POST':
            return create_track(package_code, json.loads(event['body']), user_id, user_role)
        else:
            return cors_response(405, {'error': 'Method not allowed'})
            
    except Exception as e:
        print(f"Error in tracks_handler: {str(e)}")
        return cors_response(500, {'error': 'Internal server error'})

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
        
        return cors_response(200, tracks)
        
    except Exception as e:
        print(f"Error getting tracks list: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve tracks'})

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
            return cors_response(404, {'error': 'No tracks found for this package'})
        
        # Get the latest track
        latest_track = max(tracks, key=lambda x: x['timestamp'])
        
        return cors_response(200, latest_track)
        
    except Exception as e:
        print(f"Error getting latest track: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve latest track'})

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
            return cors_response(400, {'error': 'Action is required'})
        
        action = track_data['action']
        
        # Validate state transition
        can_transition, message = can_transition_to(current_state, action)
        if not can_transition:
            return cors_response(400, {'error': message})

        # Normalize and validate optional priority
        normalized_priority = None
        if 'priority' in track_data and track_data.get('priority') is not None:
            normalized_priority = normalize_priority(track_data.get('priority'))
            if normalized_priority is None:
                return cors_response(400, {'error': 'Invalid priority. Allowed: NORMAL, PRIORITY, HIGH_PRIORITY'})
        
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
        # Optional priority change recorded in track
        if normalized_priority:
            track_item['priority'] = normalized_priority
        
        # Save track to DynamoDB
        tracks_table.put_item(Item=track_item)
        
        # Update package state
        new_state = get_new_state(current_state, action)
        update_expr = ['#state = :state', 'updated_at = :updated_at']
        expr_attr_names = {'#state': 'state'}
        expr_attr_values = {
            ':state': new_state,
            ':updated_at': datetime.utcnow().isoformat()
        }
        # If a priority is provided, persist it on the package
        if normalized_priority:
            update_expr.append('#priority = :priority')
            expr_attr_names['#priority'] = 'priority'
            expr_attr_values[':priority'] = normalized_priority

        packages_table.update_item(
            Key={'package_id': package_id},
            UpdateExpression='SET ' + ', '.join(update_expr),
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
        
        # Publish to SNS topic specific to receiver email
        receiver_email = package_data.get('receiver_email')
        receiver_name = package_data.get('receiver_name')
        
        if receiver_email and '@' in receiver_email:
            topic_arn = get_or_create_topic_for_email(receiver_email)
            if topic_arn:
                # Subscribe email to topic if not already subscribed
                subscribe_email_to_topic(receiver_email, topic_arn)
                
                # Get depot name if depot_id exists
                depot_name = None
                depot_id = track_item.get('depot_id')
                if depot_id:
                    try:
                        depot_response = depots_table.get_item(Key={'depot_id': depot_id})
                        if 'Item' in depot_response:
                            depot_name = depot_response['Item'].get('name')
                    except Exception as e:
                        print(f"Warning: Could not retrieve depot name: {str(e)}")
                
                # Get email template based on state
                timestamp = datetime.utcnow().isoformat()
                
                if new_state == 'DELIVERED':
                    subject, message_body = get_package_delivered_template(
                        receiver_name=receiver_name,
                        package_code=package_code,
                        timestamp=timestamp
                    )
                elif new_state == 'CANCELLED':
                    subject, message_body = get_package_cancelled_template(
                        receiver_name=receiver_name,
                        package_code=package_code,
                        timestamp=timestamp
                    )
                else:
                    subject, message_body = get_package_status_update_template(
                        receiver_name=receiver_name,
                        package_code=package_code,
                        action=action,
                        depot_name=depot_name,
                        new_state=new_state,
                        timestamp=timestamp
                    )
                
                sns.publish(
                    TopicArn=topic_arn,
                    Subject=subject,
                    Message=message_body
                )
                print(f"Notification sent to {receiver_email} for package {package_code} - {action}")
            else:
                print(f"Could not create/get topic for {receiver_email}")
        else:
            print(f"Invalid or missing receiver_email for package {package_code}")
        
        return cors_response(201, track_item)
        
    except Exception as e:
        print(f"Error creating track: {str(e)}")
        return cors_response(500, {'error': 'Failed to create track'})

def get_package_by_code(package_code, user_id, user_role):
    """Get package by code with access control"""
    try:
        response = packages_table.query(
            IndexName='code-index',
            KeyConditionExpression='code = :code',
            ExpressionAttributeValues={':code': package_code}
        )
        
        if not response['Items']:
            return cors_response(404, {'error': 'Package not found'})
        
        package = response['Items'][0]
        
        # Check if user has access to this package
        # For public endpoints (like track lookup), allow anonymous access
        if user_role != 'anon' and user_role != 'admin' and package['sender_id'] != user_id:
            return cors_response(403, {'error': 'Access denied'})
        
        return cors_response(200, package)
        
    except Exception as e:
        print(f"Error getting package by code: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve package'})

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

def get_scan_info(package_code):
    """Get scan information for QR code - what action can be performed"""
    try:
        # Get package
        package = get_package_by_code(package_code, None, 'anon')
        if package['statusCode'] != 200:
            return package
        
        package_data = json.loads(package['body'])
        current_state = package_data['state']
        
        # Get latest track
        package_id = package_data['package_id']
        tracks_response = tracks_table.query(
            IndexName='package-index',
            KeyConditionExpression='package_id = :package_id',
            ExpressionAttributeValues={':package_id': package_id}
        )
        
        tracks = tracks_response['Items']
        if not tracks:
            return cors_response(200, {
                'can_auto_confirm': False,
                'current_state': current_state,
                'message': 'No tracks found for this package'
            })
        
        latest_track = max(tracks, key=lambda x: x['timestamp'])
        last_action = latest_track.get('action')
        depot_id = latest_track.get('depot_id')
        
        # Get depot name if depot_id exists
        depot_name = None
        if depot_id:
            try:
                depot_response = depots_table.get_item(Key={'depot_id': depot_id})
                if 'Item' in depot_response:
                    depot_name = depot_response['Item'].get('name')
            except Exception as e:
                print(f"Warning: Could not retrieve depot name: {str(e)}")
        
        # Determine if we can auto-confirm
        can_auto_confirm = False
        suggested_action = None
        message = ""
        
        if current_state == 'IN_TRANSIT':
            if last_action == 'SEND_DEPOT':
                can_auto_confirm = True
                suggested_action = 'ARRIVED_DEPOT'
                if depot_name:
                    message = f"Package is on the way to depot '{depot_name}'. Scan to confirm arrival."
                else:
                    message = "Package is on the way to a depot. Scan to confirm arrival."
            elif last_action == 'SEND_FINAL':
                can_auto_confirm = True
                suggested_action = 'ARRIVED_FINAL'
                # Get destination address for final delivery
                destination_address = None
                if package_data.get('destination'):
                    try:
                        dest_response = addresses_table.get_item(Key={'address_id': package_data['destination']})
                        if 'Item' in dest_response:
                            dest_addr = dest_response['Item']
                            destination_address = f"{dest_addr.get('street', '')} {dest_addr.get('number', '')}, {dest_addr.get('city', '')}"
                    except Exception as e:
                        print(f"Warning: Could not retrieve destination address: {str(e)}")
                
                if destination_address:
                    message = f"Package is on the way to final destination: {destination_address}. Scan to confirm delivery."
                else:
                    message = "Package is on the way to final destination. Scan to confirm delivery."
        elif current_state == 'ON_HOLD':
            if depot_name:
                message = f"Package is at depot '{depot_name}'. Please use the management interface to select next destination."
            else:
                message = "Package is at a depot. Please use the management interface to select next destination."
        elif current_state == 'CREATED':
            message = "Package is ready to be sent. Please use the management interface to select destination."
        elif current_state == 'DELIVERED':
            message = "Package has already been delivered."
        elif current_state == 'CANCELLED':
            message = "Package delivery has been cancelled."
        
        return cors_response(200, {
            'can_auto_confirm': can_auto_confirm,
            'current_state': current_state,
            'suggested_action': suggested_action,
            'last_action': last_action,
            'depot_id': latest_track.get('depot_id'),
            'message': message
        })
        
    except Exception as e:
        print(f"Error getting scan info: {str(e)}")
        return cors_response(500, {'error': 'Failed to get scan information'})

def handle_qr_scan(package_code, user_id, user_role):
    """Handle QR code scan - auto-confirm arrival if package is in transit"""
    try:
        # Only admins can scan QR codes to update package status
        if user_role != 'admin':
            return cors_response(403, {'error': 'Only administrators can scan QR codes to update package status'})
        
        # Get scan info first
        scan_info_response = get_scan_info(package_code)
        if scan_info_response['statusCode'] != 200:
            return scan_info_response
        
        scan_info = json.loads(scan_info_response['body'])
        
        # Only auto-confirm if package is in transit
        if not scan_info.get('can_auto_confirm'):
            return cors_response(400, {
                'error': 'Cannot auto-confirm',
                'message': scan_info.get('message', 'Package is not in transit'),
                'current_state': scan_info.get('current_state')
            })
        
        suggested_action = scan_info.get('suggested_action')
        depot_id = scan_info.get('depot_id')
        
        # Create track with auto-confirmation
        track_data = {
            'action': suggested_action,
            'comment': f'Auto-confirmed via QR scan by admin at {datetime.utcnow().isoformat()}',
        }
        
        if depot_id and suggested_action == 'ARRIVED_DEPOT':
            track_data['depot_id'] = depot_id
        
        # Use create_track function with admin user
        return create_track(package_code, track_data, user_id, user_role)
        
    except Exception as e:
        print(f"Error handling QR scan: {str(e)}")
        return cors_response(500, {'error': 'Failed to process QR scan'})
