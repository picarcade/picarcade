import aiohttp
import io
import re
from typing import Optional, Tuple, List
from PIL import Image
import uuid
import time
from urllib.parse import urljoin, urlparse
from app.services.storage import storage_service

class URLProcessor:
    """Service for processing images from URLs for virtual try-on"""
    
    @staticmethod
    async def fetch_and_process_clothing_url(url: str, user_id: str = None) -> Optional[str]:
        """
        Fetch clothing image from URL and process it for virtual try-on
        
        Args:
            url: URL of the clothing image
            user_id: Optional user ID for organizing files
            
        Returns:
            URL of the processed and stored image, or None if failed
        """
        try:
            print(f"[DEBUG] URLProcessor: Fetching clothing from URL: {url}")
            
            # Try to fetch as direct image first, then as product page
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        print(f"[ERROR] Failed to fetch URL: HTTP {response.status}")
                        return None
                    
                    content_type = response.headers.get('content-type', '')
                    
                    # If it's a direct image, use it
                    if content_type.startswith('image/'):
                        print(f"[DEBUG] URLProcessor: Direct image detected")
                        image_data = await response.read()
                    
                    # If it's HTML (product page), extract the main product image
                    elif content_type.startswith('text/html'):
                        print(f"[DEBUG] URLProcessor: HTML page detected, extracting product image")
                        html_content = await response.text()
                        
                        # Extract main product image URL from HTML
                        image_url = await URLProcessor._extract_product_image_from_html(html_content, url)
                        if not image_url:
                            print(f"[ERROR] Could not find product image in HTML page")
                            return None
                        
                        print(f"[DEBUG] URLProcessor: Found product image: {image_url}")
                        
                        # Fetch the actual image
                        async with session.get(image_url, timeout=30) as img_response:
                            if img_response.status != 200:
                                print(f"[ERROR] Failed to fetch product image: HTTP {img_response.status}")
                                return None
                            
                            image_data = await img_response.read()
                    
                    else:
                        print(f"[ERROR] URL is neither an image nor HTML page: {content_type}")
                        return None
                    
            # Validate and process the image
            processed_image = await URLProcessor._process_clothing_image(image_data)
            if not processed_image:
                return None
            
            # Create a temporary file-like object for storage
            class TempFile:
                def __init__(self, data: bytes, filename: str, content_type: str):
                    self.file = io.BytesIO(data)
                    self.filename = filename
                    self.content_type = content_type
                
                async def read(self):
                    return self.file.getvalue()
            
            # Generate filename
            filename = f"clothing_{uuid.uuid4().hex}.jpg"
            temp_file = TempFile(processed_image, filename, "image/jpeg")
            
            # Store the processed image
            success, file_path, public_url = await storage_service.upload_image(
                file=temp_file,
                user_id=user_id,
                resize_max=1024  # Optimize for virtual try-on
            )
            
            if success:
                print(f"[DEBUG] URLProcessor: Stored clothing image: {public_url}")
                return public_url
            else:
                print(f"[ERROR] Failed to store processed clothing image")
                return None
                
        except Exception as e:
            print(f"[ERROR] URLProcessor: Failed to process clothing URL: {e}")
            return None
    
    @staticmethod
    async def _process_clothing_image(image_data: bytes) -> Optional[bytes]:
        """
        Process clothing image for better virtual try-on results
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Processed image bytes or None if failed
        """
        try:
            # Open and validate image
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize for optimal try-on performance (1024x1024 max)
                width, height = img.size
                max_dimension = 1024
                
                if width > max_dimension or height > max_dimension:
                    if width > height:
                        new_width = max_dimension
                        new_height = int(height * max_dimension / width)
                    else:
                        new_height = max_dimension
                        new_width = int(width * max_dimension / height)
                    
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Enhance image quality for better try-on results
                # Note: Could add background removal here in the future
                
                # Save as JPEG
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=90, optimize=True)
                return output.getvalue()
                
        except Exception as e:
            print(f"[ERROR] Image processing failed: {e}")
            return None
    
    @staticmethod
    def is_valid_image_url(url: str) -> bool:
        """
        Basic validation for image URLs
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL looks like a valid image URL
        """
        if not url or not isinstance(url, str):
            return False
        
        # Check if it's a valid HTTP(S) URL
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Check for common image extensions
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')
        url_lower = url.lower()
        
        # Direct extension check
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True
        
        # Check for image URLs with parameters (e.g., e-commerce sites)
        if any(ext in url_lower for ext in image_extensions):
            return True
        
        # Allow common image hosting domains and e-commerce sites
        image_domains = [
            'imgur.com', 'i.imgur.com',
            'images.unsplash.com', 'unsplash.com',
            'cdn.shopify.com', 'shopify.com',
            'amazon.com', 'a.co',
            'static.zara.net', 'zara.com',
            'assets.adidas.com', 'adidas.com',
            'images.nike.com', 'nike.com',
            # Australian retailers
            'myer.com.au', 'davidjones.com', 'theiconic.com.au',
            # Major global retailers
            'hm.com', 'uniqlo.com', 'gap.com', 'nordstrom.com',
            'macys.com', 'target.com', 'walmart.com', 'asos.com',
            # Fashion/luxury brands
            'gucci.com', 'prada.com', 'louisvuitton.com', 'chanel.com',
            'burberry.com', 'versace.com', 'armani.com',
            # Sportswear
            'underarmour.com', 'puma.com', 'reebok.com', 'vans.com',
            # General e-commerce
            'ebay.com', 'etsy.com', 'aliexpress.com', 'alibaba.com'
        ]
        
        if any(domain in url_lower for domain in image_domains):
            return True
        
        # More permissive check: if URL contains common e-commerce indicators
        ecommerce_indicators = [
            '/product/', '/p/', '/item/', '/clothing/', '/fashion/',
            'shop', 'store', 'buy', 'catalog', 'collection'
        ]
        
        if any(indicator in url_lower for indicator in ecommerce_indicators):
            return True
        
        return False
    
    @staticmethod
    async def _extract_product_image_from_html(html_content: str, base_url: str) -> Optional[str]:
        """
        Extract the main product image URL from HTML content
        
        Args:
            html_content: HTML content of the product page
            base_url: Base URL of the page for resolving relative URLs
            
        Returns:
            URL of the main product image or None if not found
        """
        try:
            print(f"[DEBUG] URLProcessor: Extracting images from HTML ({len(html_content)} chars)")
            
            # Common patterns for product images
            patterns = [
                # Open Graph image (most reliable for e-commerce)
                r'<meta\s+property=["\']og:image["\'].*?content=["\']([^"\']+)["\']',
                r'<meta\s+content=["\']([^"\']+)["\'].*?property=["\']og:image["\']',
                
                # Twitter Card image
                r'<meta\s+name=["\']twitter:image["\'].*?content=["\']([^"\']+)["\']',
                r'<meta\s+content=["\']([^"\']+)["\'].*?name=["\']twitter:image["\']',
                
                # Product schema microdata
                r'<img[^>]*itemprop=["\']image["\'][^>]*src=["\']([^"\']+)["\']',
                r'<img[^>]*src=["\']([^"\']+)["\'][^>]*itemprop=["\']image["\']',
                
                # JSON-LD structured data (very common in modern e-commerce)
                r'"image":\s*"([^"]+)"',
                r'"image":\s*\[\s*"([^"]+)"',
                
                # Data attributes (React/Vue apps)
                r'<img[^>]*data-src=["\']([^"\']+)["\']',
                r'<img[^>]*data-lazy=["\']([^"\']+)["\']',
                
                # Common product image selectors
                r'<img[^>]*class=["\'][^"\']*product[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
                r'<img[^>]*class=["\'][^"\']*main[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
                r'<img[^>]*class=["\'][^"\']*hero[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
                r'<img[^>]*class=["\'][^"\']*primary[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
                r'<img[^>]*class=["\'][^"\']*featured[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
                
                # Australian retailer specific patterns
                r'<img[^>]*class=["\'][^"\']*(?:tile|card|gallery)[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
                
                # Generic large images (fallback)
                r'<img[^>]*src=["\']([^"\']+)["\'][^>]*(?:width=["\'](?:\d{3,}|100%)["\']|height=["\'](?:\d{3,}|100%)["\'])',
                
                # Very permissive fallback - any img with src
                r'<img[^>]*src=["\']([^"\']+)["\']',
            ]
            
            found_urls = []
            
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                print(f"[DEBUG] URLProcessor: Pattern {i+1}/{len(patterns)} found {len(matches)} matches")
                
                for match in matches:
                    if isinstance(match, tuple):
                        url = match[0]
                    else:
                        url = match
                    
                    # Clean up the URL
                    url = url.strip()
                    if url:
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(base_url, url)
                        
                        # Validate it looks like an image
                        if URLProcessor._is_likely_product_image(absolute_url):
                            found_urls.append(absolute_url)
                            print(f"[DEBUG] URLProcessor: Found valid image: {absolute_url}")
            
            # Remove duplicates while preserving order
            unique_urls = []
            seen = set()
            for url in found_urls:
                if url not in seen:
                    unique_urls.append(url)
                    seen.add(url)
            
            print(f"[DEBUG] URLProcessor: Total unique images found: {len(unique_urls)}")
            
            # Select the best product image (prioritize actual product images over banners)
            if unique_urls:
                selected_url = URLProcessor._select_best_product_image(unique_urls)
                print(f"[DEBUG] URLProcessor: Using best product image: {selected_url}")
                return selected_url
            else:
                print(f"[DEBUG] URLProcessor: No valid product images found")
                # Let's debug by showing what meta tags exist
                meta_tags = re.findall(r'<meta[^>]*>', html_content[:10000], re.IGNORECASE)
                print(f"[DEBUG] URLProcessor: Found {len(meta_tags)} meta tags in first 10k chars")
                if meta_tags:
                    for tag in meta_tags[:5]:  # Show first 5 meta tags
                        print(f"[DEBUG] Meta tag: {tag}")
                return None
            
        except Exception as e:
            print(f"[ERROR] Failed to extract product image from HTML: {e}")
            return None
    
    @staticmethod
    def _is_likely_product_image(url: str) -> bool:
        """
        Check if URL is likely a product image (not logo, icon, etc.)
        
        Args:
            url: Image URL to check
            
        Returns:
            True if URL looks like a product image
        """
        url_lower = url.lower()
        
        # Skip obvious non-product images
        skip_patterns = [
            'logo', 'icon', 'favicon', 'sprite', 'badge', 'banner',
            'header', 'footer', 'nav', 'menu', 'social', 'share',
            'loading', 'placeholder', 'thumb', 'thumbnail',
            'avatar', 'profile', 'user', 'author',
            '.svg', 'data:image'  # Skip SVGs and data URLs
        ]
        
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
        
        # Must have image extension or be from image hosting
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']
        has_extension = any(ext in url_lower for ext in image_extensions)
        
        # Allow URLs from image CDNs even without extension
        image_cdns = ['cloudinary', 'akamai', 'fastly', 'imgix', 'cloudfront']
        has_cdn = any(cdn in url_lower for cdn in image_cdns)
        
        return has_extension or has_cdn
    
    @staticmethod
    def _select_best_product_image(image_urls: List[str]) -> str:
        """
        Select the best product image from a list of URLs
        
        Prioritizes:
        1. Product-specific URLs (with product IDs)
        2. High-resolution images  
        3. Product gallery images
        4. Main product images over promotional banners
        
        Args:
            image_urls: List of image URLs
            
        Returns:
            Best product image URL
        """
        if not image_urls:
            return None
        
        # Score each URL based on quality indicators
        scored_urls = []
        
        for url in image_urls:
            score = 0
            url_lower = url.lower()
            
            # High priority: Product-specific URLs with IDs/SKUs
            if re.search(r'\d{6,}', url):  # Product IDs (6+ digits)
                score += 100
            
            # High priority: Main product image patterns
            if any(pattern in url_lower for pattern in [
                'product', 'main', 'primary', 'hero', 'gallery',
                'front', '_1_', '_01_', 'view1'
            ]):
                score += 50
            
            # Medium priority: High resolution indicators
            if any(res in url for res in ['720x', '1080x', '1920x', 'w=1920', 'large']):
                score += 30
            
            # Medium priority: E-commerce media domains
            if any(domain in url_lower for domain in [
                'myer-media', 'assets', 'media', 'cdn', 'images'
            ]):
                score += 20
            
            # Low priority bonuses
            if '.webp' in url_lower:
                score += 10  # Modern format
            if '_1_' in url or '_01_' in url:
                score += 10  # First in series
            
            # Penalties for non-product images
            if any(pattern in url_lower for pattern in [
                'banner', 'promo', 'campaign', 'brand',
                'logo', 'icon', 'social', 'thumb'
            ]):
                score -= 50
            
            # Penalty for very small images
            if any(size in url for size in ['100x', '200x', '150x']):
                score -= 20
            
            scored_urls.append((score, url))
            print(f"[DEBUG] URLProcessor: Scored {score} for {url}")
        
        # Sort by score (highest first) and return the best
        scored_urls.sort(key=lambda x: x[0], reverse=True)
        best_url = scored_urls[0][1]
        
        print(f"[DEBUG] URLProcessor: Best image selected with score {scored_urls[0][0]}")
        return best_url 