"""
Shared utilities for MCP Agent servers.
Provides common functionality like geocoding, configuration loading, and logging setup.
"""

import httpx
import yaml
from pathlib import Path
from typing import Optional, Tuple
import logging

# Load configuration
def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_config()

# Setup logging
def setup_logging(name: str) -> logging.Logger:
    """
    Configure logging with consistent formatting across all servers.
    
    Args:
        name: Logger name (typically the module or server name)
        
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, config['logging']['level']),
        format=config['logging']['format']
    )
    return logging.getLogger(name)

logger = setup_logging(__name__)

async def get_coordinates(location: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Fetch geographical coordinates for a location using Open-Meteo Geocoding API.
    
    This is a shared utility function used by multiple MCP servers to convert
    location names into latitude/longitude coordinates.
    
    Args:
        location: City or country name (e.g., 'Delhi', 'Tokyo', 'New York')
        
    Returns:
        Tuple of (latitude, longitude, country) or (None, None, None) if not found
        
    Example:
        >>> lat, lon, country = await get_coordinates("Paris")
        >>> print(f"{lat}, {lon} in {country}")
        48.8566, 2.3522 in France
    """
    geo_url = f"{config['apis']['geocoding']}?name={location}&count=1&language=en&format=json"
    
    try:
        async with httpx.AsyncClient(timeout=config['timeouts']['http_request']) as client:
            response = await client.get(geo_url)
            response.raise_for_status()
            data = response.json()
            
        if "results" not in data or not data["results"]:
            logger.warning(f"Location '{location}' not found")
            return None, None, None
            
        result = data["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        country = result.get("country", "Unknown")
        
        logger.info(f"Coordinates found for {location}: {lat}, {lon} ({country})")
        return lat, lon, country
        
    except httpx.RequestError as e:
        logger.error(f"Network error during geocoding for '{location}': {e}")
        return None, None, None
    except httpx.HTTPStatusError as e:
        logger.error(f"Geocoding API error for '{location}': {e.response.status_code}")
        return None, None, None
    except Exception as e:
        logger.error(f"Unexpected geocoding error for '{location}': {e}")
        return None, None, None
