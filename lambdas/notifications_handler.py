import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
ses = boto3.client('ses')  # For email notifications
sns = boto3.client('sns')  # For SMS notifications (if needed)

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
    Handle notifications from SQS queue
    Processes messages from SNS Topic via SQS
    """
    
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
        
        return cors_response(200, {'message': 'Notifications processed successfully'})
        
    except Exception as e:
        print(f"Error in notifications_handler: {str(e)}")
        return cors_response(500, {'error': 'Failed to process notifications'})

def handle_package_created_notification(message_data):
    """Handle package creation notification"""
    try:
        package_code = message_data.get('code')
        user_id = message_data.get('user_id')
        timestamp = message_data.get('timestamp')
        
        # Get user email from Cognito or DynamoDB
        user_email = get_user_email(user_id)
        
        if user_email:
            # Send email notification
            subject = f"Package Created - {package_code}"
            body = f"""
            Your package has been created successfully!
            
            Package Code: {package_code}
            Created At: {timestamp}
            
            You can track your package using the code above.
            
            Best regards,
            Package Tracking System
            """
            
            send_email_notification(user_email, subject, body)
        
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
        
        # Get package details to find receiver email
        receiver_email = get_receiver_email(package_code)
        
        if receiver_email:
            # Send email notification to receiver
            subject = f"Package Update - {package_code}"
            body = f"""
            Your package status has been updated!
            
            Package Code: {package_code}
            Action: {action}
            New Status: {new_state}
            Updated At: {timestamp}
            
            You can track your package using the code above.
            
            Best regards,
            Package Tracking System
            """
            
            send_email_notification(receiver_email, subject, body)
        
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
        
        # Get user email from the uploader
        user_id = message_data.get('user_id')
        user_email = get_user_email(user_id)
        
        if user_email:
            # Send email notification
            subject = f"Image Uploaded - Package {package_code}"
            body = f"""
            An image has been uploaded for your package!
            
            Package Code: {package_code}
            Purpose: {purpose}
            Uploaded At: {timestamp}
            
            You can view the image in your package details.
            
            Best regards,
            Package Tracking System
            """
            
            send_email_notification(user_email, subject, body)
        
        # Log notification
        print(f"Image upload notification sent for package {package_code}")
        
    except Exception as e:
        print(f"Error handling image uploaded notification: {str(e)}")

def get_user_email(user_id):
    """Get user email from Cognito or DynamoDB"""
    try:
        # In a real implementation, you would:
        # 1. Query Cognito to get user details
        # 2. Or query DynamoDB users table
        # For now, return a placeholder
        return f"user_{user_id}@example.com"
    except Exception as e:
        print(f"Error getting user email: {str(e)}")
        return None

def get_receiver_email(package_code):
    """Get receiver email from package data"""
    try:
        # Query DynamoDB to get package details
        dynamodb = boto3.resource('dynamodb')
        packages_table = dynamodb.Table('package-tracking-packages')
        
        response = packages_table.query(
            IndexName='code-index',
            KeyConditionExpression='code = :code',
            ExpressionAttributeValues={':code': package_code}
        )
        
        if response['Items']:
            return response['Items'][0].get('receiver_email')
        
        return None
        
    except Exception as e:
        print(f"Error getting receiver email: {str(e)}")
        return None

def send_email_notification(email, subject, body):
    """Send email notification using SES"""
    try:
        # Configure SES (you need to verify the sender email in SES)
        sender_email = os.environ.get('SES_SENDER_EMAIL', 'noreply@yourdomain.com')
        
        response = ses.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        
        print(f"Email sent successfully: {response['MessageId']}")
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")

def send_sms_notification(phone_number, message):
    """Send SMS notification using SNS"""
    try:
        response = sns.publish(
            PhoneNumber=phone_number,
            Message=message
        )
        
        print(f"SMS sent successfully: {response['MessageId']}")
        
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")

def log_notification(notification_type, data):
    """Log notification for audit purposes"""
    try:
        # You can implement logging to CloudWatch, DynamoDB, or another service
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': notification_type,
            'data': data
        }
        
        print(f"Notification logged: {json.dumps(log_entry)}")
        
    except Exception as e:
        print(f"Error logging notification: {str(e)}")
