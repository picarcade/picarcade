import re
import os
from typing import List, Optional, Dict, Any
from app.models.generation import ReferenceImage
from app.core.database import SupabaseManager
import openai

class ReferenceService:
    """Service for handling reference images and @mentions"""
    
    @staticmethod
    async def analyze_image_with_vlm(image_url: str) -> str:
        """
        Analyze an image using OpenAI's vision model to generate a descriptive tag
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            A two-word descriptor separated by underscore (e.g., "man_horse", "castle_sunset")
        """
        try:
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this image and provide a brief 2-word description separated by an underscore. Focus on the main subject and key visual element (e.g., 'man_horse', 'castle_sunset', 'girl_flower', 'dog_park'). Keep it simple and descriptive."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                max_tokens=50
            )
            
            # Extract the tag from response and clean it
            tag = response.choices[0].message.content.strip().lower()
            # Remove any extra text and ensure it's just two words with underscore
            tag = re.sub(r'[^a-z0-9_]', '', tag)
            
            # Ensure it has the format word_word
            if '_' not in tag:
                tag = f"{tag}_scene"
            
            # Limit length
            tag = tag[:20]
            
            print(f"[DEBUG] VLM Analysis: Generated tag '{tag}' for image {image_url}")
            return tag
            
        except Exception as e:
            print(f"[ERROR] VLM analysis failed: {e}")
            # Fallback to a generic tag
            return "working_image"
    
    @staticmethod
    async def auto_tag_working_image(user_id: str, image_url: str) -> str:
        """
        Automatically analyze and tag the working image
        
        Args:
            user_id: User ID
            image_url: URL of the working image
            
        Returns:
            The generated tag for the working image
        """
        try:
            # Generate tag using VLM
            base_tag = await ReferenceService.analyze_image_with_vlm(image_url)
            
            # Check if this exact tag already exists, if so add suffix
            existing_refs = await ReferenceService.get_user_references(user_id)
            existing_tags = [ref['tag'] for ref in existing_refs]
            
            final_tag = base_tag
            counter = 1
            while final_tag in existing_tags:
                final_tag = f"{base_tag}{counter}"
                counter += 1
            
            # Create the reference (marked as temporary)
            await ReferenceService.create_reference(
                user_id=user_id,
                tag=final_tag,
                image_url=image_url,
                display_name=f"Auto-tagged: {final_tag.replace('_', ' ').title()}",
                description="Automatically generated from working image",
                category="general",
                source_type="temporary"  # Mark as temporary for cleanup
            )
            
            print(f"[DEBUG] Auto-tagged working image as '@{final_tag}'")
            return final_tag
            
        except Exception as e:
            print(f"[ERROR] Auto-tagging failed: {e}")
            # Create a fallback working image tag with timestamp
            import time
            fallback_tag = f"working_image{int(time.time() % 10000)}"
            
            try:
                # Try to create fallback reference
                await ReferenceService.create_reference(
                    user_id=user_id,
                    tag=fallback_tag,
                    image_url=image_url,
                    display_name=f"Working Image {fallback_tag[-4:]}",
                    description="Fallback tag for working image",
                    category="general",
                    source_type="temporary"  # Mark as temporary for cleanup
                )
                print(f"[DEBUG] Created fallback working image tag: @{fallback_tag}")
                return fallback_tag
            except Exception as fallback_error:
                print(f"[ERROR] Fallback tagging also failed: {fallback_error}")
                return None
    
    @staticmethod
    async def enhance_prompt_with_working_image(prompt: str, user_id: str, working_image_url: str) -> tuple[str, List[ReferenceImage]]:
        """
        Enhance prompt by auto-tagging working image and adding it to the prompt
        
        Args:
            prompt: Original prompt with user references
            user_id: User ID  
            working_image_url: URL of the current working image
            
        Returns:
            Tuple of (enhanced_prompt, all_reference_images)
        """
        try:
            # First, parse the original user references from the prompt
            print(f"[DEBUG] Parsing original user references from prompt: {prompt}")
            original_references, missing_tags = await ReferenceService.parse_reference_mentions(prompt, user_id)
            print(f"[DEBUG] Found {len(original_references)} original user references")
            if missing_tags:
                print(f"[WARNING] Missing references that need to be created: {missing_tags}")
                print(f"[INFO] To use @{missing_tags[0]}, please tag an image with this name first.")
            
            # Auto-tag the working image
            working_tag = await ReferenceService.auto_tag_working_image(user_id, working_image_url)
            
            if not working_tag:
                # If auto-tagging failed, return original references only
                print(f"[DEBUG] Auto-tagging failed, returning original references only")
                return prompt, original_references
            
            # Add working image reference to the prompt
            # Insert it naturally into the prompt based on the type of request
            if "change" in prompt.lower() and "face" in prompt.lower():
                # Face change requests: "Change the face to @skelton" -> "Change the face to @skelton in the scene from @working_tag"
                enhanced_prompt = f"{prompt} in the scene from @{working_tag}"
            elif "add" in prompt.lower() and any(ref in prompt.lower() for ref in ["@" + ref.tag for ref in original_references]):
                # Adding character to scene: "Add @charlie" -> "Add @charlie to the scene in @working_tag"
                enhanced_prompt = f"{prompt} to the scene in @{working_tag}"
            elif "to be" in prompt.lower():
                # "Add @charlie to be playing on the field" -> "Add @charlie to be playing on the field with @working_tag"
                enhanced_prompt = f"{prompt} with @{working_tag}"
            elif "add" in prompt.lower():
                # "Add @charlie playing" -> "Add @charlie playing on @working_tag"  
                enhanced_prompt = f"{prompt} on @{working_tag}"
            else:
                # Generic enhancement
                enhanced_prompt = f"{prompt} with @{working_tag}"
            
            # Add scene composition instruction (but don't conflict with transformations)
            if len(original_references) > 0:
                if "change" in prompt.lower() and ("face" in prompt.lower() or "head" in prompt.lower()):
                    # For face/head changes, preserve everything except the face
                    enhanced_prompt += f". Keep the body, pose, and background from @{working_tag}"
                    print(f"[DEBUG] Added partial preservation for face change with @{working_tag}")
                else:
                    # For other operations, maintain general composition
                    enhanced_prompt += f". Use the composition and setting from @{working_tag}"
                    print(f"[DEBUG] Added composition guidance for @{working_tag}")
            
            print(f"[DEBUG] Enhanced prompt: '{prompt}' -> '{enhanced_prompt}'")
            
            # Create working image reference object
            working_image_ref = ReferenceImage(uri=working_image_url, tag=working_tag)
            
            # Combine original user references with working image reference
            all_references = original_references + [working_image_ref]
            print(f"[DEBUG] Total references: {len(all_references)} (original: {len(original_references)}, working: 1)")
            
            # Debug log all references
            for ref in all_references:
                print(f"[DEBUG] Reference: @{ref.tag} -> {ref.uri}")
            
            return enhanced_prompt, all_references
            
        except Exception as e:
            print(f"[ERROR] Prompt enhancement failed: {e}")
            # Fallback to original behavior
            original_references, missing_tags = await ReferenceService.parse_reference_mentions(prompt, user_id)
            if missing_tags:
                print(f"[WARNING] Missing references in fallback: {missing_tags}")
            return prompt, original_references
    
    @staticmethod
    async def parse_reference_mentions(prompt: str, user_id: str) -> tuple[List[ReferenceImage], List[str]]:
        """
        Parse @mentions in prompt and return reference images
        
        Args:
            prompt: User's prompt containing @mentions
            user_id: User ID to fetch their references
            
        Returns:
            Tuple of (List of ReferenceImage objects for found tags, List of missing tag names)
        """
        # Find all @mentions in the prompt
        mentions = re.findall(r'@(\w+)', prompt)
        
        if not mentions:
            return [], []
        
        reference_images = []
        missing_tags = []
        
        # Fetch user's references from database
        db = SupabaseManager()
        
        for tag in mentions:
            try:
                # Query image_references table for this user and tag
                result = db.supabase.table('image_references').select('*').eq('user_id', user_id).eq('tag', tag).execute()
                
                if result.data:
                    ref_data = result.data[0]
                    reference_images.append(ReferenceImage(
                        uri=ref_data['image_url'],
                        tag=ref_data['tag']
                    ))
                    print(f"[DEBUG] Found reference for @{tag}: {ref_data['image_url']}")
                    
                    # Track usage
                    await ReferenceService.track_reference_usage(ref_data['id'], None)  # generation_id will be added later
                else:
                    print(f"[WARNING] No reference found in database for tag '@{tag}' for user {user_id}")
                    missing_tags.append(tag)
                    
            except Exception as e:
                print(f"[ERROR] Database error while looking up reference '@{tag}': {e}")
                missing_tags.append(tag)
                continue
        
        return reference_images, missing_tags
    
    @staticmethod
    def has_references(prompt: str) -> bool:
        """Check if prompt contains @mentions"""
        return bool(re.search(r'@\w+', prompt))
    
    @staticmethod
    async def create_reference(user_id: str, tag: str, image_url: str, 
                              display_name: Optional[str] = None,
                              description: Optional[str] = None,
                              category: str = "general",
                              source_type: str = "uploaded") -> Dict[str, Any]:
        """Create a new reference"""
        db = SupabaseManager()
        
        reference_data = {
            'user_id': user_id,
            'tag': tag,
            'display_name': display_name or tag,
            'image_url': image_url,
            'description': description,
            'category': category,
            'source_type': source_type,
            'created_at': 'now()',
            'updated_at': 'now()'
        }
        
        result = db.supabase.table('image_references').insert(reference_data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def update_reference(user_id: str, old_tag: str, 
                              new_tag: Optional[str] = None,
                              display_name: Optional[str] = None,
                              description: Optional[str] = None,
                              category: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing reference"""
        db = SupabaseManager()
        
        try:
            # Get the current reference
            current_result = db.supabase.table('image_references').select('*').eq('user_id', user_id).eq('tag', old_tag).execute()
            
            if not current_result.data:
                raise Exception(f"Reference with tag '{old_tag}' not found")
            
            current_ref = current_result.data[0]
            
            # Prepare update data - only update provided fields
            update_data = {'updated_at': 'now()'}
            
            if new_tag is not None and new_tag != old_tag:
                update_data['tag'] = new_tag
            if display_name is not None:
                update_data['display_name'] = display_name
            if description is not None:
                update_data['description'] = description
            if category is not None:
                update_data['category'] = category
            
            # Update the reference
            result = db.supabase.table('image_references').update(update_data).eq('user_id', user_id).eq('tag', old_tag).execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"[ERROR] Could not update reference @{old_tag}: {e}")
            raise e
    
    @staticmethod
    async def get_user_references(user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all references for a user"""
        db = SupabaseManager()
        
        query = db.supabase.table('image_references').select('*').eq('user_id', user_id)
        
        if category and category != 'all':
            query = query.eq('category', category)
            
        result = query.order('created_at', desc=True).execute()
        return result.data or []
    
    @staticmethod
    async def delete_reference(user_id: str, tag: str) -> bool:
        """Delete a reference by tag"""
        db = SupabaseManager()
        
        try:
            result = db.supabase.table('image_references').delete().eq('user_id', user_id).eq('tag', tag).execute()
            return bool(result.data)
        except Exception as e:
            print(f"[ERROR] Could not delete reference @{tag}: {e}")
            return False
    
    @staticmethod
    async def track_reference_usage(reference_id: str, generation_id: str):
        """Track when a reference is used"""
        if not generation_id:
            return  # Skip if no generation_id yet
            
        db = SupabaseManager()
        
        usage_data = {
            'reference_id': reference_id,
            'generation_id': generation_id,
            'used_at': 'now()'
        }
        
        try:
            db.supabase.table('reference_usage').insert(usage_data).execute()
        except Exception as e:
            print(f"[WARNING] Could not track reference usage: {e}")
    
    @staticmethod
    async def cleanup_temporary_references(user_id: str, generation_id: str):
        """Clean up temporary references created for a specific generation"""
        db = SupabaseManager()
        
        try:
            # Get all temporary references for this user
            result = db.supabase.table('image_references')\
                .select('id, tag')\
                .eq('user_id', user_id)\
                .eq('source_type', 'temporary')\
                .execute()
            
            if result.data:
                # Delete temporary references
                for ref in result.data:
                    db.supabase.table('image_references')\
                        .delete()\
                        .eq('id', ref['id'])\
                        .execute()
                    print(f"[DEBUG] Cleaned up temporary reference @{ref['tag']}")
                
                print(f"[DEBUG] Cleaned up {len(result.data)} temporary references for generation {generation_id}")
        except Exception as e:
            print(f"[ERROR] Could not cleanup temporary references: {e}")