import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table('package-tracking-users')

def lambda_handler(event, context):
    # Cognito triggers have "triggerSource"
    if "triggerSource" in event:
        source = event["triggerSource"]
        if source == "PostConfirmation_ConfirmSignUp":
            return handle_signup(event)
        elif source == "TokenGeneration_HostedAuth" or source == "TokenGeneration_Authentication":
            return handle_login(event)
        else:
            return event  # ignore others

    # Otherwise, it's an API Gateway invocation
    if "httpMethod" in event:
        return handle_api(event)

    return {"statusCode": 400, "body": "Unsupported event"}

# --- Cognito: PostConfirmation ---
def handle_signup(event):
    attrs = event["request"]["userAttributes"]
    email = attrs.get("email")

    if email:
        user_table.put_item(Item={"email": email, "role": "user"})
    return event

# --- Cognito: PreTokenGeneration ---
def handle_login(event):
    email = event["request"]["userAttributes"].get("email")
    if not email:
        return event

    resp = user_table.get_item(Key={"email": email})
    role = resp.get("Item", {}).get("role", "user")

    event["response"]["claimsOverrideDetails"] = {
        "claimsToAddOrOverride": {"custom:role": role}
    }
    return event

# --- API Gateway: POST /change-role ---
def handle_api(event):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    email = claims.get("email")
    if not email:
        return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

    try:
        body = json.loads(event["body"])
    except Exception:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    new_role = body.get("role")
    if new_role not in ["user", "admin"]:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid role"})}

    user_table.update_item(
        Key={"email": email},
        UpdateExpression="SET #r = :r",
        ExpressionAttributeNames={"#r": "role"},
        ExpressionAttributeValues={":r": new_role}
    )

    return {"statusCode": 200, "body": json.dumps({"message": f"Role changed to {new_role}"})}
