import pytest
from pytest_bdd import given, scenarios
from tests.e2e.steps import wait_for

from openfeature import api
from openfeature.client import OpenFeatureClient
from openfeature.contrib.provider.flagd import FlagdProvider
from openfeature.contrib.provider.flagd.config import CacheType, ResolverType
from openfeature.provider import ProviderStatus


@pytest.fixture(autouse=True, scope="module")
def client_name() -> str:
    return "rpc"


@pytest.fixture(autouse=True, scope="module")
def resolver_type() -> ResolverType:
    return ResolverType.GRPC


@pytest.fixture(autouse=True, scope="module")
def port():
    return 8013


@pytest.fixture(autouse=True, scope="module")
def image():
    return "ghcr.io/open-feature/flagd-testbed:v0.5.13"


@given("a provider is registered with caching", target_fixture="client")
def setup_caching_provider(setup, resolver_type, client_name) -> OpenFeatureClient:
    api.set_provider(
        FlagdProvider(
            resolver_type=resolver_type, port=setup, cache_type=CacheType.LRU
        ),
        client_name,
    )
    client = api.get_client(client_name)
    wait_for(lambda: client.get_provider_status() == ProviderStatus.READY)
    return client


scenarios(
    "../../test-harness/gherkin/flagd.feature",
    "../../test-harness/gherkin/flagd-json-evaluator.feature",
    "../../spec/specification/assets/gherkin/evaluation.feature",
    "./rpc_cache.feature",
)
