"""
# This is a Python Provider to interact with flagd
#
# -- Usage --
# open_feature_api.set_provider(flagd_provider.FlagdProvider())
# flag_value =  open_feature_client.get_string_value(
#                   key="foo",
#                   default_value="missingflag"
#               )
# print(f"Flag Value is: {flag_value}")
#   OR the more verbose option
# flag = open_feature_client.get_string_details(key="foo", default_value="missingflag")
# print(f"Flag is: {flag.value}")
#   OR
# print(f"Flag Details: {vars(flag)}"")
#
# -- Customisation --
# Follows flagd defaults: 'http' protocol on 'localhost' on port '8013'
# But can be overridden:
# provider = open_feature_api.get_provider()
# provider.initialise(schema="https",endpoint="example.com",port=1234,timeout=10)
"""

import logging
import typing

from openfeature.evaluation_context import EvaluationContext
from openfeature.event import ProviderEventDetails
from openfeature.flag_evaluation import FlagResolutionDetails
from openfeature.provider.metadata import Metadata
from openfeature.provider.provider import AbstractProvider

from .config import CacheType, Config, ResolverType
from .resolvers import AbstractResolver, GrpcResolver, InProcessResolver

T = typing.TypeVar("T")


class FlagdProvider(AbstractProvider):
    """Flagd OpenFeature Provider"""

    def __init__(  # noqa: PLR0913
        self,
        host: typing.Optional[str] = None,
        port: typing.Optional[int] = None,
        tls: typing.Optional[bool] = None,
        deadline: typing.Optional[int] = None,
        timeout: typing.Optional[int] = None,
        retry_backoff_ms: typing.Optional[int] = None,
        selector: typing.Optional[str] = None,
        resolver_type: typing.Optional[ResolverType] = None,
        offline_flag_source_path: typing.Optional[str] = None,
        cache_type: typing.Optional[CacheType] = None,
        max_cache_size: typing.Optional[int] = None,
        stream_deadline_ms: typing.Optional[int] = None,
        keep_alive_time: typing.Optional[int] = None,
    ):
        """
        Create an instance of the FlagdProvider

        :param host: the host to make requests to
        :param port: the port the flagd service is available on
        :param tls: enable/disable secure TLS connectivity
        :param timeout: the maximum to wait before a request times out
        """
        if deadline is None and timeout is not None:
            deadline = timeout * 1000
            logging.info(
                "'timeout' property is deprecated, please use 'deadline' instead, be aware that 'deadline' is in milliseconds"
            )
        self.config = Config(
            host=host,
            port=port,
            tls=tls,
            deadline=deadline,
            retry_backoff_ms=retry_backoff_ms,
            selector=selector,
            resolver_type=resolver_type,
            offline_flag_source_path=offline_flag_source_path,
            cache_type=cache_type,
            max_cache_size=max_cache_size,
            stream_deadline_ms=stream_deadline_ms,
            keep_alive_time=keep_alive_time,
        )

        self.resolver = self.setup_resolver()

    def setup_resolver(self) -> AbstractResolver:
        if self.config.resolver_type == ResolverType.RPC:
            return GrpcResolver(
                self.config,
                self.emit_provider_ready,
                self.emit_provider_error,
                self.emit_provider_configuration_changed,
            )
        elif self.config.resolver_type == ResolverType.IN_PROCESS:
            return InProcessResolver(
                self.config,
                self.emit_provider_ready,
                self.emit_provider_error,
                self.emit_provider_configuration_changed,
            )
        else:
            raise ValueError(
                f"`resolver_type` parameter invalid: {self.config.resolver_type}"
            )

    def initialize(self, evaluation_context: EvaluationContext) -> None:
        self.resolver.initialize(evaluation_context)

    def shutdown(self) -> None:
        if self.resolver:
            self.resolver.shutdown()

    def get_metadata(self) -> Metadata:
        """Returns provider metadata"""
        return Metadata(name="FlagdProvider")

    def flag_store_updated_callback(self, flag_keys: typing.List[str]) -> None:
        self.emit_provider_configuration_changed(
            ProviderEventDetails(flags_changed=flag_keys)
        )

    def resolve_boolean_details(
        self,
        key: str,
        default_value: bool,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[bool]:
        return self.resolver.resolve_boolean_details(
            key, default_value, evaluation_context
        )

    def resolve_string_details(
        self,
        key: str,
        default_value: str,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[str]:
        return self.resolver.resolve_string_details(
            key, default_value, evaluation_context
        )

    def resolve_float_details(
        self,
        key: str,
        default_value: float,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[float]:
        return self.resolver.resolve_float_details(
            key, default_value, evaluation_context
        )

    def resolve_integer_details(
        self,
        key: str,
        default_value: int,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[int]:
        return self.resolver.resolve_integer_details(
            key, default_value, evaluation_context
        )

    def resolve_object_details(
        self,
        key: str,
        default_value: typing.Union[dict, list],
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[typing.Union[dict, list]]:
        return self.resolver.resolve_object_details(
            key, default_value, evaluation_context
        )
