"""
Geocoding utilities for HarakaCare using OpenStreetMap Nominatim.
Runs in background before saving triage data.
"""

import time
import logging
import requests
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Rate limiting: track last request time across the app
_last_request_time = 0

def fetch_coordinates_from_nominatim(
    village: str, 
    district: str, 
    country: str = "Uganda"
) -> Tuple[Optional[float], Optional[float]]:
    """
    Fetch coordinates from OpenStreetMap Nominatim API.
    Automatically handles rate limiting (1 request per second).
    
    Args:
        village: Village name
        district: District name
        country: Country name (default: Uganda)
    
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found/error
    """
    global _last_request_time
    
    village = village.strip()
    district = district.strip()
    
    if not village or not district:
        return None, None
    
    # Rate limiting - ensure at least 1 second between requests
    now = time.time()
    time_since_last = now - _last_request_time
    if time_since_last < 1.0:
        sleep_time = 1.0 - time_since_last
        logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)
    
    query = f"{village}, {district}, {country}"
    url = "https://nominatim.openstreetmap.org/search"
    
    # IMPORTANT: Replace with your actual contact email
    headers = {
        'User-Agent': 'HarakaCare/1.0 (triage@harakacare.ug)'
    }
    
    params = {
        'q': query,
        'format': 'json',
        'limit': 1,
        'addressdetails': 1
    }
    
    try:
        logger.info(f"Fetching coordinates for: {query}")
        response = requests.get(
            url, 
            headers=headers, 
            params=params, 
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Update last request time AFTER successful request
        _last_request_time = time.time()
        
        if not data:
            logger.info(f"No coordinates found for: {query}")
            return None, None
        
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        
        logger.info(f"Found coordinates for {query}: {lat}, {lon}")
        return lat, lon
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Nominatim API error for {query}: {e}")
        return None, None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Error parsing Nominatim response for {query}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error in geocoding for {query}: {e}")
        return None, None