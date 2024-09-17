from asyncua.common.subscription import DataChangeNotif #type: ignore
from asyncua import Node #type: ignore
from typing import Awaitable, Callable, Any
from asyncio import iscoroutinefunction
from typing import Protocol


class Handler(Protocol):
    async def datachange_notification(
        self, node: Node, val: Any, data: DataChangeNotif
    ):
        ...


def wrap_subscription_callback(
    callback: Callable[[Node, Any, DataChangeNotif], Awaitable]
) -> Handler:
    """
    Wraps a callable or coroutine into a form used by self.__server.create_subscription().
    This is so you do not have to create a new class every time, and it abstracts
    from async or non async callbacks.

    e.g use:

        async def my_cb(node: Node, val: Any, data: DataChangeNotif):
            logging.info("Hello)

        sub = await self.__server.create_subscription(
            1, wrap_subscription_callback(my_cb)
        )
        sub.subscribe_data_change(self.__greeter_node)

    """

    if iscoroutinefunction(callback):

        class AsyncSubscriptionCallback:
            async def datachange_notification(
                self, node: Node, val: Any, data: DataChangeNotif
            ):
                await callback(node, val, data)

        return AsyncSubscriptionCallback()
    else:

        class SubscriptionCallback:
            def datachange_notification(
                self, node: Node, val: Any, data: DataChangeNotif
            ):
                callback(node, val, data)

        return SubscriptionCallback()
