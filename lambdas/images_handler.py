import json
import boto3
import uuid
import os
import mimetypes
from datetime import datetime
from botocore.exceptions import ClientError
import base64

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sns = boto3.client('sns')

# Table references
package_images_table = dynamodb.Table('package-tracking-images')
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
        response['body'] = json.dumps(body) if isinstance(body, dict) else str(body)
    
    return response

def lambda_handler(event, context):
    """
    Handle image-related API requests
    Routes: POST /packages/{code}/images/, GET /packages/{code}/images/
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
            return cors_response(400, {'error': 'Package code is required'})
        
        # Route to appropriate handler
        if http_method == 'POST':
            return upload_image(package_code, event, user_id, user_role)
        elif http_method == 'GET':
            return get_package_images(package_code, user_id, user_role)
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
        
        # Parse multipart form data
        content_type = event.get('headers', {}).get('Content-Type', '')
        
        if 'multipart/form-data' in content_type:
            # Handle multipart form data
            body = event.get('body', '')
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(body).decode('utf-8')
            
            # Parse form data (simplified - in production, use proper multipart parser)
            lines = body.split('\r\n')
            purpose = 'CREATION'
            file_data = None
            
            for i, line in enumerate(lines):
                if 'name="purpose"' in line:
                    # Extract purpose value
                    purpose_line = lines[i + 2] if i + 2 < len(lines) else ''
                    purpose = purpose_line.strip()
                elif 'name="image"' in line:
                    # Extract file data
                    if i + 4 < len(lines):
                        file_data = lines[i + 4]
            
            if not file_data:
                return cors_response(400, {'error': 'Image file is required'})
        else:
            # Handle JSON payload with base64 image
            body = json.loads(event.get('body', '{}'))
            purpose = body.get('purpose', 'CREATION')
            file_data = body.get('image')
            
            if not file_data:
                return cors_response(400, {'error': 'Image data is required'})
        
        # Generate S3 key
        file_extension = '.jpg'  # Default extension
        s3_key = f"packages/{package_id}/{uuid.uuid4().hex}{file_extension}"
        
        # Upload to S3
        try:
            if isinstance(file_data, str) and file_data.startswith('data:'):
                # Handle data URL
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
                file_content = base64.b64decode(file_data)
                content_type = 'image/jpeg'
            
            s3.put_object(
                Bucket=os.environ['S3_BUCKET_NAME'],
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            
        except Exception as e:
            print(f"Error uploading to S3: {str(e)}")
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
