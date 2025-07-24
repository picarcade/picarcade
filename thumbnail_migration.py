#!/usr/bin/env python3
"""
Thumbnail Migration Script
Generates thumbnails for existing image references that don't have them.
Run this after deploying the updated storage service.
"""

import asyncio
import aiohttp
from PIL import Image
import io
from app.core.database import SupabaseManager
from app.services.storage import storage_service

async def generate_thumbnail_for_reference(reference_data):
    """Generate thumbnail for a single reference"""
    try:
        reference_id = reference_data['id']
        image_url = reference_data['image_url']
        user_id = reference_data['user_id']
        
        print(f"Processing reference {reference_id}: @{reference_data['tag']}")
        
        # Download the original image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    print(f"  ❌ Could not download image: HTTP {response.status}")
                    return False
                
                image_data = await response.read()
        
        # Generate thumbnail
        thumbnail_content = storage_service._generate_thumbnail(image_data, 256)
        
        # Create thumbnail path based on original image path
        # Extract path info from the original URL
        original_path = image_url.split('/storage/v1/object/public/images/')[1].split('?')[0]
        path_parts = original_path.split('/')
        
        # Create thumbnail path: uploads/{user_id}/{day}/thumbs/{filename}
        thumbnail_path = f"{'/'.join(path_parts[:-1])}/thumbs/{path_parts[-1]}"
        
        # Upload thumbnail to storage
        result = storage_service.supabase.storage.from_('images').upload(
            path=thumbnail_path,
            file=thumbnail_content,
            file_options={
                "content-type": "image/jpeg",
                "cache-control": "3600",
                "upsert": "true"
            }
        )
        
        if result:
            # Get thumbnail public URL
            thumbnail_url = storage_service.supabase.storage.from_('images').get_public_url(thumbnail_path)
            
            # Update reference with thumbnail URL
            db = SupabaseManager()
            update_result = db.supabase.table('image_references')\
                .update({'thumbnail_url': thumbnail_url})\
                .eq('id', reference_id)\
                .execute()
            
            if update_result.data:
                print(f"  ✅ Generated thumbnail: {thumbnail_url}")
                return True
            else:
                print(f"  ❌ Failed to update reference with thumbnail URL")
                return False
        else:
            print(f"  ❌ Failed to upload thumbnail")
            return False
            
    except Exception as e:
        print(f"  ❌ Error processing reference {reference_id}: {e}")
        return False

async def migrate_thumbnails():
    """Main migration function"""
    db = SupabaseManager()
    
    # Get all references without thumbnails
    result = db.supabase.table('image_references')\
        .select('*')\
        .is_('thumbnail_url', 'null')\
        .execute()
    
    references = result.data or []
    total_count = len(references)
    
    if total_count == 0:
        print("✅ No references need thumbnail generation")
        return
    
    print(f"🔄 Found {total_count} references without thumbnails")
    print("Starting thumbnail generation...")
    
    success_count = 0
    failed_count = 0
    
    # Process references in batches to avoid overwhelming the API
    batch_size = 5
    for i in range(0, total_count, batch_size):
        batch = references[i:i + batch_size]
        
        # Process batch concurrently
        tasks = [generate_thumbnail_for_reference(ref) for ref in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
            elif result:
                success_count += 1
            else:
                failed_count += 1
        
        print(f"Processed {min(i + batch_size, total_count)}/{total_count} references...")
        
        # Small delay between batches
        await asyncio.sleep(1)
    
    print(f"\n📊 Migration Complete:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  📈 Success Rate: {(success_count/total_count)*100:.1f}%")

if __name__ == "__main__":
    print("🖼️  Thumbnail Migration Script")
    print("=" * 40)
    asyncio.run(migrate_thumbnails()) 