import pytest
from pytest_bdd import scenario, scenarios

from openfeature.contrib.provider.flagd.config import ResolverType


@pytest.fixture(autouse=True, scope="module")
def client_name() -> str:
    return "in-process"


@pytest.fixture(autouse=True, scope="module")
def resolver_type() -> ResolverType:
    return ResolverType.IN_PROCESS


@pytest.fixture(autouse=True, scope="module")
def port():
    return 8015


@pytest.fixture(autouse=True, scope="module")
def image():
    return "ghcr.io/open-feature/flagd-testbed:v0.5.13"


@pytest.mark.skip(reason="0 float might be a int")
@scenario("../../test-harness/gherkin/flagd.feature", "Resolves float zero value")
def test_flag_change_event():
    """not implemented"""


scenarios(
    "../../test-harness/gherkin/flagd.feature",
    "../../test-harness/gherkin/flagd-json-evaluator.feature",
    "../../spec/specification/assets/gherkin/evaluation.feature",
)
