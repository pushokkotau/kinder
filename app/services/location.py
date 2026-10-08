from geopy import Nominatim
from geopy.location import Location as GeopyLocation

from app.tinder.client import TinderClient
from app.tinder.models import Location


class LocationService:
    def __init__(
        self,
        tinder_client: TinderClient,
        user_agent: str = "tinder-refactor",
    ):
        self.client = tinder_client
        self.geolocator = Nominatim(user_agent=user_agent)

    def set_city(self, city: str) -> Location:
        location = self.geolocator.geocode(
            city,
            addressdetails=True,
        )
        if location is None:
            raise ValueError(f"Location not found: {city}")

        return self.set_location(location)

    def set_location(self, location: GeopyLocation) -> Location:
        self.client.set_location(location.latitude, location.longitude)
        return Location(
            latitude=float(location.latitude),
            longitude=float(location.longitude),
            address=location.address,
        )
