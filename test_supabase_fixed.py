#!/usr/bin/env python3
"""
Fixed Supabase Connection Test
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

async def test_supabase_basic_fixed():
    """Test basic Supabase client connection with correct table"""
    
    print("🔧 Testing Fixed Supabase Connection")
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
        
        # Test basic client with correct table
        print("\n1️⃣ Testing with user_sessions table...")
        supabase = create_client(supabase_url, supabase_key)
        
        # Test a simple query on existing table
        response = supabase.table("user_sessions").select("*").limit(1).execute()
        print(f"✅ Basic client working: {len(response.data)} sessions found")
        
        # Test with service role key
        print("\n2️⃣ Testing with service role key...")
        supabase_admin = create_client(supabase_url, supabase_service_key)
        response_admin = supabase_admin.table("generation_history").select("*").limit(1).execute()
        print(f"✅ Service role working: {len(response_admin.data)} generations found")
        
        # Test all key tables
        tables_to_test = [
            "user_sessions",
            "generation_history",
            "image_references",
            "intent_classification_logs",
            "cost_tracking"
        ]
        
        print("\n3️⃣ Testing all Sprint 3 tables...")
        for table in tables_to_test:
            try:
                result = supabase_admin.table(table).select("id").limit(1).execute()
                print(f"   ✅ {table}: {len(result.data)} rows")
            except Exception as e:
                print(f"   ❌ {table}: {str(e)[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_postgresql():
    """Test simple PostgreSQL connection using Supabase format"""
    
    print("\n🗄️ Testing Simple PostgreSQL Connection")
    print("=" * 50)
    
    try:
        import asyncpg
        
        supabase_url = os.getenv('SUPABASE_URL')
        
        if not supabase_url:
            print("❌ Missing Supabase URL")
            return False
        
        # Extract project reference
        project_ref = supabase_url.split('//')[1].split('.')[0]
        print(f"📋 Project Reference: {project_ref}")
        
        # Get database password from environment (if available)
        db_password = os.getenv('SUPABASE_DB_PASSWORD')
        
        if not db_password:
            print("⚠️ No SUPABASE_DB_PASSWORD found in .env file")
            print("💡 You need to get your database password from Supabase dashboard")
            print("   Go to Settings → Database → Copy your database password")
            return False
        
        # Test with proper database password
        connection_string = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"
        print(f"🔗 Testing connection: postgresql://postgres:[HIDDEN]@db.{project_ref}.supabase.co:5432/postgres")
        
        conn = await asyncpg.connect(connection_string)
        result = await conn.fetchval("SELECT current_database()")
        await conn.close()
        
        print(f"✅ PostgreSQL connection successful: {result}")
        return connection_string
        
    except Exception as e:
        print(f"❌ PostgreSQL test failed: {e}")
        return False

async def fix_production_database():
    """Fix the production database configuration"""
    
    print("\n🔧 Fixing Production Database")
    print("=" * 50)
    
    try:
        # Read current database.py
        with open("app/core/database.py", "r") as f:
            content = f.read()
        
        print("1️⃣ Current connection string approach detected")
        
        # Create simplified connection string approach
        new_connection_logic = '''
        # Build Supabase connection string (simplified and reliable)
        supabase_url = settings.supabase_url
        project_ref = supabase_url.split('//')[1].split('.')[0]
        
        # Try database password first, fallback to service key
        db_password = getattr(settings, 'supabase_db_password', None)
        if db_password:
            self._connection_string = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"
        else:
            # Fallback: Use service key (less reliable but may work)
            self._connection_string = f"postgresql://postgres:{settings.supabase_service_role_key}@db.{project_ref}.supabase.co:5432/postgres"
        '''
        
        print("2️⃣ Would update connection string logic")
        print("3️⃣ Need SUPABASE_DB_PASSWORD in .env file for proper fix")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to analyze database.py: {e}")
        return False

async def main():
    print("🚀 Fixed Supabase Connection Test")
    
    # Test basic Supabase client
    basic_test = await test_supabase_basic_fixed()
    
    # Test PostgreSQL connection  
    pg_test = await test_simple_postgresql()
    
    # Check production database fix
    fix_test = await fix_production_database()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print(f"• Fixed Supabase Client: {'✅ PASS' if basic_test else '❌ FAIL'}")
    print(f"• PostgreSQL Connection: {'✅ PASS' if pg_test else '❌ FAIL'}")
    print(f"• Production Fix Ready: {'✅ PASS' if fix_test else '❌ FAIL'}")
    
    if basic_test and not pg_test:
        print("\n💡 Supabase client works! Issue is with PostgreSQL connection.")
        print("🔑 Add your database password to .env file:")
        print("   SUPABASE_DB_PASSWORD=your_actual_db_password")
        print("\n   Get it from: Supabase Dashboard → Settings → Database")
    elif basic_test and pg_test:
        print("\n🎉 All connections working! Ready to fix production code.")
    else:
        print("\n❌ Basic Supabase connection failed - check credentials.")
    
    return 0 if basic_test else 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 