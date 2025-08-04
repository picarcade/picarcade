#!/usr/bin/env python3
"""
Fix Video Storage Script
Recreates the Supabase storage bucket with proper video MIME type support.
Run this if you're getting "mime type video/mp4 is not supported" errors.
"""

import asyncio
from app.services.storage import SupabaseStorageService

async def fix_video_storage():
    """Recreate the storage bucket with video support"""
    print("🔧 Fixing video storage configuration...")
    
    storage_service = SupabaseStorageService()
    
    # Try to recreate the bucket with video support
    success = storage_service._recreate_bucket_with_video_support()
    
    if success:
        print("✅ Successfully recreated storage bucket with video support!")
        print("📝 The bucket now supports the following MIME types:")
        print("   - image/jpeg, image/png, image/webp, image/gif")
        print("   - video/mp4, video/webm, video/mov, video/quicktime, video/avi")
        print("\n🔄 You can now restart your application and video uploads should work.")
    else:
        print("❌ Failed to recreate storage bucket.")
        print("💡 You may need to manually delete and recreate the bucket in the Supabase dashboard.")
        print("   Go to: https://supabase.com/dashboard/project/_/storage/buckets")
        print("   Delete the 'images' bucket and let the application recreate it automatically.")

if __name__ == "__main__":
    asyncio.run(fix_video_storage()) 