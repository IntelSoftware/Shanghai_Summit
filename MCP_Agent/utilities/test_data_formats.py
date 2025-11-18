"""Test to verify Weather and AQI data formats"""
import asyncio
from fastmcp import Client

async def test_data_formats():
    print("=" * 70)
    print("Testing Weather and AQI Data Formats")
    print("=" * 70)
    
    location = "Hillsboro, Oregon, US"
    
    # Test Weather Server
    print("\n1. WEATHER SERVER OUTPUT:")
    print("-" * 70)
    try:
        async with Client("http://127.0.0.1:8000/sse", timeout=30.0) as client:
            result = await client.call_tool("get_weather", {"location": location})
            
            # Show raw result type and structure
            print(f"Result type: {type(result)}")
            print(f"Result structure: {result}")
            
            # Extract text
            if isinstance(result, list):
                text = "\n".join(block.text for block in result if hasattr(block, "text"))
            elif hasattr(result, "text"):
                text = result.text
            else:
                text = str(result)
            
            print(f"\nExtracted text ({len(text)} chars):")
            print("-" * 70)
            print(text)
            print("-" * 70)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test AQI Server
    print("\n2. AQI SERVER OUTPUT:")
    print("-" * 70)
    try:
        async with Client("http://127.0.0.1:8001/sse", timeout=30.0) as client:
            result = await client.call_tool("get_aqi", {"location": location})
            
            # Show raw result type and structure
            print(f"Result type: {type(result)}")
            print(f"Result structure: {result}")
            
            # Extract text
            if isinstance(result, list):
                text = "\n".join(block.text for block in result if hasattr(block, "text"))
            elif hasattr(result, "text"):
                text = result.text
            else:
                text = str(result)
            
            print(f"\nExtracted text ({len(text)} chars):")
            print("-" * 70)
            print(text)
            print("-" * 70)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 70)
    print("ANALYSIS:")
    print("=" * 70)
    print("Both outputs should be clean, formatted strings without:")
    print("  - MCP protocol wrappers")
    print("  - JSON structures")
    print("  - List/array syntax")
    print("  - Extra whitespace or encoding issues")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_data_formats())
