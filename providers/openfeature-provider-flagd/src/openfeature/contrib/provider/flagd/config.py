import os
import typing
from enum import Enum

ENV_VAR_MAX_EVENT_STREAM_RETRIES = "FLAGD_MAX_EVENT_STREAM_RETRIES"

ENV_VAR_KEEP_ALIVE_TIME_MS = "FLAGD_KEEP_ALIVE_TIME_MS"

ENV_VAR_DEADLINE_MS = "FLAGD_DEADLINE_MS"
ENV_VAR_STREAM_DEADLINE_MS = "FLAGD_STREAM_DEADLINE_MS"

ENV_VAR_CACHE_TYPE = "FLAGD_CACHE_TYPE"
ENV_VAR_HOST = "FLAGD_HOST"
ENV_VAR_MAX_CACHE_SIZE = "FLAGD_MAX_CACHE_SIZE"
ENV_VAR_OFFLINE_FLAG_SOURCE_PATH = "FLAGD_OFFLINE_FLAG_SOURCE_PATH"
ENV_VAR_OFFLINE_POLL_INTERVAL_SECONDS = "FLAGD_OFFLINE_POLL_INTERVAL_SECONDS"
ENV_VAR_PORT = "FLAGD_PORT"
ENV_VAR_RESOLVER_TYPE = "FLAGD_RESOLVER_TYPE"
ENV_VAR_RETRY_BACKOFF_MS = "FLAGD_RETRY_BACKOFF_MS"
ENV_VAR_SELECTOR = "FLAGD_SELECTOR"
ENV_VAR_TLS = "FLAGD_TLS"

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
    RPC = "rpc"
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
        selector: typing.Optional[str] = None,
        resolver_type: typing.Optional[ResolverType] = None,
        offline_flag_source_path: typing.Optional[str] = None,
        retry_backoff_ms: typing.Optional[int] = None,
        cache_type: typing.Optional[CacheType] = None,
        max_cache_size: typing.Optional[int] = None,
        deadline: typing.Optional[int] = None,
        stream_deadline_ms: typing.Optional[int] = None,
        keep_alive_time: typing.Optional[int] = None,
        max_event_stream_retries: typing.Optional[int] = None,
    ):
        self.host = env_or_default(ENV_VAR_HOST, "localhost") if host is None else host
        self.tls = (
            env_or_default(ENV_VAR_TLS, False, cast=str_to_bool) if tls is None else tls
        )
        self.retry_backoff_ms: int = (
            int(env_or_default(ENV_VAR_RETRY_BACKOFF_MS, 1000, cast=int))
            if retry_backoff_ms is None
            else retry_backoff_ms
        )
        self.selector = (
            env_or_default(ENV_VAR_SELECTOR, None) if selector is None else selector
        )
        self.resolver_type = (
            ResolverType(env_or_default(ENV_VAR_RESOLVER_TYPE, "rpc"))
            if resolver_type is None
            else resolver_type
        )

        default_port = 8013 if self.resolver_type is ResolverType.RPC else 8015
        self.port: int = (
            int(env_or_default(ENV_VAR_PORT, default_port, cast=int))
            if port is None
            else port
        )
        self.offline_flag_source_path = (
            env_or_default(ENV_VAR_OFFLINE_FLAG_SOURCE_PATH, None)
            if offline_flag_source_path is None
            else offline_flag_source_path
        )

        self.cache_type = (
            CacheType(env_or_default(ENV_VAR_CACHE_TYPE, CacheType.LRU))
            if cache_type is None
            else cache_type
        )

        self.max_cache_size: int = (
            int(env_or_default(ENV_VAR_MAX_CACHE_SIZE, 1000, cast=int))
            if max_cache_size is None
            else max_cache_size
        )

        self.deadline: int = (
            int(env_or_default(ENV_VAR_DEADLINE_MS, 500, cast=int))
            if deadline is None
            else deadline
        )

        self.stream_deadline_ms: int = (
            int(env_or_default(ENV_VAR_STREAM_DEADLINE_MS, 600000, cast=int))
            if stream_deadline_ms is None
            else stream_deadline_ms
        )

        self.keep_alive_time: int = (
            int(env_or_default(ENV_VAR_KEEP_ALIVE_TIME_MS, 0, cast=int))
            if keep_alive_time is None
            else keep_alive_time
        )

        self.max_event_stream_retries: int = (
            int(env_or_default(ENV_VAR_MAX_EVENT_STREAM_RETRIES, 5, cast=int))
            if max_event_stream_retries is None
            else max_event_stream_retries
        )
