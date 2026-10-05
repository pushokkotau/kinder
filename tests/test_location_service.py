from types import SimpleNamespace

import pytest

from app.services.location import LocationService


class FakeGeolocator:
    def __init__(self, location):
        self.location = location

    def geocode(self, city):
        return self.location


class FakeClient:
    def __init__(self):
        self.coordinates = None

    def set_location(self, latitude, longitude):
        self.coordinates = (latitude, longitude)


def test_set_city_geocodes_city_and_updates_tinder_location():
    client = FakeClient()
    service = LocationService(client)
    service.geolocator = FakeGeolocator(
        SimpleNamespace(latitude=52.37, longitude=4.90)
    )

    location = service.set_city("Amsterdam")

    assert location.latitude == 52.37
    assert location.longitude == 4.90
    assert client.coordinates == (52.37, 4.90)


def test_set_city_raises_when_city_cannot_be_found():
    client = FakeClient()
    service = LocationService(client)
    service.geolocator = FakeGeolocator(None)

    with pytest.raises(ValueError, match="City not found: Atlantis"):
        service.set_city("Atlantis")
