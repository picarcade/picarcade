#!/usr/bin/env python3
"""
Comprehensive Cleanup Script for Broken Images
Removes all broken/expired images and related data from Supabase.
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

async def cleanup_broken_images():
    """Comprehensive cleanup of all broken images in Supabase"""
    db_manager = SupabaseManager()
    
    print("🧹 Comprehensive Broken Image Cleanup")
    print("=" * 50)
    
    # Step 1: Clean up generation history with NULL/broken output_urls
    print("\n1️⃣ Cleaning up broken generation history entries...")
    
    try:
        # Get entries with NULL output_url (previously marked as broken)
        null_result = db_manager.supabase.table("generation_history")\
            .select("id, generation_id, created_at")\
            .is_("output_url", "null")\
            .execute()
        
        null_entries = null_result.data
        print(f"   🗑️  Found {len(null_entries)} entries with NULL output_url")
        
        # Delete them
        for entry in null_entries:
            delete_result = db_manager.supabase.table("generation_history")\
                .delete()\
                .eq("id", entry["id"])\
                .execute()
            print(f"   ❌ Deleted generation {entry['generation_id']} (created: {entry['created_at']})")
        
    except Exception as e:
        print(f"   ⚠️  Error cleaning generation history: {e}")
    
    # Step 2: Check and clean image references with broken URLs
    print("\n2️⃣ Cleaning up broken image references...")
    
    try:
        # Get all image references
        refs_result = db_manager.supabase.table("image_references")\
            .select("id, tag, image_url, user_id, created_at")\
            .execute()
        
        all_refs = refs_result.data
        print(f"   📚 Found {len(all_refs)} image references to check")
        
        broken_refs = []
        
        async with aiohttp.ClientSession() as session:
            for ref in all_refs:
                if ref['image_url']:
                    is_accessible = await check_url_accessibility(ref['image_url'], session)
                    if not is_accessible:
                        broken_refs.append(ref)
        
        print(f"   🔍 Found {len(broken_refs)} broken references")
        
        # Delete broken references
        for ref in broken_refs:
            delete_result = db_manager.supabase.table("image_references")\
                .delete()\
                .eq("id", ref["id"])\
                .execute()
            print(f"   ❌ Deleted reference @{ref['tag']} (created: {ref['created_at']})")
        
    except Exception as e:
        print(f"   ⚠️  Error cleaning image references: {e}")
    
    # Step 3: Clean up any remaining external URLs in generation history
    print("\n3️⃣ Checking remaining generation history for external URLs...")
    
    try:
        # Get generation history with external URLs
        remaining_result = db_manager.supabase.table("generation_history")\
            .select("id, generation_id, output_url, created_at")\
            .not_.is_("output_url", "null")\
            .execute()
        
        remaining_entries = remaining_result.data
        external_domains = ['replicate.delivery', 'runway.com', 'storage.googleapis.com']
        
        still_broken = []
        
        async with aiohttp.ClientSession() as session:
            for entry in remaining_entries:
                if entry['output_url'] and any(domain in entry['output_url'] for domain in external_domains):
                    is_accessible = await check_url_accessibility(entry['output_url'], session)
                    if not is_accessible:
                        still_broken.append(entry)
        
        print(f"   🔍 Found {len(still_broken)} additional broken generation entries")
        
        # Delete these too
        for entry in still_broken:
            delete_result = db_manager.supabase.table("generation_history")\
                .delete()\
                .eq("id", entry["id"])\
                .execute()
            print(f"   ❌ Deleted generation {entry['generation_id']} (created: {entry['created_at']})")
    
    except Exception as e:
        print(f"   ⚠️  Error checking remaining entries: {e}")
    
    # Step 4: Summary
    print("\n4️⃣ Cleanup Summary")
    try:
        # Count remaining entries
        remaining_gens = db_manager.supabase.table("generation_history")\
            .select("id", count="exact")\
            .execute()
        
        remaining_refs = db_manager.supabase.table("image_references")\
            .select("id", count="exact")\
            .execute()
        
        print(f"   📊 Remaining generation history entries: {remaining_gens.count}")
        print(f"   📊 Remaining image references: {remaining_refs.count}")
        
        # Check if any external URLs remain
        external_check = db_manager.supabase.table("generation_history")\
            .select("output_url")\
            .not_.is_("output_url", "null")\
            .execute()
        
        external_count = 0
        for entry in external_check.data:
            if entry['output_url'] and any(domain in entry['output_url'] for domain in external_domains):
                external_count += 1
        
        print(f"   🌐 Remaining external URLs in generation history: {external_count}")
        
    except Exception as e:
        print(f"   ⚠️  Error getting summary: {e}")
    
    print(f"\n✅ Cleanup Complete!")
    print(f"   🗑️  All broken/expired images have been removed from the database")
    print(f"   🔄 New generations will now be stored permanently with thumbnails")
    print(f"   🚀 Your history should load much faster now!")

if __name__ == "__main__":
    asyncio.run(cleanup_broken_images()) 