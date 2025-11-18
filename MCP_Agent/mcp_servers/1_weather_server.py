# weather_server.py

import httpx
from mcp.server.fastmcp import FastMCP
from utils import get_coordinates, load_config, setup_logging

# Load configuration
config = load_config()
logger = setup_logging(__name__)

# Initialize MCP Server
mcp = FastMCP(
    config['servers']['weather']['name'],
    host=config['servers']['weather']['host'],
    port=config['servers']['weather']['port']
)

# Weather tool


@mcp.tool()
async def get_weather(location: str) -> str:
    """
    Retrieve the current weather information for a given city or country.

    This function performs two steps:
      1. Uses the Open-Meteo Geocoding API to find the latitude and longitude
         of the specified location.
      2. Uses the Open-Meteo Weather API to fetch the current weather forecast
         for those coordinates.

    The returned weather report includes:
      - Location name and country
      - Coordinates (latitude and longitude)
      - Current temperature (°C)
      - Wind speed (km/h)

    Args:
        location (str): The name of the city or country to get weather data for.

    Returns:
        str: A formatted string containing the location details and current weather.
             If the location is not found or weather data is unavailable,
             an appropriate error message is returned instead.
    """
    logger.info(f"Weather request for: {location}")
    
    # Step 1: Geocoding to get latitude/longitude using shared utility
    lat, lon, country = await get_coordinates(location)
    
    if lat is None or lon is None:
        return f"Location '{location}' not found."

    # Step 2: Get weather forecast
    forecast_url = (
        f"{config['apis']['weather']}?latitude={lat}&longitude={lon}"
        "&current_weather=true&timezone=auto"
    )

    try:
        async with httpx.AsyncClient(timeout=config['timeouts']['http_request']) as client:
            weather_response = await client.get(forecast_url)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
    except httpx.RequestError as e:
        logger.error(f"Network error while fetching weather: {e}")
        return f"Network error while fetching weather: {str(e)}"
    except httpx.HTTPStatusError as e:
        logger.error(f"Weather API error: {e.response.status_code}")
        return (
            f"Weather API returned an error: {e.response.status_code} {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during weather fetch: {e}")
        return f"Unexpected error during weather fetch: {str(e)}"

    if "current_weather" not in weather_data:
        logger.warning(f"No weather data available for '{location}'")
        return f"Weather data not available for '{location}, {country}'."

    try:
        current = weather_data["current_weather"]
        temp = current.get("temperature", "N/A")
        wind = current.get("windspeed", "N/A")
    except Exception as e:
        logger.error(f"Failed to parse weather data: {e}")
        return f"Failed to parse weather data: {str(e)}"

    logger.info(f"Successfully retrieved weather for {location}")
    return f"""
        - Location: {location}, {country}
        - Coordinates: {lat}, {lon}
        - Temperature: {temp}°C
        - Wind Speed: {wind} km/h
        """


if __name__ == "__main__":
    mcp.run("sse")
