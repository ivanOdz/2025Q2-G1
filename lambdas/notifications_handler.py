import json
import boto3
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
apigatewaymanagementapi = boto3.client('apigatewaymanagementapi')

# Table references
websocket_connections_table = dynamodb.Table('package-tracking-websocket-connections')
packages_table = dynamodb.Table('package-tracking-packages')

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
    Handle notifications from SQS queue and WebSocket events
    Processes messages from SNS Topic via SQS and WebSocket connection management
    """
    
    try:
        # Check if this is a WebSocket event
        if 'requestContext' in event and 'routeKey' in event:
            return handle_websocket_event(event, context)
        
        # Check if this is an SQS event
        if 'Records' in event:
            return handle_sqs_event(event, context)
        
        # Unknown event type
        print(f"Unknown event type: {json.dumps(event)}")
        return cors_response(400, {'error': 'Unknown event type'})
        
    except Exception as e:
        print(f"Error in notifications_handler: {str(e)}")
        return cors_response(500, {'error': 'Failed to process event'})

def handle_sqs_event(event, context):
    """Handle SQS messages from SNS Topic"""
    try:
        # Process SQS records
        for record in event['Records']:
            # Parse SNS message
            sns_message = json.loads(record['body'])
            message_data = json.loads(sns_message['Message'])
            
            # Process notification based on action type
            action = message_data.get('action')
            
            if action == 'package_created':
                handle_package_created_notification(message_data)
            elif action == 'package_track_updated':
                handle_track_updated_notification(message_data)
            elif action == 'image_uploaded':
                handle_image_uploaded_notification(message_data)
            else:
                print(f"Unknown action type: {action}")
        
        return cors_response(200, {'message': 'SQS notifications processed successfully'})
        
    except Exception as e:
        print(f"Error handling SQS event: {str(e)}")
        return cors_response(500, {'error': 'Failed to process SQS notifications'})

def handle_websocket_event(event, context):
    """Handle WebSocket events"""
    try:
        route_key = event['requestContext']['routeKey']
        connection_id = event['requestContext']['connectionId']
        
        print(f"WebSocket event - Route: {route_key}, Connection: {connection_id}")
        
        if route_key == '$connect':
            return handle_websocket_connect(event, context)
        elif route_key == '$disconnect':
            return handle_websocket_disconnect(event, context)
        elif route_key == '$default':
            return handle_websocket_message(event, context)
        else:
            print(f"Unknown WebSocket route: {route_key}")
            return cors_response(400, {'error': 'Unknown WebSocket route'})
            
    except Exception as e:
        print(f"Error handling WebSocket event: {str(e)}")
        return cors_response(500, {'error': 'Failed to process WebSocket event'})

def handle_websocket_connect(event, context):
    """Handle WebSocket connection"""
    try:
        connection_id = event['requestContext']['connectionId']
        
        # Extract user info from query parameters (if available)
        query_params = event.get('queryStringParameters', {})
        user_id = query_params.get('user_id', 'anonymous')
        
        # Store connection in DynamoDB
        ttl = int((datetime.now(timezone.utc).timestamp() + 3600))  # 1 hour TTL
        
        websocket_connections_table.put_item(
            Item={
                'connection_id': connection_id,
                'user_id': user_id,
                'connected_at': datetime.now(timezone.utc).isoformat(),
                'ttl': ttl
            }
        )
        
        print(f"WebSocket connection established: {connection_id} for user: {user_id}")
        
        return cors_response(200, {'message': 'Connected'})
        
    except Exception as e:
        print(f"Error handling WebSocket connect: {str(e)}")
        return cors_response(500, {'error': 'Failed to connect'})

def handle_websocket_disconnect(event, context):
    """Handle WebSocket disconnection"""
    try:
        connection_id = event['requestContext']['connectionId']
        
        # Remove connection from DynamoDB
        websocket_connections_table.delete_item(
            Key={'connection_id': connection_id}
        )
        
        print(f"WebSocket connection closed: {connection_id}")
        
        return cors_response(200, {'message': 'Disconnected'})
        
    except Exception as e:
        print(f"Error handling WebSocket disconnect: {str(e)}")
        return cors_response(500, {'error': 'Failed to disconnect'})

def handle_websocket_message(event, context):
    """Handle WebSocket messages"""
    try:
        connection_id = event['requestContext']['connectionId']
        body = json.loads(event.get('body', '{}'))
        
        action = body.get('action')
        
        if action == 'subscribe':
            package_code = body.get('package_code')
            return handle_subscribe_to_package(connection_id, package_code)
        elif action == 'unsubscribe':
            package_code = body.get('package_code')
            return handle_unsubscribe_from_package(connection_id, package_code)
        elif action == 'ping':
            return handle_ping(connection_id)
        else:
            print(f"Unknown WebSocket message action: {action}")
            return cors_response(400, {'error': 'Unknown action'})
            
    except Exception as e:
        print(f"Error handling WebSocket message: {str(e)}")
        return cors_response(500, {'error': 'Failed to process message'})

def handle_subscribe_to_package(connection_id, package_code):
    """Handle subscription to package updates"""
    try:
        # Update connection with package subscription
        websocket_connections_table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='SET package_code = :package_code',
            ExpressionAttributeValues={':package_code': package_code}
        )
        
        print(f"Connection {connection_id} subscribed to package {package_code}")
        
        return cors_response(200, {'message': f'Subscribed to package {package_code}'})
        
    except Exception as e:
        print(f"Error subscribing to package: {str(e)}")
        return cors_response(500, {'error': 'Failed to subscribe'})

def handle_unsubscribe_from_package(connection_id, package_code):
    """Handle unsubscription from package updates"""
    try:
        # Remove package subscription
        websocket_connections_table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='REMOVE package_code'
        )
        
        print(f"Connection {connection_id} unsubscribed from package {package_code}")
        
        return cors_response(200, {'message': f'Unsubscribed from package {package_code}'})
        
    except Exception as e:
        print(f"Error unsubscribing from package: {str(e)}")
        return cors_response(500, {'error': 'Failed to unsubscribe'})

def handle_ping(connection_id):
    """Handle ping message"""
    try:
        # Send pong response
        send_websocket_message(connection_id, {'action': 'pong', 'timestamp': datetime.now(timezone.utc).isoformat()})
        
        return cors_response(200, {'message': 'Pong'})
        
    except Exception as e:
        print(f"Error handling ping: {str(e)}")
        return cors_response(500, {'error': 'Failed to ping'})

def send_websocket_message(connection_id, message):
    """Send message to WebSocket connection"""
    try:
        # Get WebSocket API endpoint from environment
        endpoint = os.environ.get('WEBSOCKET_API_ENDPOINT')
        if not endpoint:
            print("WebSocket API endpoint not configured")
            return False
        
        # Send message via API Gateway Management API
        apigatewaymanagementapi.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        
        print(f"Message sent to connection {connection_id}: {message}")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'GoneException':
            print(f"Connection {connection_id} is gone, removing from database")
            websocket_connections_table.delete_item(Key={'connection_id': connection_id})
        else:
            print(f"Error sending WebSocket message: {str(e)}")
        return False
    except Exception as e:
        print(f"Error sending WebSocket message: {str(e)}")
        return False

def broadcast_to_subscribers(package_code, message):
    """Broadcast message to all subscribers of a package"""
    try:
        # Find all connections subscribed to this package
        response = websocket_connections_table.scan(
            FilterExpression='package_code = :package_code',
            ExpressionAttributeValues={':package_code': package_code}
        )
        
        connections = response.get('Items', [])
        
        for connection in connections:
            connection_id = connection['connection_id']
            send_websocket_message(connection_id, message)
        
        print(f"Broadcasted message to {len(connections)} connections for package {package_code}")
        
    except Exception as e:
        print(f"Error broadcasting to subscribers: {str(e)}")

def handle_package_created_notification(message_data):
    """Handle package creation notification"""
    try:
        package_code = message_data.get('code')
        user_id = message_data.get('user_id')
        timestamp = message_data.get('timestamp')
        
        # Broadcast to WebSocket subscribers
        websocket_message = {
            'action': 'package_created',
            'package_code': package_code,
            'user_id': user_id,
            'timestamp': timestamp,
            'message': f'Package {package_code} has been created'
        }
        
        broadcast_to_subscribers(package_code, websocket_message)
        
        # Log notification
        print(f"Package creation notification sent for package {package_code}")
        
    except Exception as e:
        print(f"Error handling package created notification: {str(e)}")

def handle_track_updated_notification(message_data):
    """Handle track update notification"""
    try:
        package_code = message_data.get('code')
        action = message_data.get('action')
        new_state = message_data.get('new_state')
        timestamp = message_data.get('timestamp')
        
        # Broadcast to WebSocket subscribers
        websocket_message = {
            'action': 'package_track_updated',
            'package_code': package_code,
            'track_action': action,
            'new_state': new_state,
            'timestamp': timestamp,
            'message': f'Package {package_code} status updated to {new_state}'
        }
        
        broadcast_to_subscribers(package_code, websocket_message)
        
        # Log notification
        print(f"Track update notification sent for package {package_code}")
        
    except Exception as e:
        print(f"Error handling track updated notification: {str(e)}")

def handle_image_uploaded_notification(message_data):
    """Handle image upload notification"""
    try:
        package_code = message_data.get('code')
        purpose = message_data.get('purpose')
        timestamp = message_data.get('timestamp')
        user_id = message_data.get('user_id')
        
        # Broadcast to WebSocket subscribers
        websocket_message = {
            'action': 'image_uploaded',
            'package_code': package_code,
            'purpose': purpose,
            'user_id': user_id,
            'timestamp': timestamp,
            'message': f'Image uploaded for package {package_code}'
        }
        
        broadcast_to_subscribers(package_code, websocket_message)
        
        # Log notification
        print(f"Image upload notification sent for package {package_code}")
        
    except Exception as e:
        print(f"Error handling image uploaded notification: {str(e)}")

def log_notification(notification_type, data):
    """Log notification for audit purposes"""
    try:
        # You can implement logging to CloudWatch, DynamoDB, or another service
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': notification_type,
            'data': data
        }
        
        print(f"Notification logged: {json.dumps(log_entry)}")
        
    except Exception as e:
        print(f"Error logging notification: {str(e)}")
