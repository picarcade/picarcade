# test_safe_generation.py
import replicate
import asyncio
from app.core.config import settings

async def test_safe_generation():
    """Test with a safe, clear prompt"""
    
    print("🧪 Testing Safe Replicate Generation")
    print("=" * 40)
    
    token = settings.replicate_api_token
    
    # Test 1: Direct sync call with safe prompt
    print("1️⃣ Testing direct sync call...")
    try:
        client = replicate.Client(api_token=token)
        
        # Use a very safe, clear prompt
        safe_prompt = "a beautiful landscape with mountains and trees"
        
        result = client.run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": safe_prompt,
                "width": 512,
                "height": 512,
                "num_inference_steps": 20,
                "guidance_scale": 7.5
            }
        )
        
        print(f"   ✅ Direct call succeeded: {result}")
        
    except Exception as e:
        print(f"   ❌ Direct call failed: {e}")
    
    # Test 2: Async executor call (like our generator)
    print("2️⃣ Testing async executor call...")
    try:
        def run_replicate_sync():
            client = replicate.Client(api_token=token)
            return client.run(
                "black-forest-labs/flux-1.1-pro",
                input={
                    "prompt": "a beautiful landscape with mountains and trees",
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 20,
                    "guidance_scale": 7.5
                }
            )
        
        # Run in executor like our generator does
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_replicate_sync)
        
        print(f"   ✅ Async call succeeded: {result}")
        
    except Exception as e:
        print(f"   ❌ Async call failed: {e}")
    
    # Test 3: Test our actual generator
    print("3️⃣ Testing our generator...")
    try:
        from app.services.generators.replicate import ReplicateGenerator
        
        generator = ReplicateGenerator()
        
        result = await generator.generate(
            "a beautiful landscape with mountains and trees",
            {
                "model": "flux-1.1-pro",
                "width": 512,
                "height": 512,
                "num_inference_steps": 20,
                "guidance_scale": 7.5
            }
        )
        
        if result.success:
            print(f"   ✅ Generator succeeded: {result.output_url}")
        else:
            print(f"   ❌ Generator failed: {result.error_message}")
            
    except Exception as e:
        print(f"   ❌ Generator exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_safe_generation())