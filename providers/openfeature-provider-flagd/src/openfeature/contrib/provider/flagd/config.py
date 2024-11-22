import os
import typing
from enum import Enum

ENV_VAR_MAX_CACHE_SIZE = "FLAGD_MAX_CACHE_SIZE"
ENV_VAR_CACHE_TYPE = "FLAGD_CACHE_TYPE"
ENV_VAR_OFFLINE_POLL_INTERVAL_SECONDS = "FLAGD_OFFLINE_POLL_INTERVAL_SECONDS"
ENV_VAR_OFFLINE_FLAG_SOURCE_PATH = "FLAGD_OFFLINE_FLAG_SOURCE_PATH"
ENV_VAR_PORT = "FLAGD_PORT"
ENV_VAR_RESOLVER_TYPE = "FLAGD_RESOLVER_TYPE"
ENV_VAR_TLS = "FLAGD_TLS"
ENV_VAR_HOST = "FLAGD_HOST"

T = typing.TypeVar("T")


def str_to_bool(val: str) -> bool:
    return val.lower() == "true"


def env_or_default(
    env_var: str, default: T, cast: typing.Optional[typing.Callable[[str], T]] = None
) -> typing.Union[str, T]:
    val = os.environ.get(env_var)
    if val is None:
        return default
    return val if cast is None else cast(val)


class ResolverType(Enum):
    GRPC = "grpc"
    IN_PROCESS = "in-process"


class CacheType(Enum):
    LRU = "lru"
    DISABLED = "disabled"


class Config:
    def __init__(  # noqa: PLR0913
        self,
        host: typing.Optional[str] = None,
        port: typing.Optional[int] = None,
        tls: typing.Optional[bool] = None,
        timeout: typing.Optional[int] = None,
        resolver_type: typing.Optional[ResolverType] = None,
        offline_flag_source_path: typing.Optional[str] = None,
        offline_poll_interval_seconds: typing.Optional[float] = None,
        cache_type: typing.Optional[CacheType] = None,
        max_cache_size: typing.Optional[int] = None,
    ):
        self.host = env_or_default(ENV_VAR_HOST, "localhost") if host is None else host
        self.tls = (
            env_or_default(ENV_VAR_TLS, False, cast=str_to_bool) if tls is None else tls
        )
        self.timeout = 5 if timeout is None else timeout
        self.resolver_type = (
            ResolverType(env_or_default(ENV_VAR_RESOLVER_TYPE, "grpc"))
            if resolver_type is None
            else resolver_type
        )

        default_port = 8013 if self.resolver_type is ResolverType.GRPC else 8015
        self.port = (
            env_or_default(ENV_VAR_PORT, default_port, cast=int)
            if port is None
            else port
        )
        self.offline_flag_source_path = (
            env_or_default(ENV_VAR_OFFLINE_FLAG_SOURCE_PATH, None)
            if offline_flag_source_path is None
            else offline_flag_source_path
        )
        self.offline_poll_interval_seconds = (
            float(env_or_default(ENV_VAR_OFFLINE_POLL_INTERVAL_SECONDS, 1.0))
            if offline_poll_interval_seconds is None
            else offline_poll_interval_seconds
        )

        self.cache_type = (
            CacheType(env_or_default(ENV_VAR_CACHE_TYPE, CacheType.DISABLED))
            if cache_type is None
            else cache_type
        )

        self.max_cache_size = (
            env_or_default(ENV_VAR_MAX_CACHE_SIZE, 16, cast=int)
            if max_cache_size is None
            else max_cache_size
        )
