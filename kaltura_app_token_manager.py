#!/usr/bin/env python3
import os
import argparse
import hashlib
import json
import logging
from KalturaClient import KalturaClient, KalturaConfiguration
from KalturaClient.Plugins.Core import (KalturaAppToken, KalturaAppTokenFilter, KalturaFilterPager, KalturaSessionType, KalturaAppTokenHashType)
from KalturaClient.exceptions import KalturaException

# Custom logger class
class KalturaLogger:
    def __init__(self):
        self.logger = logging.getLogger('KalturaClient')
        logging.basicConfig(level=logging.DEBUG)

    def log(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

# Privilege handling functions
def handle_privilege(privilege_name, value):
    # For 'list', we only support 'list:*', so we handle it as a special case
    if privilege_name == 'list':
        return 'list:*'
    else:
        # For all other privileges, we format it as 'privilege_name:value'
        return f"{privilege_name}:{value}"
    
# Privilege dictionary
PRIVILEGE_HANDLERS = {
    'edit': handle_privilege,
    'sview': handle_privilege,
    'list': handle_privilege,  # 'list' is a special case handled within the function
    'download': handle_privilege,
    'downloadasset': handle_privilege,
    'editplaylist': handle_privilege,
    'sviewplaylist': handle_privilege,
    'edituser': handle_privilege,
    'actionslimit': handle_privilege,
    'setrole': handle_privilege,
    'iprestrict': handle_privilege,
    'urirestrict': handle_privilege,
    'enableentitlement': handle_privilege,
    'disableentitlement': handle_privilege,
    'disableentitlementforentry': handle_privilege,
    'privacycontext': handle_privilege,
    'enablecategorymoderation': handle_privilege,
    'reftime': handle_privilege,
    'preview': handle_privilege,
    'sessionid': handle_privilege,
}

# Initialize parser with dynamic privileges based on the handlers
def setup_parser():
    parser = argparse.ArgumentParser(description='Manage Kaltura App Tokens with dynamic privileges.')
    # Add arguments for each privilege type with the correct handler
    parser.add_argument('--edit', type=str, help='Set the edit privilege. Expects entry id or * for wildcard.')
    parser.add_argument('--sview', type=str, help='Set the sview privilege. Expects entry id or * for wildcard.')
    parser.add_argument('--download', type=str, help='Set the download privilege. Expects entry id or * for wildcard.')
    parser.add_argument('--downloadasset', type=str, help='Set the downloadasset privilege. Expects asset id or *.')
    parser.add_argument('--editplaylist', type=str, help='Set the editplaylist privilege. Expects the id of the playlist.')
    parser.add_argument('--sviewplaylist', type=str, help='Set the sviewplaylist privilege. Expects the id of the playlist.')
    parser.add_argument('--edituser', type=str, help='Set the edituser privilege. * or a list of usernames separated by /.')
    parser.add_argument('--actionslimit', type=int, help='Set the actionslimit privilege. Expects an integer.')
    parser.add_argument('--setrole', type=str, help='Set the setrole privilege. Expects the id of the role.')
    parser.add_argument('--iprestrict', type=str, help='Set the iprestrict privilege. Only a single address is allowed.')
    parser.add_argument('--urirestrict', type=str, help='Set the urirestrict privilege. A URI, * as a prefix allowed.')
    parser.add_argument('--enableentitlement', action='store_true', help='Force entitlement checks.')
    parser.add_argument('--disableentitlement', action='store_true', help='Bypass entitlement checks.')
    parser.add_argument('--disableentitlementforentry', type=str, help='Bypass entitlement for a given entry id.')
    parser.add_argument('--privacycontext', type=str, help='Set the privacy context for entitlement checks.')
    parser.add_argument('--enablecategorymoderation', action='store_true', help='Enable category moderation.')
    parser.add_argument('--reftime', type=int, help='Set the reftime privilege. Expects a Unix timestamp.')
    parser.add_argument('--preview', type=int, help='Set the preview privilege. Size in bytes.')
    parser.add_argument('--sessionid', type=str, help='Set the sessionid. An arbitrary string identifying the session.')
    # Set the description of the app token
    parser.add_argument('--description', type=str, help='Description for the app token.')
    # Add the update argument
    parser.add_argument('--update', type=str, help='Update an existing app token by ID.')
    # Special handling for 'list' as it only supports wildcard
    parser.add_argument('--list', action='store_true', help='Enable listing of all entries.')
    # Should we create a session using that app token?
    parser.add_argument('--start_session', action='store_true', help='Start a session with the app token after creation or update.')
    # Delete an app token 
    parser.add_argument('--delete', type=str, help='Delete an app token by ID.')

    return parser

# Deletes an app token
def delete_app_token(client, app_token_id):
    try:
        # Delete the app token using the Kaltura API
        client.appToken.delete(app_token_id)
        print(f"App Token with ID {app_token_id} has been deleted.")
    except KalturaException as e:
        print(f"Error deleting App Token with ID {app_token_id}: {e}")

# Function to build privileges
def build_privileges(args):
    privileges = []
    for privilege, handler in PRIVILEGE_HANDLERS.items():
        value = getattr(args, privilege, None)
        if value is not None:
            # Call the handler function if it's callable, otherwise use the value as is (for 'list')
            if callable(handler):
                privilege_str = handler(privilege, value)
            else:
                privilege_str = handler
            privileges.append(privilege_str)
    return ','.join(privileges)

# word-wrap function that wraps text on exactly width characters
def wrap_text(text, width):
    return [text[i:i+width] for i in range(0, len(text), width)]

# fetch and list all app tokens available for the configured partner ID
def list_app_tokens(client):
    try:
        # Create a new filter for App Tokens
        filter = KalturaAppTokenFilter()
        
        # Create a new pager object
        pager = KalturaFilterPager()
        
        # Fetch all App Tokens using the list method
        result = client.appToken.list(filter, pager)
        
        # Check if there are any App Tokens to display
        if not result.objects:
            print("No App Tokens found.")
            return
        
        # Get the terminal width
        terminal_width = os.get_terminal_size().columns
        
        # Define fixed column widths
        id_width = 15
        value_width = 32
        description_width = 20
        fixed_widths = id_width + value_width + description_width + 3  # +3 for separators between fixed columns
        
        # Calculate dynamic width for privileges column
        privileges_width = terminal_width - fixed_widths - 6  # -6 for the separators and margins

        # Print header
        header_format = f"{{:<{id_width}}} | {{:<{value_width}}} | {{:<{description_width}}} | {{:<{privileges_width}}}"
        print(header_format.format("App Token ID", "Value", "Description", "Session Privileges"))
        print("-" * (terminal_width - 1))  # Adjust to terminal width
        
        # Print each app token in a row
        for app_token in result.objects:
            # Wrap the privileges string to avoid very long lines
            wrapped_privileges = wrap_text(app_token.sessionPrivileges or '', privileges_width)
            
            # Print the first line with the token ID, value, and description
            first_line_format = f"{{:<{id_width}}} | {{:<{value_width}}} | {{:<{description_width}}} | {{:<{privileges_width}}}"
            print(first_line_format.format(app_token.id, app_token.token, app_token.description or '', wrapped_privileges[0] if wrapped_privileges else ''))
            
            # Print the subsequent lines for wrapped privileges
            for line in wrapped_privileges[1:]:
                print(f"{' ' * (id_width + value_width + description_width + 6)}| {line}")
    except KalturaException as e:
        print(f"Failed to list App Tokens: {e}")

#  initiates a session using an application token
def start_app_token_session(client, partner_id, app_token_id, app_token_value):
    # Start an unprivileged session using session.startWidgetSession
    widget_id = "_{0}".format(partner_id)  # Construct the widget ID
    unprivileged_ks_response = client.session.startWidgetSession(widget_id)
    unprivileged_ks = unprivileged_ks_response.ks  # Extracting the KS from the response object

    if not unprivileged_ks:
        raise Exception("Failed to start an unprivileged session.")

    # Set the KS for the client to the unprivileged one
    client.setKs(unprivileged_ks)

    # Calculate the hash for the app token session
    token_hash = hashlib.sha256((unprivileged_ks + app_token_value).encode('utf-8')).hexdigest()

    # Start the app token session
    app_token_session = client.appToken.startSession(app_token_id, token_hash, "", KalturaSessionType.USER, partner_id)
    privileged_ks = app_token_session.ks  # Extracting the privileged KS

    if not privileged_ks:
        raise Exception("Failed to start a privileged session with the app token.")

    # Set the KS for the client to the privileged one
    client.setKs(privileged_ks)

    return privileged_ks

import sys

def load_configuration():
    try:
        with open('config.json', 'r') as config_file:
            config_data = json.load(config_file)
        return config_data
    except FileNotFoundError:
        raise Exception("Configuration file 'config.json' not found.")
    except json.JSONDecodeError:
        raise Exception("Configuration file 'config.json' contains invalid JSON.")

def initialize_client(config):
    # Initialize the Kaltura configuration with the partner ID
    kaltura_config = KalturaConfiguration(config['PARTNER_ID'])
    kaltura_config.serviceUrl = config['KALTURA_SERVICE_URL']
    # Create the Kaltura client with the configuration
    client = KalturaClient(kaltura_config)
    client.requestHeaders = {
        'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    }
    return client

def start_admin_session(client, config):
    # Extract the necessary information from the configuration
    admin_secret = config.get('ADMIN_SECRET')
    user_id = config.get('USER_ID', '')  # Use empty string as default if USER_ID is not provided
    partner_id = config.get('PARTNER_ID')
    expiry = config.get('EXPIRY', 86400)  # Default expiry to 24 hours if not provided
    privileges = config.get("DEFAULT_ADMIN_PRIVILEGES", '')  # Default privileges to empty if not provided
    
    # Start the session
    try:
        ks = client.session.start(admin_secret, user_id, KalturaSessionType.ADMIN, partner_id, expiry, privileges)
        print(f"KS: {ks}")
        return ks
    except KalturaException as e:
        raise Exception(f"Failed to start session: {e}")

# handle updating an existing app token's privileges and description
def update_app_token(client, app_token_id, privileges, description):
    try:
        # Fetch the existing app token to update it
        app_token_to_update = client.appToken.get(app_token_id)
        
        # Update the privileges and description if provided
        if privileges:
            app_token_to_update.sessionPrivileges = privileges
        if description:
            app_token_to_update.description = description
        
        # Update the app token using the Kaltura API
        updated_app_token = client.appToken.update(app_token_id, app_token_to_update)

        # Print the updated token details
        print(f"Updated App Token ID: {updated_app_token.id}")
        print(f"Updated App Token Description: {updated_app_token.description}")
        print(f"Updated App Token Session Privileges: {updated_app_token.sessionPrivileges}")
        return updated_app_token
    except KalturaException as e:
        print(f"Error updating App Token with ID {app_token_id}: {e}")
        return None

def create_app_token(client, privileges, description):
    try:
        # Create a new instance of the KalturaAppToken
        app_token = KalturaAppToken()
        app_token.description = description
        app_token.sessionPrivileges = privileges
        app_token.sessionType = KalturaSessionType.USER  # Or use KalturaSessionType.ADMIN based on your requirement
        app_token.hashType = KalturaAppTokenHashType.SHA256  # Assuming SHA256 is the desired hash type

        # Add the new app token using the Kaltura API
        new_app_token = client.appToken.add(app_token)

        # Print the new token details
        print(f"Created New App Token ID: {new_app_token.id}")
        print(f"App Token Description: {new_app_token.description}")
        print(f"App Token Session Privileges: {new_app_token.sessionPrivileges}")

        return new_app_token
    except KalturaException as e:
        print(f"Error creating new App Token: {e}")
        return None

def main():
    parser = setup_parser()
    args = parser.parse_args()
    
    # If no arguments are provided, print the help message and exit
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    
    # Initialize the application logic
    run_application(args)

def run_application(args):
    # Load the configuration and continue with the script logic
    config = load_configuration()
    client = initialize_client(config)
    ks = start_admin_session(client, config)
    client.setKs(ks)

    if args.delete:
        delete_app_token(client, args.delete)
    elif args.list:
        list_app_tokens(client)
    else:
        process_app_token_arguments(client, args, config)

def process_app_token_arguments(client, args, config):
    new_token_id = None
    new_token_value = None
    privileges = build_privileges(args)
    if hasattr(args, 'update') and args.update:
        # If an update ID is provided, update the token, otherwise create a new one
        update_app_token(client, args.update, build_privileges(args), args.description)
    else:
        # Assume we want to create a new token if we're not updating
        new_app_token = create_app_token(client, build_privileges(args), args.description)
        if new_app_token:
            new_token_id = new_app_token.id
            new_token_value = new_app_token.token  # Assuming the token value is returned here

    # Start session with app token if requested
    if args.start_session:
        # Ensure new_token_id and new_token_value are not None before calling
        if new_token_id and new_token_value:
            start_app_token_session(client, config.get('PARTNER_ID'), new_token_id, new_token_value)

if __name__ == "__main__":
    main()
