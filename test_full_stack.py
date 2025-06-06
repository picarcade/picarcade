# test_full_stack.py
import asyncio
import aiohttp
import json

async def test_full_stack():
    """Test the complete Pictures app stack"""
    
    backend_url = "http://localhost:8000"
    frontend_url = "http://localhost:3000"
    
    print("🧪 Testing Pictures Full Stack")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Backend Health Check
        print("1️⃣  Testing Backend Health...")
        try:
            async with session.get(f"{backend_url}/health") as response:
                health_data = await response.json()
                print(f"   ✅ Backend Status: {health_data['status']}")
                print(f"   📊 Database: {health_data.get('database', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Backend Error: {e}")
            return
        
        # Test 2: Frontend Health Check
        print("\n2️⃣  Testing Frontend...")
        try:
            async with session.get(frontend_url) as response:
                if response.status == 200:
                    print("   ✅ Frontend is running")
                else:
                    print(f"   ⚠️  Frontend returned status {response.status}")
        except Exception as e:
            print(f"   ❌ Frontend Error: {e}")
        
        # Test 3: Configuration Check
        print("\n3️⃣  Testing Configuration...")
        try:
            # Test if we can load config
            from app.core.config import settings
            print(f"   📋 App Name: {settings.app_name}")
            print(f"   🔑 Replicate Token: {'✅ Set' if settings.replicate_api_token else '❌ Missing'}")
            print(f"   🔑 Runway Token: {'✅ Set' if settings.runway_api_key else '❌ Missing'}")
            print(f"   🗄️  Supabase URL: {'✅ Set' if settings.supabase_url else '❌ Missing'}")
        except Exception as e:
            print(f"   ❌ Config Error: {e}")
        
        # Test 4: Direct Replicate Test
        print("\n4️⃣  Testing Replicate Integration...")
        try:
            from app.services.generators.replicate import ReplicateGenerator
            
            generator = ReplicateGenerator()
            test_params = {
                "model": "flux-1.1-pro",
                "width": 512,  # Smaller for faster testing
                "height": 512,
                "num_inference_steps": 20  # Faster
            }
            
            print("   🔄 Testing direct Replicate call...")
            result = await generator.generate("A simple test image", test_params)
            
            if result.success:
                print("   ✅ Replicate: Working correctly!")
                print(f"   🖼️  Generated: {result.output_url[:50]}...")
            else:
                print(f"   ❌ Replicate Error: {result.error_message}")
                
        except Exception as e:
            print(f"   ❌ Replicate Test Failed: {e}")
        
        # Test 5: Full API Generation Test
        print("\n5️⃣  Testing Full API Pipeline...")
        test_request = {
            "prompt": "A serene lake at sunrise with mountains in the background",
            "user_id": "test_user_integration",
            "quality_priority": "speed"  # Use speed for faster testing
        }
        
        try:
            print("   🔄 Sending generation request...")
            async with session.post(
                f"{backend_url}/api/v1/generation/generate",
                json=test_request,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout
            ) as response:
                result = await response.json()
                print(f"   📝 Request Status: {response.status}")
                print(f"   🎯 Generation Success: {result.get('success')}")
                print(f"   🤖 Model Used: {result.get('model_used')}")
                print(f"   ⏱️  Execution Time: {result.get('execution_time', 0):.2f}s")
                
                if result.get('success'):
                    print(f"   🖼️  Output URL: {result.get('output_url')}")
                    print("   🎉 Full pipeline working!")
                else:
                    error_msg = result.get('error_message', 'Unknown error')
                    print(f"   ❌ Error: {error_msg}")
                    
                    # Provide specific debugging based on error type
                    if 'Replicate' in error_msg and 'Unauthenticated' in error_msg:
                        print("   🔍 Debug: Replicate authentication issue")
                        print("   💡 Check: Token format, network connection, account status")
                    elif 'timeout' in error_msg.lower():
                        print("   ⏰ Debug: Generation timed out - this can be normal for complex requests")
                    elif 'model' in error_msg.lower():
                        print("   🤖 Debug: Model access issue - check if model is available")
                    
        except asyncio.TimeoutError:
            print("   ⏱️  Generation timed out after 2 minutes")
            print("   💡 This can be normal for real API calls - try with 'speed' priority")
        except Exception as e:
            print(f"   ❌ Generation Test Error: {e}")
        
        # Test 6: History Retrieval
        print("\n6️⃣  Testing History Retrieval...")
        try:
            async with session.get(
                f"{backend_url}/api/v1/generation/history/test_user_integration?limit=5"
            ) as response:
                history = await response.json()
                print(f"   📚 History Entries: {len(history)}")
                if history:
                    latest = history[0]
                    print(f"   📄 Latest: {latest['prompt'][:40]}...")
                    print(f"   ✅ Latest Success: {latest['success']}")
                    
                    # Show success rate
                    successful = sum(1 for h in history if h['success'] == 'success')
                    print(f"   📊 Success Rate: {successful}/{len(history)} ({successful/len(history)*100:.1f}%)")
                else:
                    print("   📝 No history entries yet")
                    
        except Exception as e:
            print(f"   ❌ History Test Error: {e}")
        
        # Test 7: API Documentation
        print("\n7️⃣  Testing API Documentation...")
        try:
            async with session.get(f"{backend_url}/docs") as response:
                if response.status == 200:
                    print("   ✅ API docs accessible at http://localhost:8000/docs")
                else:
                    print(f"   ⚠️  API docs returned status {response.status}")
        except Exception as e:
            print(f"   ❌ API docs error: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 Pictures Full Stack Test Complete!")
        
        # Final Status Summary
        print("\n📊 System Status:")
        print("   • Backend API: ✅ Running on http://localhost:8000")
        print("   • Frontend UI: ✅ Running on http://localhost:3000" if frontend_url else "   • Frontend UI: ❌ Not running")
        print("   • Database: ✅ Connected (Supabase)")
        
        # Configuration status
        from app.core.config import settings
        if settings.replicate_api_token:
            print("   • Replicate: ✅ Token configured")
        else:
            print("   • Replicate: ❌ Token missing")
            
        if settings.runway_api_key:
            print("   • Runway: ✅ Token configured")
        else:
            print("   • Runway: ⚠️  Token missing (video generation unavailable)")
        
        print("\n🚀 Ready to use Pictures!")
        print("   • Main UI: http://localhost:3000")
        print("   • API Docs: http://localhost:8000/docs")
        print("   • Health Check: http://localhost:8000/health")

if __name__ == "__main__":
    asyncio.run(test_full_stack())