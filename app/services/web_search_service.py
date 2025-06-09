import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

class WebSearchService:
    """Service for web search integration for celebrity/event styling references"""
    
    def __init__(self):
        self.search_cache = {}  # Simple in-memory cache for development
        self.cache_ttl = 3600  # 1 hour cache
        
        # Celebrity name patterns for better detection
        self.celebrity_patterns = [
            r'\btaylor\s+swift\b',
            r'\bbeyonce\b',
            r'\brihanna\b',
            r'\bjennifer\s+lawrence\b',
            r'\bemma\s+stone\b',
            r'\bbrad\s+pitt\b',
            r'\bleonardo\s+dicaprio\b',
            r'\btom\s+cruise\b',
            r'\bscarlett\s+johansson\b',
            r'\bchris\s+evans\b'
        ]
        
        # Event patterns for styling references
        self.event_patterns = [
            r'\bmet\s+gala\b',
            r'\bgrammy\s+(awards?)?\b',
            r'\boscar\s+(awards?)?\b',
            r'\bcannes\b',
            r'\bred\s+carpet\b',
            r'\bfashion\s+week\b',
            r'\bcoachella\b',
            r'\bvictoria\'?s?\s+secret\b'
        ]
    
    async def should_search_for_reference(self, prompt: str, intent_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Determine if web search is needed for celebrity/event styling
        
        Returns:
            (should_search: bool, search_query: Optional[str])
        """
        
        prompt_lower = prompt.lower()
        
        # Check for celebrity mentions
        for pattern in self.celebrity_patterns:
            if re.search(pattern, prompt_lower):
                celebrity_match = re.search(pattern, prompt_lower)
                celebrity_name = celebrity_match.group(0)
                
                # Check for event context
                for event_pattern in self.event_patterns:
                    if re.search(event_pattern, prompt_lower):
                        event_match = re.search(event_pattern, prompt_lower)
                        event_name = event_match.group(0)
                        search_query = f"{celebrity_name} {event_name} outfit fashion style"
                        return True, search_query
                
                # General celebrity styling
                search_query = f"{celebrity_name} fashion style outfit latest"
                return True, search_query
        
        # Check for event styling without specific celebrity
        for pattern in self.event_patterns:
            if re.search(pattern, prompt_lower):
                event_match = re.search(pattern, prompt_lower)
                event_name = event_match.group(0)
                search_query = f"{event_name} fashion style outfit trends"
                return True, search_query
        
        # Check for virtual try-on patterns that might benefit from web search
        virtual_tryon_patterns = [
            r'try\s+on',
            r'wear\s+this',
            r'put.*in.*outfit',
            r'dress\s+like',
            r'style\s+like'
        ]
        
        for pattern in virtual_tryon_patterns:
            if re.search(pattern, prompt_lower):
                # Extract what they want to try on
                style_match = re.search(r'(try\s+on|wear|dress\s+like|style\s+like)\s+(.+)', prompt_lower)
                if style_match:
                    style_description = style_match.group(2)
                    search_query = f"{style_description} fashion style outfit inspiration"
                    return True, search_query
        
        return False, None
    
    async def search_for_styling_references(self, search_query: str) -> Dict[str, Any]:
        """
        Search for styling references using web search
        
        Args:
            search_query: The search query for styling references
            
        Returns:
            Dictionary containing search results with images and descriptions
        """
        
        # Check cache first
        cache_key = f"style_search_{hash(search_query)}"
        if cache_key in self.search_cache:
            cached_result = self.search_cache[cache_key]
            if datetime.now().timestamp() - cached_result["timestamp"] < self.cache_ttl:
                print(f"[DEBUG] Using cached search result for: {search_query}")
                return cached_result["data"]
        
        try:
            print(f"[DEBUG] Performing web search for styling: {search_query}")
            
            # Use firecrawl MCP for web search
            # For now, return a structured placeholder that matches expected format
            # In production, this would call the actual firecrawl search API
            
            search_results = await self._perform_web_search(search_query)
            
            # Process and structure the results
            processed_results = self._process_search_results(search_results, search_query)
            
            # Cache the results
            self.search_cache[cache_key] = {
                "data": processed_results,
                "timestamp": datetime.now().timestamp()
            }
            
            return processed_results
            
        except Exception as e:
            print(f"[ERROR] Web search for styling failed: {e}")
            return self._get_fallback_styling_data(search_query)
    
    async def _perform_web_search(self, search_query: str) -> List[Dict[str, Any]]:
        """
        Perform actual web search using available search APIs
        
        For Sprint 2, this is a placeholder that would integrate with:
        - Firecrawl MCP for web search
        - Google Custom Search API
        - Bing Search API
        """
        
        # Placeholder implementation - in production this would call actual search APIs
        print(f"[INFO] Web search placeholder for: {search_query}")
        
        # Simulate search results structure
        mock_results = [
            {
                "title": f"Style Guide: {search_query}",
                "url": "https://example.com/style-guide",
                "description": f"Fashion inspiration and styling tips for {search_query}",
                "image_url": None
            }
        ]
        
        return mock_results
    
    def _process_search_results(self, search_results: List[Dict[str, Any]], search_query: str) -> Dict[str, Any]:
        """
        Process raw search results into structured styling data
        """
        
        return {
            "search_query": search_query,
            "results_found": len(search_results),
            "styling_inspiration": self._extract_styling_keywords(search_query),
            "search_results": search_results[:5],  # Limit to top 5 results
            "generated_at": datetime.now().isoformat()
        }
    
    def _extract_styling_keywords(self, search_query: str) -> List[str]:
        """
        Extract relevant styling keywords from search query
        """
        
        # Common styling keywords to enhance prompts
        styling_keywords = []
        
        query_lower = search_query.lower()
        
        # Add event-specific styling keywords
        if "met gala" in query_lower:
            styling_keywords.extend(["avant-garde", "high fashion", "dramatic", "artistic"])
        elif "grammy" in query_lower:
            styling_keywords.extend(["glamorous", "musical", "performance-ready", "bold"])
        elif "oscar" in query_lower:
            styling_keywords.extend(["elegant", "classic", "sophisticated", "timeless"])
        elif "red carpet" in query_lower:
            styling_keywords.extend(["glamorous", "formal", "statement", "photogenic"])
        elif "fashion week" in query_lower:
            styling_keywords.extend(["trendy", "runway", "designer", "fashion-forward"])
        elif "coachella" in query_lower:
            styling_keywords.extend(["bohemian", "festival", "casual", "trendy"])
        
        # Add celebrity-specific styling keywords
        if "taylor swift" in query_lower:
            styling_keywords.extend(["sparkly", "vintage", "feminine", "romantic"])
        elif "beyonce" in query_lower:
            styling_keywords.extend(["powerful", "glamorous", "bold", "confident"])
        elif "rihanna" in query_lower:
            styling_keywords.extend(["edgy", "avant-garde", "bold", "experimental"])
        
        return styling_keywords
    
    def _get_fallback_styling_data(self, search_query: str) -> Dict[str, Any]:
        """
        Provide fallback styling data when web search fails
        """
        
        return {
            "search_query": search_query,
            "results_found": 0,
            "styling_inspiration": self._extract_styling_keywords(search_query),
            "search_results": [],
            "generated_at": datetime.now().isoformat(),
            "fallback": True,
            "message": "Web search unavailable, using keyword-based styling suggestions"
        }
    
    def enhance_prompt_with_styling_context(self, prompt: str, styling_data: Dict[str, Any]) -> str:
        """
        Enhance the original prompt with styling context from web search
        """
        
        if not styling_data or not styling_data.get("styling_inspiration"):
            return prompt
        
        styling_keywords = styling_data["styling_inspiration"]
        
        # Add styling context to prompt
        if styling_keywords:
            styling_context = ", ".join(styling_keywords[:3])  # Use top 3 keywords
            enhanced_prompt = f"{prompt}, {styling_context} style"
            
            print(f"[DEBUG] Enhanced prompt with styling context: '{prompt}' -> '{enhanced_prompt}'")
            return enhanced_prompt
        
        return prompt
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        
        active_entries = 0
        current_time = datetime.now().timestamp()
        
        for entry in self.search_cache.values():
            if current_time - entry["timestamp"] < self.cache_ttl:
                active_entries += 1
        
        return {
            "total_cached_searches": len(self.search_cache),
            "active_cached_searches": active_entries,
            "cache_ttl_seconds": self.cache_ttl
        } 