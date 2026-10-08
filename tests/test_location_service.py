from types import SimpleNamespace

import pytest

from app.services.location import LocationService
from app.tinder.models import Location


class FakeGeolocator:
    def __init__(self, location):
        self.location = location
        self.calls = []

    def geocode(self, city, **kwargs):
        self.calls.append((city, kwargs))
        return self.location


class FakeClient:
    def __init__(self):
        self.coordinates = None

    def set_location(self, latitude, longitude):
        self.coordinates = (latitude, longitude)


def test_set_city_geocodes_location_and_updates_tinder_location():
    client = FakeClient()
    service = LocationService(client)
    geolocator = FakeGeolocator(
        SimpleNamespace(
            latitude=52.37,
            longitude=4.90,
            address="Amsterdam, Netherlands",
            raw={"type": "city"},
        )
    )
    service.geolocator = geolocator

    location = service.set_city("Amsterdam")

    assert location == Location(
        latitude=52.37,
        longitude=4.90,
        address="Amsterdam, Netherlands",
    )
    assert client.coordinates == (52.37, 4.90)
    assert geolocator.calls == [
        ("Amsterdam", {"addressdetails": True})
    ]


@pytest.mark.parametrize(
    "query, result_type",
    [
        ("Москва", "administrative"),
        ("деревня Ивановка", "village"),
        ("1012 WX", "postcode"),
        ("Damrak 1, Amsterdam", "house"),
    ],
)
def test_set_city_accepts_any_location_type_when_geocoded(query, result_type):
    client = FakeClient()
    service = LocationService(client)
    service.geolocator = FakeGeolocator(
        SimpleNamespace(
            latitude=52.37,
            longitude=4.90,
            address="Resolved location",
            raw={"type": result_type},
        )
    )

    location = service.set_city(query)

    assert location.address == "Resolved location"
    assert client.coordinates == (52.37, 4.90)


def test_set_city_raises_when_location_cannot_be_found():
    client = FakeClient()
    service = LocationService(client)
    service.geolocator = FakeGeolocator(None)

    with pytest.raises(ValueError, match="Location not found: Atlantis"):
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
