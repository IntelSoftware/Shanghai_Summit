"""Test LLM server connection and inference"""
import asyncio
from fastmcp import Client

async def test_llm_detailed():
    print("=" * 60)
    print("Testing LLM Server Connection")
    print("=" * 60)
    
    weather_report = """
    - Location: Hillsboro, United States
    - Coordinates: 45.5229, -122.9898
    - Temperature: 8.3°C
    - Wind Speed: 11.5 km/h
    """
    
    aqi_report = """
    - Location: Hillsboro, United States
    - Coordinates: 45.5229, -122.9898
    - AQI Level: 1 (Good)
    
     Pollutants (μg/m3):
     - CO: 230.32
     - NO: 0.01
     - NO2: 7.14
     - O3: 72.09
     - SO2: 1.07
     - PM2.5: 3.39
     - PM10: 4.09
     - NH3: 0.15
    """
    
    try:
        print(f"\n1. Connecting to http://127.0.0.1:8002/sse...")
        print(f"   Timeout: 120 seconds")
        
        async with Client("http://127.0.0.1:8002/sse", timeout=120.0) as client:
            print("   ✓ Connected successfully!")
            
            print(f"\n2. Calling safety_guidelines tool...")
            print(f"   Weather report length: {len(weather_report)} chars")
            print(f"   AQI report length: {len(aqi_report)} chars")
            
            result = await client.call_tool("safety_guidelines", {
                "weather_report": weather_report,
                "aqi_report": aqi_report
            })
            
            print("\n3. Extracting response...")
            
            # Extract text
            if isinstance(result, list):
                text = "\n".join(block.text for block in result if hasattr(block, "text"))
            elif hasattr(result, "text"):
                text = result.text
            else:
                text = str(result)
            
            print("\n" + "=" * 60)
            print("LLM RESPONSE:")
            print("=" * 60)
            print(text)
            print("=" * 60)
            print("\n✅ Test completed successfully!")
            
    except asyncio.TimeoutError as e:
        print(f"\n❌ Timeout Error: {e}")
        print("   The LLM server took too long to respond")
    except ConnectionRefusedError as e:
        print(f"\n❌ Connection Refused: {e}")
        print("   The LLM server is not running on port 8002")
    except ConnectionResetError as e:
        print(f"\n❌ Connection Reset: {e}")
        print("   The server closed the connection")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_detailed())
