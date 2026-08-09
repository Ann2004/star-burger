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