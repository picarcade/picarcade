"""
Witty Message Generation Service

Generates engaging, contextual messages for asset generation using Anthropic Claude.
These messages are displayed during generation to keep users engaged and informed.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional
import replicate

logger = logging.getLogger(__name__)


class WittyMessageService:
    """
    Service for generating witty, contextual messages for asset generation
    """
    
    def __init__(self):
        # Use Anthropic Claude 4 Sonnet via Replicate for message generation
        self.model = "anthropic/claude-4-sonnet"
        
    async def generate_witty_messages(
        self, 
        user_prompt: str,
        prompt_type: str,
        estimated_time: int = 30,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate 10 witty, contextual messages about the user's request
        
        Args:
            user_prompt: The user's original prompt
            prompt_type: Type of generation (NEW_IMAGE, EDIT_IMAGE, etc.)
            estimated_time: Estimated time in seconds for generation
            context: Additional context about the generation
            
        Returns:
            List of 10 witty messages
        """
        
        try:
            # Build context-aware prompt for message generation
            system_prompt = self._build_system_prompt(prompt_type, estimated_time, context)
            
            # Create user prompt for message generation
            user_message = self._build_user_message(user_prompt, prompt_type, context)
            
            # Generate messages using Claude
            combined_prompt = f"{system_prompt}\n\n{user_message}"
            messages = await self._generate_with_claude(combined_prompt, "")
            
            # Parse and validate the response
            witty_messages = self._parse_messages(messages)
            
            # Ensure we have exactly 10 messages
            if len(witty_messages) < 10:
                # Generate additional messages if needed
                additional_messages = await self._generate_additional_messages(
                    user_prompt, prompt_type, 10 - len(witty_messages), context
                )
                witty_messages.extend(additional_messages)
            
            # Trim to exactly 10 messages
            witty_messages = witty_messages[:10]
            
            logger.info(f"Generated {len(witty_messages)} witty messages for prompt type: {prompt_type}")
            return witty_messages
            
        except Exception as e:
            logger.error(f"Error generating witty messages: {e}")
            # Return fallback messages
            return self._get_fallback_messages(prompt_type, estimated_time)
    
    def _build_system_prompt(self, prompt_type: str, estimated_time: int, context: Optional[Dict[str, Any]]) -> str:
        """Build the system prompt for message generation"""
        
        base_prompt = f"""You are a witty, engaging AI assistant that generates fun, contextual messages for users while they wait for their AI-generated content to be created.

Your task is to generate exactly 10 engaging messages that:
1. Are specific to what the user is requesting
2. Show enthusiasm and excitement about their creative vision
3. Include witty humor and personality
4. Mention the estimated time ({estimated_time} seconds) in a fun, contextual way
5. Vary in tone and style to keep things interesting
6. Are encouraging and positive
7. Reference the user's specific request and context

Generation Type: {prompt_type}

Guidelines:
- Keep messages under 100 characters each
- Make them feel personal and specific to the request
- Include time references naturally (e.g., "This might take {estimated_time} seconds, but it'll be worth the wait")
- Be encouraging about their creative choices
- NO EMOJIS - keep it clean and professional
- Make specific references to what they're creating
- Be witty and clever, not just generic encouragement
- Consider the context of their request and any previous work
- Be specific about what they're creating (e.g., "Your portrait is getting a makeover", "That landscape is about to get epic")

Example styles:
- "Your portrait is getting a makeover"
- "Great call adding this horse, it's going to look special"
- "This might take around {estimated_time} seconds, but it'll be worth the wait"
- "I liked your hair before, but this is going to look even better"
- "Your creative vision is coming to life"

Return exactly 10 messages as a JSON array of strings."""

        # Add context-specific instructions
        if context:
            if context.get("is_edit"):
                base_prompt += "\n\nThis is an edit operation - focus on improvements and enhancements to their existing work."
            if context.get("has_references"):
                base_prompt += "\n\nThis uses reference images - mention how the references will help create something special and unique."
            if context.get("is_video"):
                base_prompt += "\n\nThis is video generation - mention the dynamic nature and movement that will bring their vision to life."
            if context.get("total_references"):
                base_prompt += f"\n\nUsing {context.get('total_references')} reference(s) to ensure consistency and quality."
            
            # Add working image context for more specific messages
            if context.get("working_image"):
                base_prompt += "\n\nThe user is editing an existing image - reference their previous work and improvements."
            if context.get("working_video"):
                base_prompt += "\n\nThe user is editing an existing video - reference their previous work and the dynamic improvements."
            if context.get("uploaded_images"):
                base_prompt += f"\n\nThe user uploaded {len(context.get('uploaded_images', []))} image(s) - reference their specific content and how it will enhance the result."
        
        return base_prompt
    
    def _build_user_message(self, user_prompt: str, prompt_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the user message for message generation"""
        
        context_info = ""
        if context:
            if context.get("working_image"):
                context_info += f"\nWorking with existing image: {context.get('working_image', '')[:50]}..."
            if context.get("working_video"):
                context_info += f"\nWorking with existing video: {context.get('working_video', '')[:50]}..."
            if context.get("uploaded_images"):
                context_info += f"\nUploaded {len(context.get('uploaded_images', []))} image(s) for reference"
            if context.get("total_references"):
                context_info += f"\nUsing {context.get('total_references')} reference(s) from their library"
        
        return f"""Generate 10 witty messages for this user request:

User's Request: "{user_prompt}"
Generation Type: {prompt_type}{context_info}

Please analyze what they're asking for and create engaging, contextual messages that will keep them excited while they wait. Make the messages specific to their request and show that you understand what they're trying to create. Be witty and clever, referencing their specific situation.

Focus on what they're actually creating - if they mentioned specific objects, people, scenes, or actions, reference those directly. Make the messages feel like they're about their specific request, not generic encouragement.

Return the messages as a JSON array of exactly 10 strings."""
    
    async def _generate_with_claude(self, prompt: str, unused_param: str = "") -> str:
        """Generate messages using Claude via Replicate"""
        
        try:
            # Use Replicate to call Claude
            output = replicate.run(
                self.model,
                input={
                    "prompt": prompt,
                    "max_tokens": 1024,
                    "temperature": 0.8
                }
            )
            
            # Replicate returns a list of message parts, join them
            if isinstance(output, list):
                return "".join(output)
            else:
                return str(output)
                
        except Exception as e:
            logger.error(f"Error calling Claude for witty messages: {e}")
            raise
    
    def _parse_messages(self, response: str) -> List[str]:
        """Parse the Claude response to extract messages"""
        
        try:
            # Try to extract JSON from the response
            # Look for JSON array pattern
            import re
            
            # Find JSON array in the response
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                messages = json.loads(json_str)
                
                # Validate messages
                if isinstance(messages, list):
                    # Clean and validate each message
                    cleaned_messages = []
                    for msg in messages:
                        if isinstance(msg, str) and msg.strip():
                            cleaned_messages.append(msg.strip())
                    
                    return cleaned_messages
            
            # Fallback: try to extract messages line by line
            lines = response.split('\n')
            messages = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('```'):
                    # Remove quotes and numbering
                    line = re.sub(r'^["\']?\d*\.?\s*["\']?', '', line)
                    line = re.sub(r'["\']$', '', line)
                    if line and len(line) < 150:  # Reasonable length
                        messages.append(line)
            
            return messages[:10]  # Limit to 10
            
        except Exception as e:
            logger.error(f"Error parsing witty messages: {e}")
            return []
    
    async def _generate_additional_messages(self, user_prompt: str, prompt_type: str, count: int, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate additional messages if we don't have enough"""
        
        try:
            system_prompt = f"""Generate exactly {count} more witty, engaging messages for AI content generation.

Keep them under 100 characters each, specific to the user's request, and include time references naturally.

Generation Type: {prompt_type}

Return as a JSON array of strings."""

            user_message = f"Generate {count} more messages for: {user_prompt}"
            if context:
                if context.get("working_image"):
                    user_message += f" (editing existing image)"
                if context.get("working_video"):
                    user_message += f" (editing existing video)"
                if context.get("uploaded_images"):
                    user_message += f" (with {len(context.get('uploaded_images', []))} uploaded image(s))"
            
            # Combine system and user message for single prompt
            combined_prompt = f"{system_prompt}\n\n{user_message}"
            response = await self._generate_with_claude(combined_prompt, "")
            messages = self._parse_messages(response)
            
            return messages[:count]
            
        except Exception as e:
            logger.error(f"Error generating additional messages: {e}")
            return []
    
    def _get_fallback_messages(self, prompt_type: str, estimated_time: int) -> List[str]:
        """Return fallback messages if generation fails"""
        
        base_messages = [
            f"Your creation is taking shape",
            f"This might take around {estimated_time} seconds, but it'll be worth the wait",
            "Your vision is coming to life",
            "Working some AI magic here",
            "Almost there! Your masterpiece is being crafted",
            f"Just {estimated_time} seconds until your creation is ready",
            "The AI is putting the finishing touches on your request",
            "Something special is being generated just for you",
            "Your imagination is becoming reality",
            "The wait will be worth it - this is going to look incredible!"
        ]
        
        # Customize based on prompt type
        if "EDIT" in prompt_type:
            base_messages[0] = "Enhancing your creation with some AI magic"
            base_messages[2] = "Your improvements are being applied"
        elif "VIDEO" in prompt_type:
            base_messages[0] = "Bringing your vision to life with motion"
            base_messages[2] = "Your video is being crafted frame by frame"
        
        return base_messages


# Global instance
witty_message_service = WittyMessageService() 