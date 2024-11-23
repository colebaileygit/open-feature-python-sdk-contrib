import logging
import threading
import time
import typing

import grpc
from cachebox import LRUCache  # type:ignore[import-not-found]
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct
from schemas.protobuf.flagd.evaluation.v1 import (  # type:ignore[import-not-found]
    evaluation_pb2,
    evaluation_pb2_grpc,
)

from openfeature.evaluation_context import EvaluationContext
from openfeature.event import ProviderEventDetails
from openfeature.exception import (
    ErrorCode,
    FlagNotFoundError,
    GeneralError,
    InvalidContextError,
    ParseError,
    TypeMismatchError,
)
from openfeature.flag_evaluation import FlagResolutionDetails, Reason

from ..config import CacheType, Config
from ..flag_type import FlagType
from .protocol import AbstractResolver

T = typing.TypeVar("T")

logger = logging.getLogger("openfeature.contrib")


class GrpcResolver(AbstractResolver):
    MAX_BACK_OFF = 120

    def __init__(
        self,
        config: Config,
        emit_provider_ready: typing.Callable[[ProviderEventDetails], None],
        emit_provider_error: typing.Callable[[ProviderEventDetails], None],
        emit_provider_configuration_changed: typing.Callable[
            [ProviderEventDetails], None
        ],
    ):
        self.config = config
        self.emit_provider_ready = emit_provider_ready
        self.emit_provider_error = emit_provider_error
        self.emit_provider_configuration_changed = emit_provider_configuration_changed
        channel_factory = (
            grpc.secure_channel if self.config.tls else grpc.insecure_channel
        )
        self.channel = channel_factory(f"{self.config.host}:{self.config.port}")
        self.stub = evaluation_pb2_grpc.ServiceStub(self.channel)
        self.retry_backoff_seconds = 0.1
        self.connected = False

        self._cache = (
            LRUCache(maxsize=self.config.max_cache_size)
            if self.config.cache_type == CacheType.LRU
            else None
        )

    def initialize(self, evaluation_context: EvaluationContext) -> None:
        self.connect()

    def shutdown(self) -> None:
        self.active = False
        self.channel.close()
        if self._cache:
            self._cache.clear()

    def connect(self) -> None:
        self.active = True
        self.thread = threading.Thread(
            target=self.listen, daemon=True, name="FlagdGrpcServiceWorkerThread"
        )
        self.thread.start()

    def listen(self) -> None:
        retry_delay = self.retry_backoff_seconds
        while self.active:
            request = evaluation_pb2.EventStreamRequest()
            try:
                logger.debug("Setting up gRPC sync flags connection")
                for message in self.stub.EventStream(request):
                    if message.type == "provider_ready":
                        if not self.connected:
                            self.emit_provider_ready(
                                ProviderEventDetails(
                                    message="gRPC sync connection established"
                                )
                            )
                            self.connected = True
                            # reset retry delay after successsful read
                            retry_delay = self.retry_backoff_seconds

                    elif message.type == "configuration_change":
                        data = MessageToDict(message)["data"]
                        self.handle_changed_flags(data)

                    if not self.active:
                        logger.info("Terminating gRPC sync thread")
                        return
            except grpc.RpcError as e:
                logger.error(f"SyncFlags stream error, {e.code()=} {e.details()=}")
            except ParseError:
                logger.exception(
                    f"Could not parse flag data using flagd syntax: {message=}"
                )

            self.connected = False
            self.emit_provider_error(
                ProviderEventDetails(
                    message=f"gRPC sync disconnected, reconnecting in {retry_delay}s",
                    error_code=ErrorCode.GENERAL,
                )
            )
            logger.info(f"gRPC sync disconnected, reconnecting in {retry_delay}s")
            time.sleep(retry_delay)
            retry_delay = min(2 * retry_delay, self.MAX_BACK_OFF)

    def handle_changed_flags(self, data: typing.Any) -> None:
        changed_flags = list(data["flags"].keys())

        if self._cache:
            for flag in changed_flags:
                self._cache.pop(flag)

        self.emit_provider_configuration_changed(ProviderEventDetails(changed_flags))

    def resolve_boolean_details(
        self,
        key: str,
        default_value: bool,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[bool]:
        return self._resolve(key, FlagType.BOOLEAN, default_value, evaluation_context)

    def resolve_string_details(
        self,
        key: str,
        default_value: str,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[str]:
        return self._resolve(key, FlagType.STRING, default_value, evaluation_context)

    def resolve_float_details(
        self,
        key: str,
        default_value: float,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[float]:
        return self._resolve(key, FlagType.FLOAT, default_value, evaluation_context)

    def resolve_integer_details(
        self,
        key: str,
        default_value: int,
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[int]:
        return self._resolve(key, FlagType.INTEGER, default_value, evaluation_context)

    def resolve_object_details(
        self,
        key: str,
        default_value: typing.Union[dict, list],
        evaluation_context: typing.Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[typing.Union[dict, list]]:
        return self._resolve(key, FlagType.OBJECT, default_value, evaluation_context)

    def _resolve(  # noqa: PLR0915 C901
        self,
        flag_key: str,
        flag_type: FlagType,
        default_value: T,
        evaluation_context: typing.Optional[EvaluationContext],
    ) -> FlagResolutionDetails[T]:
        if self._cache is not None and flag_key in self._cache:
            cached_flag: FlagResolutionDetails[T] = self._cache[flag_key]
            cached_flag.reason = Reason.CACHED
            return cached_flag

        context = self._convert_context(evaluation_context)
        call_args = {"timeout": self.config.timeout}
        try:
            if flag_type == FlagType.BOOLEAN:
                request = evaluation_pb2.ResolveBooleanRequest(
                    flag_key=flag_key, context=context
                )
                response = self.stub.ResolveBoolean(request, **call_args)
                value = response.value
            elif flag_type == FlagType.STRING:
                request = evaluation_pb2.ResolveStringRequest(
                    flag_key=flag_key, context=context
                )
                response = self.stub.ResolveString(request, **call_args)
                value = response.value
            elif flag_type == FlagType.OBJECT:
                request = evaluation_pb2.ResolveObjectRequest(
                    flag_key=flag_key, context=context
                )
                response = self.stub.ResolveObject(request, **call_args)
                value = MessageToDict(response, preserving_proto_field_name=True)[
                    "value"
                ]
            elif flag_type == FlagType.FLOAT:
                request = evaluation_pb2.ResolveFloatRequest(
                    flag_key=flag_key, context=context
                )
                response = self.stub.ResolveFloat(request, **call_args)
                value = response.value
            elif flag_type == FlagType.INTEGER:
                request = evaluation_pb2.ResolveIntRequest(
                    flag_key=flag_key, context=context
                )
                response = self.stub.ResolveInt(request, **call_args)
                value = response.value
            else:
                raise ValueError(f"Unknown flag type: {flag_type}")

        except grpc.RpcError as e:
            code = e.code()
            message = f"received grpc status code {code}"

            if code == grpc.StatusCode.NOT_FOUND:
                raise FlagNotFoundError(message) from e
            elif code == grpc.StatusCode.INVALID_ARGUMENT:
                raise TypeMismatchError(message) from e
            elif code == grpc.StatusCode.DATA_LOSS:
                raise ParseError(message) from e
            raise GeneralError(message) from e

        # Got a valid flag and valid type. Return it.
        result = FlagResolutionDetails(
            value=value,
            reason=response.reason,
            variant=response.variant,
        )

        if response.reason == Reason.STATIC and self._cache is not None:
            self._cache.insert(flag_key, result)

        return result

    def _convert_context(
        self, evaluation_context: typing.Optional[EvaluationContext]
    ) -> Struct:
        s = Struct()
        if evaluation_context:
            try:
                s["targetingKey"] = evaluation_context.targeting_key
                s.update(evaluation_context.attributes)
            except ValueError as exc:
                message = (
                    "could not serialize evaluation context to google.protobuf.Struct"
                )
                raise InvalidContextError(message) from exc
        return s
