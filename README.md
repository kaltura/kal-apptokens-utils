# Kaltura App Token Manager

This Python script is designed to manage Kaltura App Tokens. It allows for the creation, listing, updating, and deletion of app tokens. This document provides usage, maintenance, and extension guidelines.

## Features

- **Create App Tokens:** Generate new app tokens with specified privileges.
- **List App Tokens:** Retrieve and display all app tokens for the configured partner ID.
- **Update App Tokens:** Modify existing app tokens' privileges and descriptions.
- **Delete App Tokens:** Remove app tokens by ID.
- **Session Management:** Start a session with an app token after creation or update.

## Prerequisites

To run this script, you'll need Python 3 installed on your system and the `KalturaClient` library.

## Configuration

Before running the script, you must have a `config.json` file in the same directory as the script. 
Clone `config.template.json` to `config.json`, and configure it:  

- `<your_partner_id>` - The Partner ID from KMC Integration Settings
- `<your_admin_secret_from_kmc>` - The Admin Secret from KMC Integration Settings

### Run as command line utility

Run the following:

```bash
chmod +x kaltura_app_token_manager.py
```

## Usage

Run the script with -h or --help to see the available options:

```bash
./kaltura_app_token_manager.py --help
```

### Samples 

#### Create a New App Token

```bash
./kaltura_app_token_manager.py --create --description "My App Token" --edit "*"
```

#### List All App Tokens

```bash
./kaltura_app_token_manager.py --list
```

#### Update an Existing App Token

```bash
./kaltura_app_token_manager.py --update "token_id" --description "Updated Description"
```

#### Delete an App Token

```bash
./kaltura_app_token_manager.py --delete "token_id"
```

#### Start a Session with the App Token

```bash
./kaltura_app_token_manager.py --create --start_session --description "Session Token" --sview "*"
```

## Extending the Script

To extend the functionality:

1. Add New Privileges: Introduce new privileges by expanding the PRIVILEGE_HANDLERS dictionary and updating the argument parser in setup_parser().
1. Enhance Session Management: You might want to add features such as logging out sessions or extending session lifetimes.
1. Improve Output Formatting: For better readability when listing tokens, consider implementing tabular display or exporting to formats like CSV.
1. Integrate with Other Systems: You can extend the script to work with other systems by adding appropriate APIs and configuration options.

## Troubleshooting

1. Configuration Errors: Ensure config.json is valid JSON and contains the correct information.
1. Dependency Issues: If the KalturaClient cannot be imported, check your Python environment and the library installation.
1. API Limitations: Be aware of any API rate limits or changes in the Kaltura API that may affect the script's operation.  

## License

This script is released under the [MIT License](https://opensource.org/license/mit/).  

## Support

This script is provided "as-is" without warranty or support. Use it at your own risk. If you encounter any issues, please report them in the repository's issues section.
