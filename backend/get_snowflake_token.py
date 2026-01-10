#!/usr/bin/env python3
"""
Snowflake OAuth Token Generator
Helps you get an OAuth access token for Snowflake authentication
"""

import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_oauth_token():
    """
    Get OAuth token using external browser authentication
    """
    print("=" * 60)
    print("Snowflake OAuth Token Generator")
    print("=" * 60)
    print()
    
    # Get credentials from environment or prompt
    user = os.getenv('SNOWFLAKE_USER') or input("Enter Snowflake username: ")
    account = os.getenv('SNOWFLAKE_ACCOUNT') or input("Enter Snowflake account (e.g., qb28835.us-east4.gcp): ")
    warehouse = os.getenv('SNOWFLAKE_WAREHOUSE') or input("Enter warehouse name (default: COMPUTE_WH): ") or "COMPUTE_WH"
    database = os.getenv('SNOWFLAKE_DATABASE') or input("Enter database name (default: MY_DB): ") or "MY_DB"
    
    print()
    print("Connecting to Snowflake...")
    print("A browser window will open for authentication.")
    print()
    
    try:
        # Connect using external browser OAuth
        conn = snowflake.connector.connect(
            user=user,
            account=account,
            authenticator='externalbrowser',
            warehouse=warehouse,
            database=database,
            schema='PUBLIC'
        )
        
        print("✓ Successfully authenticated!")
        print()
        
        # Get the OAuth token
        token = conn._rest._token
        
        print("=" * 60)
        print("Your OAuth Access Token:")
        print("=" * 60)
        print()
        print(token)
        print()
        print("=" * 60)
        print()
        print("Add this to your .env file:")
        print(f"SNOWFLAKE_TOKEN={token}")
        print()
        print("Note: This token will expire. You may need to regenerate it.")
        print()
        
        # Save to .env file option
        save = input("Would you like to save this to .env file? (y/n): ").lower()
        if save == 'y':
            env_path = '../.env'
            
            # Read existing .env
            env_lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Update or add token
            token_found = False
            for i, line in enumerate(env_lines):
                if line.startswith('SNOWFLAKE_TOKEN='):
                    env_lines[i] = f'SNOWFLAKE_TOKEN={token}\n'
                    token_found = True
                    break
            
            if not token_found:
                env_lines.append(f'\nSNOWFLAKE_TOKEN={token}\n')
            
            # Write back
            with open(env_path, 'w') as f:
                f.writelines(env_lines)
            
            print(f"✓ Token saved to {env_path}")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
        print("Common issues:")
        print("1. Incorrect account identifier format")
        print("2. User doesn't have access to the warehouse/database")
        print("3. Browser authentication was cancelled")
        print("4. Network connectivity issues")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(get_oauth_token())
