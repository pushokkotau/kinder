from types import SimpleNamespace

import pytest

from app.services.location import LocationService
from app.tinder.models import Location


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
        SimpleNamespace(
            latitude=52.37,
            longitude=4.90,
            address="Amsterdam, Netherlands",
        )
    )

    location = service.set_city("Amsterdam")

    assert location == Location(
        latitude=52.37,
        longitude=4.90,
        address="Amsterdam, Netherlands",
    )
    assert client.coordinates == (52.37, 4.90)


def test_set_city_raises_when_city_cannot_be_found():
    client = FakeClient()
    service = LocationService(client)
    service.geolocator = FakeGeolocator(None)

    with pytest.raises(ValueError, match="City not found: Atlantis"):
        service.set_city("Atlantis")


def test_set_location_converts_geopy_location_to_domain_model():
    client = FakeClient()
    service = LocationService(client)
    geocoded = SimpleNamespace(
        latitude=52.3702,
        longitude=4.8952,
        address="Amsterdam, Netherlands",
    )

    location = service.set_location(geocoded)

    assert location == Location(
        latitude=52.3702,
        longitude=4.8952,
        address="Amsterdam, Netherlands",
    )
    assert client.coordinates == (52.3702, 4.8952)


def test_set_city_rejects_non_city_geocoding_result():
    client = FakeClient()
    service = LocationService(client)
    service.geolocator = FakeGeolocator(
        SimpleNamespace(
            latitude=48.85,
            longitude=2.35,
            address="12, Paris, France",
            raw={"type": "house"},
        )
    )

    with pytest.raises(ValueError, match="City not found: 12"):
        service.set_city("12")

    assert client.coordinates is None


def test_set_city_accepts_supported_city_type():
    client = FakeClient()
    service = LocationService(client)
    service.geolocator = FakeGeolocator(
        SimpleNamespace(
            latitude=52.37,
            longitude=4.90,
            address="Amsterdam, Netherlands",
            raw={"type": "city"},
        )
    )

    location = service.set_city("Amsterdam")

    assert location == Location(
        latitude=52.37,
        longitude=4.90,
        address="Amsterdam, Netherlands",
    )
