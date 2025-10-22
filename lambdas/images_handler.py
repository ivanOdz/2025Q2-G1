import json
import boto3
import uuid
import os
import mimetypes
from datetime import datetime
from botocore.exceptions import ClientError
import base64
from decimal import Decimal
from email import message_from_string
from email.message import EmailMessage

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sns = boto3.client('sns')

# Table references
package_images_table = dynamodb.Table('package-tracking-images')
packages_table = dynamodb.Table('package-tracking-packages')

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
        # Convert Decimals to floats before JSON serialization
        body = convert_decimals_to_float(body)
        response['body'] = json.dumps(body)

    return response

def lambda_handler(event, context):
    """
    Handle image-related API requests and S3 events
    Routes: 
    - GET /packages/{code}/images/ - Request pre-signed URL for upload
    - POST /packages/{code}/images/ - Upload via multipart (legacy)
    - GET /packages/{code}/images/ - Get existing images (if query param present)
    - S3 Event - Handle upload completion
    """
    
    try:
        # Check if this is an S3 event
        if 'Records' in event and event['Records']:
            record = event['Records'][0]
            if record.get('eventSource') == 'aws:s3':
                return handle_s3_event(record)
        
        # Extract user information from Cognito JWT
        user_id = event['requestContext']['authorizer']['claims']['sub']
        user_email = event['requestContext']['authorizer']['claims']['email']
        user_role = event['requestContext']['authorizer']['claims'].get('custom:role', 'user')
        
        # Parse HTTP method and path
        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {})
        
        # Get package code from path
        package_code = path_parameters.get('code')
        if not package_code:
            return cors_response(400, {'error': 'Package code is required'})
        
        # Route to appropriate handler
        if http_method == 'GET':
            # Check if requesting upload URL or getting existing images
            if query_parameters and query_parameters.get('action') == 'upload':
                return get_upload_url(package_code, user_id, user_role, query_parameters)
            else:
                return get_package_images(package_code, user_id, user_role)
        elif http_method == 'POST':
            return upload_image(package_code, event, user_id, user_role)
        else:
            return cors_response(405, {'error': 'Method not allowed'})
            
    except Exception as e:
        print(f"Error in images_handler: {str(e)}")
        return cors_response(500, {'error': 'Internal server error'})

def upload_image(package_code, event, user_id, user_role):
    """Upload image for a package"""
    try:
        # First, get the package to verify access
        package = get_package_by_code(package_code, user_id, user_role)
        if package['statusCode'] != 200:
            return package
        
        package_data = json.loads(package['body'])
        package_id = package_data['package_id']
        
        # Parse request body based on content type
        content_type = event.get('headers', {}).get('Content-Type', '')
        body = event.get('body', '')
        
        print(f"DEBUG: Content-Type: {content_type}")
        print(f"DEBUG: Body length: {len(body) if body else 0}")
        print(f"DEBUG: isBase64Encoded: {event.get('isBase64Encoded', False)}")
        
        if 'multipart/form-data' in content_type:
            # Handle multipart form data using Python's email parser
            print("DEBUG: Processing multipart form data")
            
            # Get the raw body
            raw_body = event.get('body', '')
            if event.get('isBase64Encoded', False):
                raw_body = base64.b64decode(raw_body).decode('utf-8')
            
            print(f"DEBUG: Raw body length: {len(raw_body)}")
            
            # Create a proper multipart message
            headers = f"Content-Type: {content_type}\r\n\r\n"
            message_text = headers + raw_body
            
            # Parse using email library
            msg = message_from_string(message_text)
            
            purpose = 'CREATION'
            file_data = None
            
            # Extract form fields
            for part in msg.walk():
                if part.get_content_disposition() == 'form-data':
                    name = part.get_param('name', header='content-disposition')
                    filename = part.get_param('filename', header='content-disposition')
                    
                    if name == 'purpose':
                        purpose = part.get_payload(decode=True).decode('utf-8').strip()
                        print(f"DEBUG: Extracted purpose: {purpose}")
                    elif name == 'image' and filename:
                        # This is the file
                        file_data = part.get_payload(decode=True)
                        print(f"DEBUG: Extracted file: {filename}, size: {len(file_data)} bytes")
                        # Convert to base64 for processing
                        file_data = base64.b64encode(file_data).decode('utf-8')
            
            if not file_data:
                return cors_response(400, {'error': 'Image file is required'})
        else:
            # Handle JSON payload with base64 image
            if not body:
                return cors_response(400, {'error': 'Request body is required'})
            
            try:
                body_json = json.loads(body)
                purpose = body_json.get('purpose', 'CREATION')
                file_data = body_json.get('image')
                
                if not file_data:
                    return cors_response(400, {'error': 'Image data is required'})
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON decode error: {str(e)}")
                return cors_response(400, {'error': 'Invalid JSON in request body'})
        
        # Generate S3 key
        file_extension = '.jpg'  # Default extension
        s3_key = f"packages/{package_id}/{uuid.uuid4().hex}{file_extension}"
        
        # Upload to S3
        try:
            print(f"DEBUG: Processing file_data type: {type(file_data)}")
            print(f"DEBUG: File data length: {len(file_data) if file_data else 0}")
            
            if isinstance(file_data, str) and file_data.startswith('data:'):
                # Handle data URL
                print("DEBUG: Processing data URL")
                header, encoded = file_data.split(',', 1)
                file_content = base64.b64decode(encoded)
                
                # Extract content type from data URL
                if 'image/jpeg' in header:
                    content_type = 'image/jpeg'
                    file_extension = '.jpg'
                elif 'image/png' in header:
                    content_type = 'image/png'
                    file_extension = '.png'
                elif 'image/gif' in header:
                    content_type = 'image/gif'
                    file_extension = '.gif'
                else:
                    content_type = 'image/jpeg'
                    file_extension = '.jpg'
                
                s3_key = f"packages/{package_id}/{uuid.uuid4().hex}{file_extension}"
            else:
                # Handle base64 string
                print("DEBUG: Processing base64 string")
                file_content = base64.b64decode(file_data)
                content_type = 'image/jpeg'
            
            print(f"DEBUG: Uploading to S3 - Bucket: {os.environ['S3_BUCKET_NAME']}, Key: {s3_key}")
            
            s3.put_object(
                Bucket=os.environ['S3_BUCKET_NAME'],
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            
            print("DEBUG: S3 upload successful")
            
        except Exception as e:
            print(f"Error uploading to S3: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return cors_response(500, {'error': 'Failed to upload image to S3'})
        
        # Save image metadata to DynamoDB
        image_id = str(uuid.uuid4())
        image_item = {
            'image_id': image_id,
            'package_id': package_id,
            'purpose': purpose,
            's3_key': s3_key,
            'created_at': datetime.utcnow().isoformat()
        }
        
        package_images_table.put_item(Item=image_item)
        
        # Publish to SNS for notifications
        sns_message = {
            'package_id': package_id,
            'code': package_code,
            'image_id': image_id,
            's3_key': s3_key,
            'purpose': purpose,
            'user_id': user_id,
            'action': 'image_uploaded',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=json.dumps(sns_message),
            Subject='Package Image Uploaded'
        )
        
        return cors_response(201, {
            'id': image_id,
            'package_id': package_id,
            'purpose': purpose,
            's3_key': s3_key,
            'created_at': image_item['created_at']
        })
        
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return cors_response(500, {'error': 'Failed to upload image'})

def get_package_images(package_code, user_id, user_role):
    """Get all images for a package"""
    try:
        # First, get the package to verify access
        package = get_package_by_code(package_code, user_id, user_role)
        if package['statusCode'] != 200:
            return package
        
        package_data = json.loads(package['body'])
        package_id = package_data['package_id']
        
        # Get all images for this package
        response = package_images_table.query(
            IndexName='package-index',
            KeyConditionExpression='package_id = :package_id',
            ExpressionAttributeValues={':package_id': package_id}
        )
        
        images = response['Items']
        
        # Generate pre-signed URLs for image access
        for image in images:
            try:
                presigned_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': os.environ['S3_BUCKET_NAME'], 'Key': image['s3_key']},
                    ExpiresIn=3600  # 1 hour
                )
                image['presigned_url'] = presigned_url
            except Exception as e:
                print(f"Error generating presigned URL: {str(e)}")
                image['presigned_url'] = None
        
        return cors_response(200, images)
        
    except Exception as e:
        print(f"Error getting package images: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve images'})

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
        if user_role != 'admin' and package['sender_id'] != user_id:
            return cors_response(403, {'error': 'Access denied'})
        
        return cors_response(200, package)
        
    except Exception as e:
        print(f"Error getting package by code: {str(e)}")
        return cors_response(500, {'error': 'Failed to retrieve package'})

def get_upload_url(package_code, user_id, user_role, query_parameters):
    """Generate pre-signed URL for image upload"""
    try:
        print(f"DEBUG: Generating upload URL for package: {package_code}")
        
        # First, get the package to verify access
        package = get_package_by_code(package_code, user_id, user_role)
        if package['statusCode'] != 200:
            return package
        
        package_data = json.loads(package['body'])
        package_id = package_data['package_id']
        
        # Get parameters from query string
        purpose = query_parameters.get('purpose', 'CREATION')
        content_type = query_parameters.get('contentType', 'image/jpeg')
        filename = query_parameters.get('filename', 'image.jpg')
        
        print(f"DEBUG: Upload parameters - purpose: {purpose}, contentType: {content_type}, filename: {filename}")
        
        # Generate unique S3 key
        file_extension = '.jpg'  # Default
        if 'image/png' in content_type:
            file_extension = '.png'
        elif 'image/gif' in content_type:
            file_extension = '.gif'
        
        s3_key = f"packages/{package_id}/{uuid.uuid4().hex}{file_extension}"
        
        # Generate pre-signed URL for PUT operation
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': os.environ['S3_BUCKET_NAME'],
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=3600  # 1 hour
        )
        
        print(f"DEBUG: Generated presigned URL for key: {s3_key}")
        
        # Save upload metadata to DynamoDB (pending upload)
        image_id = str(uuid.uuid4())
        image_item = {
            'image_id': image_id,
            'package_id': package_id,
            'purpose': purpose,
            's3_key': s3_key,
            'filename': filename,
            'content_type': content_type,
            'status': 'PENDING_UPLOAD',
            'created_at': datetime.utcnow().isoformat()
        }
        
        package_images_table.put_item(Item=image_item)
        
        return cors_response(200, {
            'upload_url': presigned_url,
            'image_id': image_id,
            's3_key': s3_key,
            'expires_in': 3600,
            'fields': {
                'key': s3_key,
                'Content-Type': content_type
            }
        })
        
    except Exception as e:
        print(f"Error generating upload URL: {str(e)}")
        return cors_response(500, {'error': 'Failed to generate upload URL'})

def handle_s3_upload_completion(s3_key, image_id):
    """Handle S3 upload completion - update DynamoDB and send notifications"""
    try:
        print(f"DEBUG: Handling S3 upload completion for key: {s3_key}, image_id: {image_id}")
        
        # Update image status in DynamoDB
        package_images_table.update_item(
            Key={'image_id': image_id},
            UpdateExpression='SET #status = :status, uploaded_at = :uploaded_at',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'UPLOADED',
                ':uploaded_at': datetime.utcnow().isoformat()
            }
        )
        
        # Get the image record to extract package info
        response = package_images_table.get_item(Key={'image_id': image_id})
        if 'Item' not in response:
            print(f"ERROR: Image record not found for image_id: {image_id}")
            return
        
        image_item = response['Item']
        package_id = image_item['package_id']
        
        # Get package info for notifications
        package_response = packages_table.get_item(Key={'package_id': package_id})
        if 'Item' not in package_response:
            print(f"ERROR: Package not found for package_id: {package_id}")
            return
        
        package = package_response['Item']
        
        # Publish to SNS for notifications
        sns_message = {
            'package_id': package_id,
            'code': package.get('code'),
            'image_id': image_id,
            's3_key': s3_key,
            'purpose': image_item['purpose'],
            'action': 'image_uploaded',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=json.dumps(sns_message),
            Subject='Package Image Uploaded'
        )
        
        print(f"DEBUG: Successfully processed upload completion for image_id: {image_id}")
        
    except Exception as e:
        print(f"Error handling S3 upload completion: {str(e)}")
        # Don't return error response as this is called internally

def handle_s3_event(record):
    """Handle S3 upload event"""
    try:
        print(f"DEBUG: Received S3 event: {json.dumps(record)}")
        
        # Extract S3 information
        bucket_name = record['s3']['bucket']['name']
        s3_key = record['s3']['object']['key']
        event_name = record['eventName']
        
        print(f"DEBUG: S3 event - bucket: {bucket_name}, key: {s3_key}, event: {event_name}")
        
        # Only process ObjectCreated events
        if not event_name.startswith('ObjectCreated'):
            print(f"DEBUG: Ignoring non-ObjectCreated event: {event_name}")
            return {'statusCode': 200}
        
        # Extract image_id from the S3 key path
        # Expected format: packages/{package_id}/{image_id}.{ext}
        key_parts = s3_key.split('/')
        if len(key_parts) != 3 or key_parts[0] != 'packages':
            print(f"ERROR: Unexpected S3 key format: {s3_key}")
            return {'statusCode': 400}
        
        package_id = key_parts[1]
        filename = key_parts[2]
        
        # Extract image_id from filename (remove extension)
        image_id = filename.split('.')[0]
        
        print(f"DEBUG: Extracted package_id: {package_id}, image_id: {image_id}")
        
        # Find the image record in DynamoDB
        response = package_images_table.get_item(Key={'image_id': image_id})
        if 'Item' not in response:
            print(f"ERROR: Image record not found for image_id: {image_id}")
            return {'statusCode': 404}
        
        image_item = response['Item']
        
        # Verify the package_id matches
        if image_item['package_id'] != package_id:
            print(f"ERROR: Package ID mismatch. Expected: {package_id}, Found: {image_item['package_id']}")
            return {'statusCode': 400}
        
        # Update image status to uploaded
        package_images_table.update_item(
            Key={'image_id': image_id},
            UpdateExpression='SET #status = :status, uploaded_at = :uploaded_at',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'UPLOADED',
                ':uploaded_at': datetime.utcnow().isoformat()
            }
        )
        
        # Get package info for notifications
        package_response = packages_table.get_item(Key={'package_id': package_id})
        if 'Item' not in package_response:
            print(f"ERROR: Package not found for package_id: {package_id}")
            return {'statusCode': 404}
        
        package = package_response['Item']
        
        # Publish to SNS for notifications
        sns_message = {
            'package_id': package_id,
            'code': package.get('code'),
            'image_id': image_id,
            's3_key': s3_key,
            'purpose': image_item['purpose'],
            'action': 'image_uploaded',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=json.dumps(sns_message),
            Subject='Package Image Uploaded'
        )
        
        print(f"DEBUG: Successfully processed S3 upload for image_id: {image_id}")
        return {'statusCode': 200}
        
    except Exception as e:
        print(f"Error handling S3 event: {str(e)}")
        return {'statusCode': 500}
