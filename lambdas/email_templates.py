"""
Email templates for package tracking notifications
All email templates are in English
"""


def format_state(state):
    """Format state by replacing underscores with spaces"""
    return state.replace('_', ' ')


def get_package_created_template(receiver_name, package_code, tracking_link, timestamp):
    """
    Template for package creation notification
    
    Args:
        receiver_name: Name of the package receiver
        package_code: Package tracking code
        tracking_link: URL to track the package
        timestamp: Creation timestamp
    
    Returns:
        tuple: (subject, message_body)
    """
    greeting = f"Hello {receiver_name}," if receiver_name else "Hello,"
    
    subject = f"Package {package_code} On The Way - FastTrack Delivery"
    
    message_body = f"""
{greeting}

You have a package on the way to you.

Package Code: {package_code}
Status: Created and ready for shipment
Date: {timestamp}

Track your package: {tracking_link}

---
FastTrack Delivery Team
This is an automated email.
    """
    
    return subject, message_body.strip()


def get_package_delivered_template(receiver_name, package_code, timestamp):
    """
    Template for package delivered notification
    
    Args:
        receiver_name: Name of the package receiver
        package_code: Package tracking code
        timestamp: Delivery timestamp
    
    Returns:
        tuple: (subject, message_body)
    """
    greeting = f"Hello {receiver_name}," if receiver_name else "Hello,"
    
    subject = f"Package {package_code} Delivered! - FastTrack Delivery"
    
    formatted_state = format_state('DELIVERED')
    
    message_body = f"""
{greeting}

Your package {package_code} has been successfully delivered!

Package Code: {package_code}
Status: {formatted_state}
Date: {timestamp}

Thank you for using FastTrack Delivery.

---
FastTrack Delivery Team
This is an automated email.
    """
    
    return subject, message_body.strip()


def get_package_cancelled_template(receiver_name, package_code, timestamp):
    """
    Template for package cancelled notification
    
    Args:
        receiver_name: Name of the package receiver
        package_code: Package tracking code
        timestamp: Cancellation timestamp
    
    Returns:
        tuple: (subject, message_body)
    """
    greeting = f"Hello {receiver_name}," if receiver_name else "Hello,"
    
    subject = f"Package {package_code} Cancelled - FastTrack Delivery"
    
    formatted_state = format_state('CANCELLED')
    
    message_body = f"""
{greeting}

The shipment of package {package_code} has been cancelled.

Package Code: {package_code}
Status: {formatted_state}
Date: {timestamp}

If you have any questions, please contact the sender.

---
FastTrack Delivery Team
This is an automated email.
    """
    
    return subject, message_body.strip()


def get_package_status_update_template(receiver_name, package_code, action, depot_name, new_state, timestamp):
    """
    Template for package status update notification
    
    Args:
        receiver_name: Name of the package receiver
        package_code: Package tracking code
        action: Track action (e.g., 'ARRIVED_DEPOT', 'SEND_FINAL')
        depot_name: Name of the depot (if applicable)
        new_state: New package state
        timestamp: Update timestamp
    
    Returns:
        tuple: (subject, message_body)
    """
    greeting = f"Hello {receiver_name}," if receiver_name else "Hello,"
    
    subject = f"Package {package_code} - Status Update"
    
    # Map actions to display names
    action_map = {
        'SEND_DEPOT': 'Sent to Depot',
        'ARRIVED_DEPOT': 'Arrived at Depot',
        'SEND_FINAL': 'Sent to Final Destination',
        'ARRIVED_FINAL': 'Arrived at Final Destination'
    }
    action_display = action_map.get(action, action)
    
    # Format state for display
    formatted_state = format_state(new_state)
    
    # Add depot information if available
    depot_info = ""
    if depot_name:
        depot_info = f"\nDepot: {depot_name}"
    
    message_body = f"""
{greeting}

Your package {package_code} status has been updated.

Package Code: {package_code}
Action: {action_display}{depot_info}
Status: {formatted_state}
Date: {timestamp}

You can track your package at any time.

---
FastTrack Delivery Team
This is an automated email.
    """
    
    return subject, message_body.strip()

