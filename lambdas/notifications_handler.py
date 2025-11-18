import json
import boto3
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
apigatewaymanagementapi = boto3.client('apigatewaymanagementapi')
sns = boto3.client('sns')

# Table references
websocket_connections_table = dynamodb.Table('package-tracking-websocket-connections')
packages_table = dynamodb.Table('package-tracking-packages')

# Configuration
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
SNS_TOPIC_PREFIX = 'fast-track-delivery-notifications-'

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

def normalize_email_for_topic(email):
    """
    Normalize email to create a valid SNS topic name
    SNS topic names can only contain alphanumeric characters, hyphens, and underscores
    """
    # Replace @ with -at- and . with -dot-
    normalized = email.lower().replace('@', '-at-').replace('.', '-dot-')
    # Remove any invalid characters
    normalized = ''.join(c if c.isalnum() or c in ['-', '_'] else '-' for c in normalized)
    return normalized

def get_or_create_topic_for_email(email):
    """
    Get or create a unique SNS topic for a specific email address
    This ensures each email only receives notifications for their own packages
    
    SNS create_topic is idempotent - if topic exists, it returns the existing one
    """
    try:
        # Normalize email to create topic name
        topic_name = f"{SNS_TOPIC_PREFIX}{normalize_email_for_topic(email)}"
        
        # SNS create_topic is idempotent - if topic exists, returns existing ARN
        # If it doesn't exist, creates it. This is more efficient than listing all topics
        try:
            create_response = sns.create_topic(Name=topic_name)
            topic_arn = create_response['TopicArn']
            print(f"✅ Topic for {email}: {topic_arn}")
            return topic_arn
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'InvalidParameter':
                # Topic name might be too long or invalid, try with hash
                import hashlib
                email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
                topic_name = f"{SNS_TOPIC_PREFIX}{email_hash}"
                create_response = sns.create_topic(Name=topic_name)
                topic_arn = create_response['TopicArn']
                print(f"Created topic (with hash) for {email}: {topic_arn}")
                return topic_arn
            elif error_code == 'AuthorizationError':
                print(f"No permission to create SNS topic. LabRole may need sns:CreateTopic permission")
                raise
            else:
                print(f"Error creating topic: {str(e)}")
                raise
        
    except Exception as e:
        print(f"Error getting/creating topic for {email}: {str(e)}")
        return None

def send_email_via_sns(email, subject, message_body):
    """
    Send email notification via SNS using a dedicated topic per email
    This ensures each email only receives notifications for their own packages
    """
    try:
        if not email or '@' not in email:
            print(f"Invalid email: {email}")
            return False
        
        # Get or create topic for this specific email
        topic_arn = get_or_create_topic_for_email(email)
        if not topic_arn:
            print(f"Could not get/create topic for {email}")
            return False
        
        # Subscribe email to topic (if not already subscribed)
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
                print(f"Subscription request sent to {email} - user must confirm via email")
            else:
                # Check if subscription is confirmed
                for sub in subscriptions_response.get('Subscriptions', []):
                    if sub['Protocol'] == 'email' and sub['Endpoint'] == email:
                        if sub['SubscriptionArn'] == 'PendingConfirmation':
                            print(f"Subscription for {email} is pending confirmation")
                        else:
                            print(f"{email} is already subscribed and confirmed")
                        break
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code not in ['SubscriptionLimitExceeded', 'InvalidParameter']:
                print(f"Error subscribing email: {str(e)}")
        
        sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message_body
        )
        
        print(f"✅ Email notification published to SNS topic for {email}: {subject}")
        return True
        
    except Exception as e:
        print(f"Error sending email via SNS: {str(e)}")
        return False

def handle_package_created_notification(message_data):
    """Handle package creation notification"""
    try:
        package_code = message_data.get('code')
        user_id = message_data.get('user_id')
        timestamp = message_data.get('timestamp')
        
        # Get package to find receiver email (destinatario)
        receiver_email = None
        receiver_name = None
        try:
            package_response = packages_table.query(
                IndexName='code-index',
                KeyConditionExpression='code = :code',
                ExpressionAttributeValues={':code': package_code}
            )
            if package_response['Items']:
                package = package_response['Items'][0]
                receiver_email = package.get('receiver_email')
                receiver_name = package.get('receiver_name')
                print(f"Package {package_code} - Receiver: {receiver_name} ({receiver_email})")
            else:
                print(f"Package {package_code} not found in database")
        except Exception as e:
            print(f"Error fetching package: {str(e)}")
        
        # Send email notification ONLY to receiver (destinatario)
        if receiver_email and '@' in receiver_email:
            subject = f"Paquete {package_code} en Camino - FastTrack Delivery"
            greeting = f"Hola {receiver_name}," if receiver_name else "Hola,"
            message = f"""
{greeting}

Tienes un paquete en camino hacia ti.

Código de Paquete: {package_code}
Estado: Creado y listo para envío
Fecha: {timestamp}

Puedes hacer seguimiento de tu paquete en cualquier momento usando el código de rastreo.
            """
            print(f"📧 Sending notification to receiver: {receiver_email} for package {package_code}")
            send_email_via_sns(receiver_email, subject, message)
        else:
            if not receiver_email:
                print(f"No receiver_email found for package {package_code}, skipping email notification")
            else:
                print(f"Invalid receiver_email format for package {package_code}: {receiver_email}")
        
        # Broadcast to WebSocket subscribers
        websocket_message = {
            'action': 'package_created',
            'package_code': package_code,
            'user_id': user_id,
            'timestamp': timestamp,
            'message': f'Package {package_code} has been created'
        }
        
        broadcast_to_subscribers(package_code, websocket_message)
        
        print(f"Package creation notification sent for package {package_code}")
        
    except Exception as e:
        print(f"Error handling package created notification: {str(e)}")

def handle_track_updated_notification(message_data):
    """Handle track update notification"""
    try:
        package_code = message_data.get('code')
        action = message_data.get('track_action') or message_data.get('action')
        new_state = message_data.get('new_state')
        timestamp = message_data.get('timestamp')
        
        # Get package to find receiver email (destinatario)
        receiver_email = None
        receiver_name = None
        try:
            package_response = packages_table.query(
                IndexName='code-index',
                KeyConditionExpression='code = :code',
                ExpressionAttributeValues={':code': package_code}
            )
            if package_response['Items']:
                package = package_response['Items'][0]
                receiver_email = package.get('receiver_email')
                receiver_name = package.get('receiver_name')
                print(f"Package {package_code} - Receiver: {receiver_name} ({receiver_email})")
            else:
                print(f"Package {package_code} not found in database")
        except Exception as e:
            print(f"Error fetching package: {str(e)}")
        
        # Determine notification message based on state
        greeting = f"Hola {receiver_name}," if receiver_name else "Hola,"
        
        if new_state == 'DELIVERED':
            subject = f"¡Paquete {package_code} Entregado! - FastTrack Delivery"
            message = f"""
{greeting}

¡Tu paquete {package_code} ha sido entregado exitosamente!

Código de Paquete: {package_code}
Estado: Entregado
Fecha: {timestamp}

Gracias por usar FastTrack Delivery.
            """
        elif new_state == 'CANCELLED':
            subject = f"Paquete {package_code} Cancelado - FastTrack Delivery"
            message = f"""
{greeting}

El envío del paquete {package_code} ha sido cancelado.

Código de Paquete: {package_code}
Estado: Cancelado
Fecha: {timestamp}

Si tienes preguntas, por favor contacta con el remitente.
            """
        else:
            subject = f"Paquete {package_code} - Actualización de Estado"
            action_map = {
                'SEND_DEPOT': 'Enviado al Depósito',
                'ARRIVED_DEPOT': 'Llegó al Depósito',
                'SEND_FINAL': 'Enviado a Destino Final',
                'ARRIVED_FINAL': 'Llegó al Destino Final'
            }
            action_display = action_map.get(action, action)
            message = f"""
{greeting}

El estado de tu paquete {package_code} ha sido actualizado.

Código de Paquete: {package_code}
Acción: {action_display}
Estado: {new_state}
Fecha: {timestamp}

Puedes hacer seguimiento de tu paquete en cualquier momento.
            """
        
        # Send email notification ONLY to receiver (destinatario)
        if receiver_email and '@' in receiver_email:
            print(f"📧 Sending notification to receiver: {receiver_email} for package {package_code}")
            send_email_via_sns(receiver_email, subject, message)
        else:
            if not receiver_email:
                print(f"No receiver_email found for package {package_code}, skipping email notification")
            else:
                print(f"Invalid receiver_email format for package {package_code}: {receiver_email}")
        
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
