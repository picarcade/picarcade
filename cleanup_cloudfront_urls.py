#!/usr/bin/env python3
"""
Cleanup Cloudfront URLs Script
Removes generation history entries with expired cloudfront.net URLs from Runway.
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

async def cleanup_cloudfront_urls():
    """Clean up cloudfront.net URLs from generation history"""
    db_manager = SupabaseManager()
    
    print("🧹 Cleaning up CloudFront URLs from Runway")
    print("=" * 50)
    
    try:
        # Get all generation history entries with cloudfront.net URLs
        result = db_manager.supabase.table("generation_history")\
            .select("id, generation_id, output_url, created_at")\
            .like("output_url", "%cloudfront.net%")\
            .execute()
        
        cloudfront_entries = result.data
        print(f"🔍 Found {len(cloudfront_entries)} entries with cloudfront.net URLs")
        
        if not cloudfront_entries:
            print("✅ No cloudfront.net URLs found")
            return
        
        # Check which URLs are still accessible
        broken_entries = []
        working_entries = []
        
        async with aiohttp.ClientSession() as session:
            for entry in cloudfront_entries:
                print(f"   Checking: {entry['generation_id']} ({entry['created_at']})")
                is_accessible = await check_url_accessibility(entry['output_url'], session)
                
                if is_accessible:
                    working_entries.append(entry)
                    print(f"   ✅ Working: {entry['generation_id']}")
                else:
                    broken_entries.append(entry)
                    print(f"   ❌ Broken: {entry['generation_id']}")
        
        print(f"\n📊 Results:")
        print(f"   ✅ Working cloudfront URLs: {len(working_entries)}")
        print(f"   ❌ Broken cloudfront URLs: {len(broken_entries)}")
        
        # Delete broken entries
        if broken_entries:
            print(f"\n🗑️ Deleting {len(broken_entries)} broken entries...")
            
            for entry in broken_entries:
                delete_result = db_manager.supabase.table("generation_history")\
                    .delete()\
                    .eq("id", entry["id"])\
                    .execute()
                
                print(f"   ❌ Deleted generation {entry['generation_id']} (created: {entry['created_at']})")
        
        if working_entries:
            print(f"\n⚠️ Warning: {len(working_entries)} cloudfront URLs are still working but will expire eventually.")
            print("   These will be handled automatically by the new permanent storage system.")
        
        print(f"\n✅ CloudFront cleanup complete!")
        
    except Exception as e:
        print(f"❌ Error during cloudfront cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_cloudfront_urls()) 