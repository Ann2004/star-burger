import requests
from geo.models import AddressCoordinates


def fetch_coordinates_from_api(apikey, address):
    if not address:
        return None

    base_url = "https://geocode-maps.yandex.ru/1.x"

    try:
        response = requests.get(base_url, params={
            "geocode": address,
            "apikey": apikey,
            "format": "json",
        })
        response.raise_for_status()

        found_places = response.json()['response']['GeoObjectCollection']['featureMember']

        if not found_places:
            return None
        
        most_relevant = found_places[0]
        lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
        return lon, lat
        
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return None


def get_coordinates(apikey, address):
    if not address:
        return None
    
    try:
        coords_obj = AddressCoordinates.objects.get(address=address)
        if coords_obj.latitude is not None and coords_obj.longitude is not None:
            return (coords_obj.longitude, coords_obj.latitude)
        return None
    except AddressCoordinates.DoesNotExist:
        pass
    
    coords = fetch_coordinates_from_api(apikey, address)
    
    AddressCoordinates.objects.create(
        address=address,
        longitude=coords[0] if coords else None,
        latitude=coords[1] if coords else None,
    )
    
    return coords