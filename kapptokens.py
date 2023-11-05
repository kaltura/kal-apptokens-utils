import argparse
import logging
from KalturaClient import KalturaClient, KalturaConfiguration
from KalturaClient.Plugins.Core import KalturaAppToken, KalturaAppTokenFilter, KalturaFilterPager, KalturaSessionType
from KalturaClient.exceptions import KalturaException
import hashlib
import json

# Custom logger class
class KalturaLogger:
    def __init__(self):
        self.logger = logging.getLogger('KalturaClient')
        logging.basicConfig(level=logging.DEBUG)

    def log(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

def start_app_token_session(client, partner_id, app_token_id, app_token_value):
    # Start an unprivileged session using session.startWidgetSession
    widget_id = f"_{partner_id}"  # Replace with your actual Partner ID
    unprivileged_ks_response = client.session.startWidgetSession(widget_id)
    unprivileged_ks = unprivileged_ks_response.ks  # Extracting the ks from the response object
    
    if not unprivileged_ks:
        print("Failed to get an unprivileged ks.")
        return None
    
    client.setKs(unprivileged_ks)

    # Compute the Hash
    hash_string = hashlib.sha256((unprivileged_ks + app_token_value).encode('ascii')).hexdigest()

    # Start the App Token Session using appToken.startSession
    app_token_session = client.appToken.startSession(app_token_id, hash_string)
    privileged_ks = app_token_session.ks  # Again, extract the ks

    # Set the new KS
    client.setKs(privileged_ks)

    return privileged_ks

def build_uri_privilege(list_actions):
    uris = []
    for action in list_actions:
        if '*' in action:
            uri = f"/api_v3/service/{action.replace('.', '/action/').replace('*', '*')}"
        else:
            uri = f"/api_v3/service/{action.replace('.', '/action/')}/"
        uris.append(uri)
    return uris

def list_app_tokens(client):
    filter = KalturaAppTokenFilter()
    pager = KalturaFilterPager()
    
    # Fetch all App Tokens
    result = client.appToken.list(filter, pager)
    
    # Print the list of App Tokens
    for app_token in result.objects:
        print(f"App Token ID: {app_token.id}")
        print(f"App Token Value: {app_token.token}")
        print(f"App Token Description: {app_token.description}")
        print("------")

def main():
    parser = argparse.ArgumentParser(description='Manage Kaltura App Tokens.')
    parser.add_argument(
        '-l', '--list', 
        action='store_true', 
        help='List all existing App Tokens.'
    )
    parser.add_argument(
        '--actions', 
        type=str, 
        help='A comma-separated list of allowed actions for the App Token. Use the format "service.action" for each action. Wildcards can be used, e.g., "media.*".'
    )
    parser.add_argument(
        '-u', '--update', 
        type=str, 
        help='Specify the ID of an existing App Token to update. If this option is not provided, a new App Token will be created.'
    )
    parser.add_argument(
        '-a', '--append', 
        action='store_true', 
        help='If this flag is set, the new actions will be appended to the existing "urirestrict" privileges of the App Token specified by the --update option.'
    )
    parser.add_argument(
        '-d', '--description',
        type=str,
        help='A description for the App Token. This will be set for new App Tokens and can update existing ones if --update is used.'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug printing.'
    )
    
    args = parser.parse_args()
    
    # Check for mandatory 'actions' argument when adding or updating an App Token
    if (args.update or not args.list) and not args.actions:
        print("The --actions argument is mandatory when adding or updating an App Token.")
        return

    list_actions = args.actions.lower().split(',') if args.actions else None

    # Load configuration from JSON file
    with open('config.json', 'r') as f:
        config_data = json.load(f)
    PARTNER_ID = config_data['PARTNER_ID']
    ADMIN_SECRET = config_data['ADMIN_SECRET']
    SCRIPT_USER_ID = config_data['SCRIPT_USER_ID']
    ADMIN_SESSION_EXPIRY = config_data['ADMIN_SESSION_EXPIRY']
    KALTURA_SERVICE_URL = config_data['KALTURA_SERVICE_URL']

    # Initialize the Kaltura client
    config = KalturaConfiguration(PARTNER_ID)
    config.serviceUrl = KALTURA_SERVICE_URL
    if args.debug:
        kaltura_logger = KalturaLogger()
        config.setLogger(kaltura_logger)
    client = KalturaClient(config)
    client.requestHeaders = {
        'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    }
    
    # Start an admin-level Kaltura session using your Admin Secret
    ks = client.session.start(ADMIN_SECRET, SCRIPT_USER_ID, KalturaSessionType.ADMIN, PARTNER_ID, ADMIN_SESSION_EXPIRY, '')
    
    client.setKs(ks)
    
    if args.list:
        list_app_tokens(client)
        return  # Exit after listing all tokens
    
    print_text_prefix = ''
    app_token_id = None
    app_token_value = None
    session_privileges = None

    if args.update:
        # Update existing App Token
        try:
            existing_app_token = client.appToken.get(args.update)
        except KalturaException as e:
            if e.code == 'APP_TOKEN_ID_NOT_FOUND':
                print(f"App Token ID {args.update} not found. Please use a valid ID.")
                return
            else:
                raise e

        if args.append:
            # Create a list of existing URIs by splitting the string on "|"
            existing_uris = existing_app_token.sessionPrivileges.split("|")
            
            # Add new URIs to the list
            new_uris = build_uri_privilege(list_actions)
            existing_uris.extend(new_uris)
            
            # Remove duplicates
            unique_uris = list(set(existing_uris))
            
            # Convert back to string
            existing_app_token.sessionPrivileges = "urirestrict:" + "|".join(unique_uris)
        else:
            existing_app_token.sessionPrivileges = build_uri_privilege(list_actions)
        
        if args.description:
            existing_app_token.description = args.description

        result = client.appToken.update(args.update, existing_app_token)
        app_token_id = result.id
        app_token_value = result.token
        session_privileges = result.sessionPrivileges
        print_text_prefix = f"Updated App Token ({args.update})"
    else:
        # Add a new App Token
        app_token = KalturaAppToken()
        app_token.sessionType = KalturaSessionType.USER
        app_token.sessionPrivileges = build_uri_privilege(list_actions)
        app_token.hashType = "SHA256"
        
        if args.description:
            app_token.description = args.description

        result = client.appToken.add(app_token)
        app_token_id = result.id
        app_token_value = result.token
        session_privileges = result.sessionPrivileges
        print_text_prefix = f"New App Token ID ({app_token_id})"

    print(print_text_prefix + f"Value: {app_token_value}")
    print(print_text_prefix + f"Privileges: {session_privileges}")

    # Generate a sample KS from this appToken:
    token_ks = start_app_token_session(client, PARTNER_ID, app_token_id, app_token_value)
    print(f"Gen KS from this AppToken: {token_ks}")

if __name__ == "__main__":
    main()