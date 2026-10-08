import pytest

from app.services.auth import AuthService
from app.services.auto_swipe import AutoSwipeService
from app.services.factory import ClientServices, ServiceFactory
from app.services.location import LocationService
from app.services.matches import MatchService
from app.services.profile import ProfileService
from app.services.recommendations import RecommendationService
from app.services.swipe import SwipeService


def test_factory_builds_complete_client_service_graph():
    client = object()

    services = ServiceFactory.for_client(client)

    assert isinstance(services, ClientServices)
    assert isinstance(services.auth, AuthService)
    assert isinstance(services.profile, ProfileService)
    assert isinstance(services.recommendations, RecommendationService)
    assert isinstance(services.swipe, SwipeService)
    assert isinstance(services.location, LocationService)
    assert isinstance(services.matches, MatchService)
    assert services.auth.client is client
    assert services.profile.client is client
    assert services.recommendations.client is client
    assert services.swipe.client is client
    assert services.swipe.recommendations is services.recommendations
    assert services.location.client is client
    assert services.matches.client is client
    assert isinstance(services.autoswipe, AutoSwipeService)
    assert services.autoswipe.recommendations is services.recommendations
    assert services.autoswipe.swipes is services.swipe
    assert services.autoswipe.matches is services.matches
    assert services.autoswipe.location_service.client is client


def test_factory_returns_independent_service_graphs():
    client = object()

    first = ServiceFactory.for_client(client)
    second = ServiceFactory.for_client(client)

    assert first is not second
    assert first.recommendations is not second.recommendations
    assert first.swipe is not second.swipe
