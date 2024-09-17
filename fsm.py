import asyncio
from typing import Optional, Union
from address_space import MyOpcuaAddressSpace, NODE_COMMAND_VALUES

class IState:

    def __init__(self, fsm: 'MyFSM', old_state: Optional['IState']) -> None:
        """
        This state object contains a back reference to it's parent FSM so it can transition the state.
        It also contains a reference to the previous state so it can stop the task created in start_state_behaviour.
        The FSM object contains a reference to the address space so it can read and write values to the nodes.
        """
        self._fsm = fsm
        if old_state is not None: old_state.stop_state_behaviour()
        self.on_enter()
        print(f'"{type(old_state).__name__}" -> "{self.__class__.__name__}"')
        self.start_state_behaviour()

    def on_enter(self):
        """Use this to perform any actions when the FSM transitions to this state."""
        pass

    def start_state_behaviour(self):
        """Use this to create a task that will run while the FSM is in this state."""
        pass

    def stop_state_behaviour(self):
        """Use this to stop the task created in start_state_behaviour."""
        pass

    """
    Default state methods that will be overridden by the subclasses.
    If they are not overridden, they will print a message saying that the method cannot be called from the current state.
    """

    def enable(self):
        print(f'Cannot enable from "{self.__class__.__name__}"')
    def disable(self):
        print(f'Cannot disable from "{self.__class__.__name__}"')
    def jog(self):
        print(f'Cannot jog from "{self.__class__.__name__}"')
    def abort(self):
        print(f'Cannot abort from "{self.__class__.__name__}"')

class DisabledState(IState):
    """
    Only 1 valid transition from the DisabledState: enable
    """
    def enable(self):
        self._fsm.state = EnabledState(self._fsm, self)

    def on_enter(self):
        async def task():
            await self._fsm.nodes.set_mode(NODE_COMMAND_VALUES.DISABLE)
        asyncio.create_task(task())

class EnabledState(IState):
    """
    2 valid transitions from the EnabledState: disable and jog
    """

    def disable(self):
        self._fsm.state = DisabledState(self._fsm, self)
    def jog(self):
        self._fsm.state = JogState(self._fsm, self)

    def on_enter(self):
        async def task():
            await self._fsm.nodes.set_mode(NODE_COMMAND_VALUES.ENABLE)
        asyncio.create_task(task())

class JogState(IState):
    """
    Only 1 valid transition from the JogState: abort
    """

    def abort(self):
        self._fsm.state = AbortState(self._fsm, self)

    def on_enter(self):
        async def task():
            await self._fsm.nodes.set_mode(NODE_COMMAND_VALUES.JOG)
        asyncio.create_task(task())

    def start_state_behaviour(self):
        async def task():
            while True:
                pos = await self._fsm.nodes.position
                await self._fsm.nodes.set_position(pos + 1)
                print(f"Jogging: {pos + 1}mm")
                await asyncio.sleep(0.5)

        self.task = asyncio.create_task(task())

    def stop_state_behaviour(self):
        self.task.cancel()
        print("Stopped Jogging")

class AbortState(IState):
    """
    2 valid transitions from the AbortState: disable and enable
    """

    def disable(self):
        self._fsm.state = DisabledState(self._fsm, self)
    def enable(self):
        self._fsm.state = EnabledState(self._fsm, self)

    def on_enter(self):
        async def task():
            await self._fsm.nodes.set_mode(NODE_COMMAND_VALUES.ABORT)
        asyncio.create_task(task())

class MyFSM:
    """
    A Finite State Machine that transitions between the DISABLE, ENABLE, and JOG states.
    It has a reference to the address space so it can read and write values to the nodes.
    It contains a state object that represents the current state of the FSM.
    The state object contains a back reference to the FSM so it can transition the state.
    """

    def __init__(self, nodes: Union[MyOpcuaAddressSpace, 'MockAddressSpace']) -> None:
        self.nodes = nodes
        self.state: IState = DisabledState(self, None) #contains a back reference to this FSM so it can transition the state

"""
--- TESTS ---
"""

class MockAddressSpace:
    def __init__(self) -> None:
        self.pos = 0
        self.mod = NODE_COMMAND_VALUES.DEFAULT

    @property
    async def position(self) -> int:
        return self.pos

    async def set_position(self, pos: int):
        self.pos = pos

    @property
    async def mode(self) -> NODE_COMMAND_VALUES:
        return self.mod

    async def set_mode(self, value: NODE_COMMAND_VALUES) -> None:
        self.mod = value


if __name__ == "__main__":

    async def test():
        address_space = MockAddressSpace()
        fsm = MyFSM(address_space)

        #check it starts in the DisabledState
        assert isinstance(fsm.state, DisabledState)

        #enable it and check it transitions to the EnabledState
        fsm.state.enable()
        assert isinstance(fsm.state, EnabledState)

        #disable it and check it transitions back to the DisabledState
        fsm.state.disable()
        assert isinstance(fsm.state, DisabledState)

        #try to jog while disabled and check it remains in the DisabledState
        fsm.state.jog()
        assert isinstance(fsm.state, DisabledState)

        #enable it and check it transitions to the EnabledState
        fsm.state.enable()
        assert isinstance(fsm.state, EnabledState)

        #jog it and check it transitions to the JogState
        fsm.state.jog()
        assert isinstance(fsm.state, JogState)

        print("Waiting 3 seconds...")
        await asyncio.sleep(3)

        #abort it and check it transitions to the AbortState
        fsm.state.abort()
        assert isinstance(fsm.state, AbortState)
        pos = await address_space.position

        print("Waiting 3 seconds...")
        await asyncio.sleep(3)
        #check it has stopped jogging
        assert pos == await address_space.position

    asyncio.run(test())