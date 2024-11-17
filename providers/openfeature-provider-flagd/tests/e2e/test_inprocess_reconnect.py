import pytest
from pytest_bdd import scenarios

from openfeature.contrib.provider.flagd.config import ResolverType


@pytest.fixture(autouse=True, scope="module")
def client_name() -> str:
    return "in-process-reconnect"


@pytest.fixture(autouse=True, scope="module")
def resolver_type() -> ResolverType:
    return ResolverType.IN_PROCESS


@pytest.fixture(autouse=True, scope="module")
def port():
    return 8015


@pytest.fixture(autouse=True, scope="module")
def image():
    return "ghcr.io/open-feature/flagd-testbed-unstable:v0.5.13"


# @pytest.mark.skip(reason="Reconnect seems to be flacky")
# @scenario("../../test-harness/gherkin/flagd-reconnect.feature", "Provider reconnection")
# def test_flag_change_event():
#     """not implemented"""


scenarios(
    "../../test-harness/gherkin/flagd-reconnect.feature",
)
