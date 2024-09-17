from asyncua import Server  #type: ignore
from simulator.address_space import *
from fsm import MyFSM
import asyncio

class MyServer(Server):
    """
    This class composes an opcua address space and a FSM.
    The address space has a method to register callbacks that will be triggered when the COMMAND node is written to with certain values.
    The FSM has a method to transition the state of the FSM.
    This class uses the address space to register callbacks that will transition the FSM.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__address_space = MyOpcuaAddressSpace()
        self.__fsm: Optional[MyFSM] = None #Can only create the FSM after the address space has been initialized

    async def async_init(self, xml_file_path: str):
        """
        Initialize the address space, and register the callbacks that will transition the FSM.
        """
        await self.__address_space.async_init(self, xml_file_path)
        await self.start() #Start the server (base class method)
        self.__fsm = MyFSM(self.__address_space) #FSM has access to the address space to read and write values to the nodes

        self.__address_space.register_callback(NODE_COMMAND_VALUES.DISABLE, self.__disable)
        self.__address_space.register_callback(NODE_COMMAND_VALUES.ENABLE, self.__enable)
        self.__address_space.register_callback(NODE_COMMAND_VALUES.JOG, self.__jog)
        self.__address_space.register_callback(NODE_COMMAND_VALUES.ABORT, self.__abort)

    async def __disable(self):
        """Try to transition the FSM to the DISABLE state."""
        self.__fsm.state.disable()

    async def __enable(self):
        """Try to transition the FSM to the ENABLE state."""
        self.__fsm.state.enable()

    async def __jog(self):
        """Try to transition the FSM to the JOG state."""
        self.__fsm.state.jog()

    async def __abort(self):
        """Try to transition the FSM to the ABORT state."""
        self.__fsm.state.abort()

async def main():
    server = MyServer()
    await server.init()
    server.set_endpoint("opc.tcp://localhost:4840/freeopcua/server/")
    await server.async_init("D:/sandbox/hlcs_tutorial/simulator/nodeset.xml")
    while True:
        await asyncio.sleep(0)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
