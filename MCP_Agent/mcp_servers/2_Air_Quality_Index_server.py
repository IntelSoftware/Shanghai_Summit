import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import httpx
import os
from dotenv import load_dotenv
from utils import get_coordinates, load_config, setup_logging

# Load configuration
config = load_config()
logger = setup_logging(__name__)

# Initialize MCP Server
mcp = FastMCP(
    config['servers']['aqi']['name'],
    host=config['servers']['aqi']['host'],
    port=config['servers']['aqi']['port']
)

# Load API key for OpenWeatherMap AQI
load_dotenv()
OPENWEATHERMAP_API_KEY = os.getenv("AQI_API_KEY")

# AQI Tool


@mcp.tool()
async def get_aqi(location: str) -> str:
    """
    Retrieve the Air Quality Index (AQI) and pollutant concentrations
    for a given location using the OpenWeatherMap Air Pollution API.

    This tool first fetches the latitude and longitude for the location,
    then requests the AQI data from OpenWeatherMap.

    Args:
        location (str): The name of the location to get AQI data for.

    Returns:
        str: A formatted string containing:
            - Location and country
            - Coordinates (latitude, longitude)
            - AQI level and description
            - Concentrations of various pollutants (CO, NO, NO2, O3, SO2, PM2.5, PM10, NH3)

        Returns an error message if:
            - The AQI API key is missing
            - Coordinates cannot be found for the location
            - Network request fails
            - Invalid response is received
    """
    logger.info(f"AQI request for: {location}")
    
    if not OPENWEATHERMAP_API_KEY:
        logger.error("AQI API key is missing")
        return "AQI API key is missing. Set the 'AQI_API_KEY' environment variable."

    # Use shared geocoding utility
    lat, lon, country = await get_coordinates(location)

    if lat is None or lon is None:
        return f"Unable to get coordinates for '{location}'."

    aqi_url = (
        f"http://api.openweathermap.org/data/2.5/air_pollution?"
        f"lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}"
    )

    try:
        async with httpx.AsyncClient(timeout=config['timeouts']['http_request']) as client:
            response = await client.get(aqi_url)
            response.raise_for_status()  # Raises an HTTPStatusError for 4xx/5xx
            aqi_data = response.json()
    except httpx.RequestError as e:
        logger.error(f"Network error while fetching AQI: {e}")
        return f"Network error while fetching AQI: {str(e)}"
    except httpx.HTTPStatusError as e:
        logger.error(f"AQI API error: {e.response.status_code}")
        return f"API returned an error: {e.response.status_code} {e.response.text}"
    except Exception as e:
        logger.error(f"Unexpected error while fetching AQI: {e}")
        return f"Unexpected error while fetching AQI: {str(e)}"

    if "list" not in aqi_data or not aqi_data["list"]:
        logger.warning(f"No AQI data found for '{location}'")
        return f"No AQI data found for '{location}'."

    try:
        aqi = aqi_data["list"][0]["main"]["aqi"]
        components = aqi_data["list"][0]["components"]
        # AQI level explanation based on OpenWeatherMap
        levels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}

        logger.info(f"Successfully retrieved AQI for {location}: {aqi} ({levels.get(aqi, 'Unknown')})")
        
        return f"""
    - Location: {location}, {country}
    - Coordinates: {lat}, {lon}
    - AQI Level: {aqi} ({levels.get(aqi, 'Unknown')})

     Pollutants (μg/m3):
     - CO: {components.get('co', 'N/A')}
     - NO: {components.get('no', 'N/A')}
     - NO2: {components.get('no2', 'N/A')}
     - O3: {components.get('o3', 'N/A')}
     - SO2: {components.get('so2', 'N/A')}
     - PM2.5: {components.get('pm2_5', 'N/A')}
     - PM10: {components.get('pm10', 'N/A')}
     - NH3: {components.get('nh3', 'N/A')}
     """
    except Exception as e:
        logger.error(f"Failed to parse AQI response: {e}")
        return f"Failed to parse AQI response: {str(e)}"


if __name__ == "__main__":
    mcp.run("sse")
