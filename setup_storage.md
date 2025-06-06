# Supabase Storage Setup for Image Uploads

## Overview
This guide explains how to set up Supabase Storage for handling image uploads in your Pictures application.

## Storage Bucket Setup

### Option 1: Using Supabase Dashboard (Recommended)

1. **Navigate to Storage**
   - Go to your Supabase project dashboard
   - Click on "Storage" in the left sidebar

2. **Create Storage Bucket**
   - Click "Create bucket"
   - Name: `images`
   - Make it public: **Yes** (checked)
   - File size limit: `50 MB`
   - Allowed MIME types: `image/jpeg, image/png, image/webp, image/gif`

3. **Set Storage Policies**
   - Click on the `images` bucket
   - Go to "Policies" tab
   - Add the following policies:

   **Policy 1: Allow public read access**
   ```sql
   CREATE POLICY "Public read access" ON storage.objects
   FOR SELECT USING (bucket_id = 'images');
   ```

   **Policy 2: Allow authenticated uploads**
   ```sql
   CREATE POLICY "Allow uploads" ON storage.objects
   FOR INSERT WITH CHECK (bucket_id = 'images');
   ```

   **Policy 3: Allow users to delete their own files**
   ```sql
   CREATE POLICY "Allow delete own files" ON storage.objects
   FOR DELETE USING (bucket_id = 'images');
   ```

### Option 2: Using SQL Editor

Run this SQL in your Supabase SQL Editor:

```sql
-- Create storage bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('images', 'images', true, 52428800, '{"image/jpeg","image/png","image/webp","image/gif"}');

-- Create policies
CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'images');

CREATE POLICY "Allow uploads" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'images');

CREATE POLICY "Allow delete own files" ON storage.objects
FOR DELETE USING (bucket_id = 'images');
```

## Environment Variables

Make sure your `.env` file contains:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

## Backend Dependencies

Install required Python packages:

```bash
pip install pillow python-multipart
```

## Testing the Setup

1. **Start your backend server**:
   ```bash
   cd /path/to/your/backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start your frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test image upload**:
   - Open your application in the browser
   - Click the paperclip (📎) icon
   - Select one or more images
   - Check that they appear in the uploaded images section
   - Verify images are stored in your Supabase Storage bucket

## Features Implemented

✅ **Image Upload**: Click the paperclip icon to upload images  
✅ **Multiple Files**: Upload multiple images at once  
✅ **Image Preview**: See uploaded images with thumbnails  
✅ **Auto-resize**: Images automatically resized to max 2048px  
✅ **File Validation**: Only image files (JPEG, PNG, WebP, GIF) allowed  
✅ **Progress Indicators**: Loading states during upload  
✅ **Remove Images**: Click X to remove uploaded images  
✅ **Supabase Storage**: Secure storage with public URLs  
✅ **Organized Storage**: Files organized by user and date  

## Troubleshooting

### Storage bucket not found
- Verify the bucket was created successfully
- Check that it's named exactly `images`
- Ensure it's set to public

### Upload errors
- Check your service role key is correct
- Verify file size is under 50MB
- Ensure file is a valid image format

### Permission errors
- Verify storage policies are set correctly
- Check that RLS is enabled on storage.objects

### Network errors
- Verify your backend is running on port 8000
- Check CORS settings allow your frontend domain
- Ensure Supabase URL and keys are correct

## File Organization

Images are stored with this structure:
```
/images/uploads/{user_id}/{day_timestamp}/{unique_filename}.{ext}
```

Example:
```
/images/uploads/user_1234567890/19734/a1b2c3d4e5f6.jpg
```

This organization helps with:
- User-specific file management
- Date-based organization
- Avoiding filename conflicts
- Easy cleanup and maintenance 