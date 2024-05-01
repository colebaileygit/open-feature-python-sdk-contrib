import json
import logging
import threading
import time

import grpc

from openfeature.evaluation_context import EvaluationContext
from openfeature.event import ProviderEventDetails
from openfeature.exception import ErrorCode, ParseError, ProviderNotReadyError
from openfeature.provider.provider import AbstractProvider

from ....config import Config
from ....proto.flagd.sync.v1 import sync_pb2, sync_pb2_grpc
from ..connector import FlagStateConnector
from ..flags import FlagStore

logger = logging.getLogger("openfeature.contrib")


class GrpcWatcher(FlagStateConnector):
    INIT_BACK_OFF = 2
    MAX_BACK_OFF = 120

    def __init__(
        self, config: Config, provider: AbstractProvider, flag_store: FlagStore
    ):
        self.provider = provider
        self.flag_store = flag_store
        channel_factory = grpc.secure_channel if config.tls else grpc.insecure_channel
        self.channel = channel_factory(f"{config.host}:{config.port}")
        self.stub = sync_pb2_grpc.FlagSyncServiceStub(self.channel)

        self.connected = False

        # TODO: Add selector

    def initialize(self, context: EvaluationContext) -> None:
        self.active = True
        self.thread = threading.Thread(target=self.sync_flags, daemon=True)
        self.thread.start()

        ## block until ready or deadline reached

        # TODO: get deadline from user
        deadline = 2 + time.time()
        while not self.connected and time.time() < deadline:
            time.sleep(0.05)
        logger.debug("Finished blocking gRPC state initialization")

        if not self.connected:
            raise ProviderNotReadyError(
                "Blocking init finished before data synced. Consider increasing startup deadline to avoid inconsistent evaluations."
            )

    def shutdown(self) -> None:
        self.active = False

    def sync_flags(self) -> None:
        request = sync_pb2.SyncFlagsRequest()  # type:ignore[attr-defined]

        retry_delay = self.INIT_BACK_OFF
        while self.active:
            try:
                logger.debug("Setting up gRPC sync flags connection")
                for flag_rsp in self.stub.SyncFlags(request):
                    flag_str = flag_rsp.flag_configuration
                    logger.debug(
                        f"Received flag configuration - {abs(hash(flag_str)) % (10 ** 8)}"
                    )
                    self.flag_store.update(json.loads(flag_str))

                    if not self.connected:
                        self.provider.emit_provider_ready(
                            ProviderEventDetails(
                                message="gRPC sync connection established"
                            )
                        )
                        self.connected = True
                        # reset retry delay after successsful read
                        retry_delay = self.INIT_BACK_OFF
                    if not self.active:
                        logger.info("Terminating gRPC sync thread")
                        return
            except grpc.RpcError as e:
                logger.error(f"SyncFlags stream error, {e.code()=} {e.details()=}")
            except json.JSONDecodeError:
                logger.exception(
                    f"Could not parse JSON flag data from SyncFlags endpoint: {flag_str=}"
                )
            except ParseError:
                logger.exception(
                    f"Could not parse flag data using flagd syntax: {flag_str=}"
                )

            self.connected = False
            self.provider.emit_provider_error(
                ProviderEventDetails(
                    message=f"gRPC sync disconnected, reconnecting in {retry_delay}s",
                    error_code=ErrorCode.GENERAL,
                )
            )
            logger.info(f"gRPC sync disconnected, reconnecting in {retry_delay}s")
            time.sleep(retry_delay)
            retry_delay = min(2 * retry_delay, self.MAX_BACK_OFF)
