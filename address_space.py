from tkinter import N
from asyncua import Server, Node, ua  #type: ignore
from asyncua.common.xmlimporter import XmlImporter #type: ignore
from typing import Awaitable, Callable, List, Dict, Optional
from enum import Enum
from wrap_subscription_callback import wrap_subscription_callback
import aioconsole #type: ignore #(for testing)

AsyncFn = Callable[[], Awaitable] #type aliases

class NODE_NAME_ENUM(Enum):
    """
    Create an ENUM so we can store the nodes in a dictionary and access them by name
    """
    MY_NODES = "MY_NODES"
    POSITION = "POSITION"
    VOLTAGE = "VOLTAGE"
    COMMAND = "COMMAND"
    MODE = "MODE"

    @classmethod
    def from_str(cls, name: str) -> 'NODE_NAME_ENUM':
        return cls[name]

class NODE_COMMAND_VALUES(Enum):
    """
    This represents the Command Nodes integer enum values
    """
    DEFAULT = 0
    DISABLE = 1
    ENABLE = 2
    JOG = 3
    ABORT = 4

class MyOpcuaAddressSpace:
    """
    Composes a set of opcua nodes (imported via XML) and callbacks to be executed when the COMMAND node is written to.
    Exposes a function to register a callback that will be triggered when the COMMAND node is written to with a certain value. <- This is used by Simulator class to transition the FSM
    Exposes a property to read and write to the value of each of the nodes. <- This is used by the Simulator class to simulate how the values change over time
    """

    async def async_init(self, server: Server, xml_file_path: str):
        """
        Import the nodes from the XML file, store them in a dictionary, and create a subscription to the COMMAND node to monitor for changes.
        """
        
        self.__server = server

        #Create dictionaries with empty values for the nodes and callbacks
        self.__nodes: Dict[NODE_NAME_ENUM, Optional[Node]] = {
            NODE_NAME_ENUM.MY_NODES: None,
            NODE_NAME_ENUM.POSITION: None,
            NODE_NAME_ENUM.VOLTAGE: None,
            NODE_NAME_ENUM.COMMAND: None,
            NODE_NAME_ENUM.MODE: None
        }
        self.__cmd_callbacks: Dict[NODE_COMMAND_VALUES, Optional[AsyncFn]] = {
            NODE_COMMAND_VALUES.DEFAULT: None,
            NODE_COMMAND_VALUES.DISABLE: None,
            NODE_COMMAND_VALUES.ENABLE: None,
            NODE_COMMAND_VALUES.JOG: None,
            NODE_COMMAND_VALUES.ABORT: None
        }

        importer = XmlImporter(server)
        imported_nodes: List[ua.NodeId] = await importer.import_xml(xml_file_path)

        #Fill the dictionaries with the imported nodes and callbacks
        for node_id in imported_nodes:
            node: Node = self.__server.get_node(node_id)

            NODE_NAME = NODE_NAME_ENUM.from_str((await node.read_display_name()).Text)
            self.__nodes[NODE_NAME] = node

            #if the node is the COMMAND node, create a subscription to it to monitor for changes. Call the appropriate cmd callback when the value changes
            if NODE_NAME == NODE_NAME_ENUM.COMMAND:
                async def subscription_callback(_, cmd_integer_value: int, _dcn): #is late binding fix needed here?
                    COMMAND = NODE_COMMAND_VALUES(cmd_integer_value)
                    cmd_callback = self.__cmd_callbacks[COMMAND]
                    if cmd_callback is not None:
                        await cmd_callback()
                sub = await self.__server.create_subscription(
                    1, wrap_subscription_callback(subscription_callback)
                )
                await sub.subscribe_data_change(node)

    def register_callback(
        self, command: NODE_COMMAND_VALUES, callback: AsyncFn
    ) -> None:
        """
        register an async function to be called when the COMMAND node is written with a certain value, for example:
        when the COMMAND node is written with the value 0, call the callback that was registered with the DISABLE enum,
        when the COMMAND node is written with the value 1, call the callback that was registered with the ENABLE enum,
        when the COMMAND node is written with the value 2, call the callback that was registered with the JOG enum
        """
        self.__cmd_callbacks[command] = callback

    """
    Getters and setters for the nodes in the address space
    """

    @property
    async def position(self) -> int:
        node = self.__nodes[NODE_NAME_ENUM.POSITION]
        assert node is not None
        return await node.get_value()
    
    async def set_position(self, value: int) -> None:
        node = self.__nodes[NODE_NAME_ENUM.POSITION]
        assert node is not None
        await node.write_value(value, ua.VariantType.UInt32)

    @property
    async def voltage(self) -> int:
        node = self.__nodes[NODE_NAME_ENUM.VOLTAGE]
        assert node is not None
        return await node.get_value()

    async def set_voltage(self, value: int) -> None:
        node = self.__nodes[NODE_NAME_ENUM.VOLTAGE]
        assert node is not None
        await node.write_value(value, ua.VariantType.UInt32)

    @property
    async def command(self) -> NODE_COMMAND_VALUES:
        node = self.__nodes[NODE_NAME_ENUM.COMMAND]
        assert node is not None
        return NODE_COMMAND_VALUES(await node.get_value())

    async def set_command(self, value: NODE_COMMAND_VALUES) -> None:
        node = self.__nodes[NODE_NAME_ENUM.COMMAND]
        assert node is not None
        await node.write_value(value.value, ua.VariantType.UInt32)

    @property
    async def mode(self) -> NODE_COMMAND_VALUES:
        node = self.__nodes[NODE_NAME_ENUM.MODE]
        assert node is not None
        value = await node.get_value()
        return NODE_COMMAND_VALUES(value)

    async def set_mode(self, value: NODE_COMMAND_VALUES) -> None:
        node = self.__nodes[NODE_NAME_ENUM.MODE]
        assert node is not None
        await node.write_value(value.value, ua.VariantType.UInt32)

"""
--- TESTS ---
"""

if __name__ == "__main__":
    import asyncio

    async def test():
        server = Server()
        await server.init()
        server.set_endpoint("opc.tcp://localhost:4840/freeopcua/server/")
        address_space = MyOpcuaAddressSpace()
        await address_space.async_init(server, "D:/sandbox/hlcs_tutorial/simulator/nodeset.xml")
        await server.start()

        #test the namespace was created and the nodes were imported correctly
        assert await address_space.position is not None

        #test reading the opcua node default values
        assert await address_space.position == 42
        assert await address_space.voltage == 240
        assert await address_space.command == NODE_COMMAND_VALUES.DEFAULT

        #test writing to the opcua node values
        await address_space.set_position(43)
        await address_space.set_voltage(241)
        assert await address_space.position == 43
        assert await address_space.voltage == 241

        #test registering callbacks for when the COMMAND node is written to with a certain value
        called = [False, False, False]
        async def my_disable_callback():
            print("disable called")
            called[0] = True
        async def my_enable_callback():
            print("enable called")
            called[1] = True
        async def my_jog_callback():
            print("jog called")
            called[2] = True

        address_space.register_callback(NODE_COMMAND_VALUES.DISABLE, my_disable_callback)
        address_space.register_callback(NODE_COMMAND_VALUES.ENABLE, my_enable_callback)
        address_space.register_callback(NODE_COMMAND_VALUES.JOG, my_jog_callback)

        #test that the correct callbacks are called when the COMMAND node is written to

        print("calling disable")
        await address_space.set_command(NODE_COMMAND_VALUES.DISABLE)
        await asyncio.sleep(0.1) #give the callbacks time to run
        assert called == [True, False, False]
        called = [False, False, False]

        print("calling enable")
        await address_space.set_command(NODE_COMMAND_VALUES.ENABLE)
        await asyncio.sleep(0.1)
        assert called == [False, True, False]
        called = [False, False, False]

        print("calling jog")
        await address_space.set_command(NODE_COMMAND_VALUES.JOG)
        await asyncio.sleep(0.1)
        assert called == [False, False, True]
        called = [False, False, False]

        #test calling a command twice
        print("calling disable twice")
        await address_space.set_command(NODE_COMMAND_VALUES.DISABLE)
        await asyncio.sleep(0.1)
        assert called == [True, False, False]
        called = [False, False, False]

        print("calling disable again (should do nothing)")
        await address_space.set_command(NODE_COMMAND_VALUES.DISABLE)
        await asyncio.sleep(0.1)
        assert called == [False, False, False] #should not have been called again
        called = [False, False, False]

        print("All tests passed, press Enter to exit")
        await aioconsole.ainput()

    asyncio.run(test())