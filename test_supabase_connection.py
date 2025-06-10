#!/usr/bin/env python3
"""
Test Supabase Connection and Fix Issues
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_supabase_basic():
    """Test basic Supabase client connection"""
    
    print("🔧 Testing Basic Supabase Connection")
    print("=" * 50)
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY') 
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        print(f"📋 Supabase URL: {supabase_url}")
        print(f"📋 Anon Key: {'✅ SET' if supabase_key else '❌ MISSING'}")
        print(f"📋 Service Key: {'✅ SET' if supabase_service_key else '❌ MISSING'}")
        
        if not all([supabase_url, supabase_key]):
            print("❌ Missing required Supabase credentials")
            return False
        
        # Test basic client
        print("\n1️⃣ Testing Supabase client with anon key...")
        supabase = create_client(supabase_url, supabase_key)
        
        # Test a simple query
        response = supabase.table("sessions").select("*").limit(1).execute()
        print(f"✅ Basic client working: {len(response.data)} rows")
        
        # Test with service role key
        print("\n2️⃣ Testing with service role key...")
        supabase_admin = create_client(supabase_url, supabase_service_key)
        response_admin = supabase_admin.table("sessions").select("*").limit(1).execute()
        print(f"✅ Service role working: {len(response_admin.data)} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_postgresql_connection():
    """Test direct PostgreSQL connection to Supabase"""
    
    print("\n🗄️ Testing Direct PostgreSQL Connection")
    print("=" * 50)
    
    try:
        import asyncpg
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            print("❌ Missing Supabase credentials")
            return False
        
        # Extract project reference from URL
        # URL format: https://icgwpkroorulmsfdiuoh.supabase.co
        project_ref = supabase_url.split('//')[1].split('.')[0]
        print(f"📋 Project Reference: {project_ref}")
        
        # Try different connection string formats
        connection_strings = [
            # Standard Supabase connection string
            f"postgresql://postgres:[YOUR_PASSWORD]@db.{project_ref}.supabase.co:5432/postgres",
            
            # Direct connection (if password known)
            f"postgresql://postgres:{supabase_service_key}@db.{project_ref}.supabase.co:5432/postgres",
            
            # Pooler connection
            f"postgresql://postgres.{project_ref}:{supabase_service_key}@aws-0-{project_ref}.pooler.supabase.com:5432/postgres",
            
            # Alternative pooler format
            f"postgresql://postgres:{supabase_service_key}@aws-0-{project_ref}.pooler.supabase.com:6543/postgres",
        ]
        
        print(f"\n🔗 Testing {len(connection_strings)} connection formats...")
        
        for i, conn_str in enumerate(connection_strings, 1):
            try:
                print(f"\n{i}️⃣ Testing connection format {i}...")
                # Hide the password in logs
                safe_conn_str = conn_str.replace(supabase_service_key, "[HIDDEN]")
                print(f"   Format: {safe_conn_str}")
                
                # Test connection
                conn = await asyncpg.connect(conn_str)
                result = await conn.fetchval("SELECT 1")
                await conn.close()
                
                print(f"   ✅ Connection {i} SUCCESS!")
                return conn_str
                
            except Exception as e:
                print(f"   ❌ Connection {i} failed: {str(e)[:100]}...")
        
        print("❌ All PostgreSQL connection attempts failed")
        return False
        
    except Exception as e:
        print(f"❌ PostgreSQL test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_production_database():
    """Test the production database code"""
    
    print("\n🏭 Testing Production Database Code")
    print("=" * 50)
    
    try:
        from app.core.database import get_database
        
        print("1️⃣ Initializing production database...")
        database = await get_database()
        
        if not database.pool:
            print("❌ Database pool not initialized")
            return False
        
        print("2️⃣ Testing database query...")
        result = await database.fetch_one("SELECT 1 as test")
        print(f"✅ Database query successful: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Production database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_supabase_database_password():
    """Help user get the correct database password"""
    
    print("\n🔑 How to get your Supabase Database Password")
    print("=" * 50)
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to Settings → Database")
    print("3. Look for 'Connection string' or 'Database password'")
    print("4. Copy the password (not the service role key)")
    print("5. The connection string should look like:")
    print("   postgresql://postgres:[YOUR_PASSWORD]@db.[PROJECT].supabase.co:5432/postgres")
    print("\nNote: The database password is different from API keys!")

async def main():
    print("🚀 Supabase Connection Diagnostics")
    
    # Test basic Supabase client
    basic_test = await test_supabase_basic()
    
    # Test PostgreSQL connection
    pg_test = await test_postgresql_connection()
    
    # Test production code
    prod_test = await test_production_database()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print(f"• Basic Supabase Client: {'✅ PASS' if basic_test else '❌ FAIL'}")
    print(f"• PostgreSQL Connection: {'✅ PASS' if pg_test else '❌ FAIL'}")
    print(f"• Production Database: {'✅ PASS' if prod_test else '❌ FAIL'}")
    
    if basic_test and not pg_test:
        print("\n💡 Supabase client works but PostgreSQL connection fails.")
        print("This suggests a database password or connection string issue.")
        get_supabase_database_password()
    elif not basic_test:
        print("\n💡 Basic Supabase connection failed.")
        print("Check your SUPABASE_URL and SUPABASE_KEY in .env file.")
    elif all([basic_test, pg_test, prod_test]):
        print("\n🎉 All Supabase connections working!")
    
    return 0 if prod_test else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 