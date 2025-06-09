#!/usr/bin/env python3
"""
Debug script to check which Runway endpoint is being used
"""

import os
import sys
sys.path.append('.')

from dotenv import load_dotenv
from runwayml import RunwayML

# Load environment variables
load_dotenv()

def debug_runway_client():
    """Debug the Runway client configuration"""
    
    api_key = os.getenv("RUNWAY_API_KEY")
    print(f"🔑 RUNWAY_API_KEY found: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"   Key starts with: {api_key[:20]}...")
    
    print("\n🏗️  Creating Runway client...")
    client = RunwayML(api_key=api_key)
    
    print(f"   Client object: {client}")
    print(f"   Client type: {type(client)}")
    
    # Try to access the internal client attributes
    try:
        print(f"\n🔍 Inspecting client internals...")
        print(f"   Client dir: {[attr for attr in dir(client) if not attr.startswith('_')]}")
        
        # Try to access the internal HTTP client
        if hasattr(client, '_client'):
            print(f"   Internal client: {client._client}")
            if hasattr(client._client, 'base_url'):
                print(f"   🎯 Base URL: {client._client.base_url}")
            else:
                print(f"   Internal client attributes: {[attr for attr in dir(client._client) if not attr.startswith('_')]}")
        
        # Try other ways to access the endpoint
        for attr_name in ['base_url', 'api_base', 'endpoint', 'url']:
            if hasattr(client, attr_name):
                print(f"   {attr_name}: {getattr(client, attr_name)}")
    
    except Exception as e:
        print(f"   Error inspecting client: {e}")
    
    # Check environment variables that might affect endpoint
    print(f"\n🌍 Environment variables:")
    env_vars = [
        'RUNWAY_API_BASE',
        'RUNWAY_BASE_URL', 
        'RUNWAY_ENDPOINT',
        'RUNWAY_API_URL',
        'RUNWAY_ENV',
        'RUNWAY_ENVIRONMENT'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        print(f"   {var}: {value if value else 'Not set'}")

if __name__ == "__main__":
    debug_runway_client() 