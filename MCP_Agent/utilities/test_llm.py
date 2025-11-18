"""Quick test script for LLM server with real Weather and AQI data"""
import asyncio
from fastmcp import Client

async def test_llm():
    # Use the actual outputs we captured from test_data_formats.py
    weather_report = """
        - Location: Hillsboro, Oregon, US, United States
        - Coordinates: 45.52289, -122.98983
        - Temperature: 4.4°C
        - Wind Speed: 5.5 km/h
        """
    
    aqi_report = """
    - Location: Hillsboro, Oregon, US, United States
    - Coordinates: 45.52289, -122.98983
    - AQI Level: 2 (Fair)

     Pollutants (μg/m3):
     - CO: 128.33
     - NO: 0
     - NO2: 2.63
     - O3: 60.64
     - SO2: 0.1
     - PM2.5: 1.15
     - PM10: 3.93
     - NH3: 0.06
     """
    
    print("=" * 70)
    print("Testing LLM server with real Weather and AQI data")
    print("=" * 70)
    print(f"\nWeather report ({len(weather_report)} chars):")
    print("-" * 70)
    print(weather_report)
    print("-" * 70)
    
    print(f"\nAQI report ({len(aqi_report)} chars):")
    print("-" * 70)
    print(aqi_report)
    print("-" * 70)
    
    print("\nSending to LLM for health recommendations...")
    print("(This may take 30-60 seconds for inference...)")
    
    try:
        async with Client("http://127.0.0.1:8002/sse", timeout=120.0) as client:
            print("✓ Connected to LLM server")
            
            result = await client.call_tool("safety_guidelines", {
                "weather_report": weather_report,
                "aqi_report": aqi_report
            })
            
            # Extract text from result
            if isinstance(result, list):
                text = "\n".join(block.text for block in result if hasattr(block, "text"))
            elif hasattr(result, "text"):
                text = result.text
            else:
                text = str(result)
            
            print("\n" + "=" * 70)
            print("LLM HEALTH & SAFETY RECOMMENDATIONS:")
            print("=" * 70)
            print(text)
            print("=" * 70)
            print("\n✅ Test completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm())
