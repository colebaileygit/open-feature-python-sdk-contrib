import json
import os
import tempfile
from os import listdir

import pytest
import yaml
from pytest_bdd import given, scenario, scenarios

from openfeature import api
from openfeature.client import OpenFeatureClient
from openfeature.contrib.provider.flagd import FlagdProvider
from openfeature.contrib.provider.flagd.config import ResolverType
from openfeature.provider import ProviderStatus
from tests.e2e.steps import wait_for

KEY_EVALUATORS = "$evaluators"

KEY_FLAGS = "flags"

MERGED_FILE = "merged_file"


@pytest.fixture(params=["json", "yaml"], autouse=True)
def file_name(request):
    extension = request.param
    result = {KEY_FLAGS: {}, KEY_EVALUATORS: {}}

    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../test-harness/flags/")
    )

    for f in listdir(path):
        with open(path + "/" + f, "rb") as infile:
            loaded_json = json.load(infile)
            result[KEY_FLAGS] = {**result[KEY_FLAGS], **loaded_json[KEY_FLAGS]}
            if loaded_json.get(KEY_EVALUATORS):
                result[KEY_EVALUATORS] = {
                    **result[KEY_EVALUATORS],
                    **loaded_json[KEY_EVALUATORS],
                }

    with tempfile.NamedTemporaryFile(
        "w", delete=False, suffix="." + extension
    ) as outfile:
        if extension == "json":
            json.dump(result, outfile)
        else:
            yaml.dump(result, outfile)

    return outfile


@pytest.fixture(autouse=True, scope="module")
def setup(request):
    pass


@given("a flagd provider is set", target_fixture="client")
@given("a provider is registered", target_fixture="client")
def setup_provider(setup, file_name) -> OpenFeatureClient:
    api.set_provider(
        FlagdProvider(
            resolver_type=ResolverType.IN_PROCESS,
            offline_flag_source_path=file_name.name,
        )
    )
    client = api.get_client()
    wait_for(lambda: client.get_provider_status() == ProviderStatus.READY)
    return client


@pytest.mark.skip(reason="Eventing not implemented")
@scenario("../../test-harness/gherkin/flagd.feature", "Flag change event")
def test_flag_change_event():
    """not implemented"""


scenarios(
    "../../test-harness/gherkin/flagd.feature",
    "../../test-harness/gherkin/flagd-json-evaluator.feature",
    "../../spec/specification/assets/gherkin/evaluation.feature",
)
