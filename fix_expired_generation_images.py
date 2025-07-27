#!/usr/bin/env python3
"""
Fix Expired Generation Images Script
Identifies and handles generation history entries with expired external URLs.
Since the URLs are already expired, we can't recover the images, but we can clean up the database.
"""

import asyncio
import aiohttp
from app.core.database import SupabaseManager

async def check_url_accessibility(url: str, session: aiohttp.ClientSession) -> bool:
    """Check if a URL is still accessible"""
    try:
        async with session.head(url, timeout=10) as response:
            return response.status == 200
    except Exception:
        return False

async def fix_expired_images():
    """Find and handle expired generation history images"""
    db_manager = SupabaseManager()
    
    try:
        # Get all generation history entries with external URLs
        print("🔍 Fetching generation history entries...")
        
        result = db_manager.supabase.table("generation_history")\
            .select("id, generation_id, user_id, output_url, created_at")\
            .eq("success", "success")\
            .not_.is_("output_url", "null")\
            .execute()
        
        all_entries = result.data
        print(f"📊 Found {len(all_entries)} successful generation entries")
        
        # Filter for external URLs that might expire
        external_domains = ['replicate.delivery', 'runway.com', 'storage.googleapis.com']
        external_entries = []
        
        for entry in all_entries:
            if entry['output_url'] and any(domain in entry['output_url'] for domain in external_domains):
                external_entries.append(entry)
        
        print(f"🌐 Found {len(external_entries)} entries with external URLs")
        
        if not external_entries:
            print("✅ No external URLs found to check")
            return
        
        # Check which URLs are still accessible
        broken_entries = []
        working_entries = []
        
        print("🔍 Checking URL accessibility...")
        
        async with aiohttp.ClientSession() as session:
            for i, entry in enumerate(external_entries):
                if i % 10 == 0:
                    print(f"   Progress: {i}/{len(external_entries)}")
                
                is_accessible = await check_url_accessibility(entry['output_url'], session)
                
                if is_accessible:
                    working_entries.append(entry)
                else:
                    broken_entries.append(entry)
        
        print(f"\n📊 Results:")
        print(f"   ✅ Working URLs: {len(working_entries)}")
        print(f"   ❌ Broken URLs: {len(broken_entries)}")
        
        # Handle broken entries
        if broken_entries:
            print(f"\n🧹 Handling {len(broken_entries)} broken entries...")
            
            for entry in broken_entries:
                # Option 1: Set output_url to NULL to indicate broken image
                # Option 2: Delete the entry entirely
                # We'll go with Option 1 to preserve the history record
                
                update_result = db_manager.supabase.table("generation_history")\
                    .update({"output_url": None})\
                    .eq("id", entry["id"])\
                    .execute()
                
                print(f"   🔧 Marked entry {entry['generation_id']} as broken (created: {entry['created_at']})")
        
        print(f"\n✅ Cleanup complete!")
        print(f"   📝 {len(broken_entries)} entries marked as having broken images")
        print(f"   🖼️  {len(working_entries)} entries still have working images")
        
        if working_entries:
            print(f"\n⚠️  Recommendation: The {len(working_entries)} working external URLs will eventually expire.")
            print(f"   Consider running the application to generate new images so they get stored permanently.")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    print("🖼️  Fix Expired Generation Images Script")
    print("=" * 50)
    asyncio.run(fix_expired_images()) 