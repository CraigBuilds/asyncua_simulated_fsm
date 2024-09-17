# Introduction

An OPCUA Server exposing a simulation of a machine that can be enabled, disabled, jogged (start moving), and aborted (stop moving). It is implemented using an async finite state machine.

# Dependencies
```
pip install asyncua
pip install aioconsole #for tests
```

# Usage

`python server_main.py`

# Architecture

`MyServer` composes `MyOpcuaAddressSpace` and `MyFSM`.

The FSM contains an instance of an IState object, representing the current state. The IState object contains a back reference to the FSM, and overridable methods for the state's transition functions. Concrete states should override these methods to set the current state of the FSM.
When a new state is entered, the transition will be logged, and 3 abstract methods will be called, `self.on_enter`, `self.start_state_behaviour`, and `old_state.stop_state_behaviour()`. These can be used to read/write to the opcua address space, and to create and stop asyncio tasks that run loops and write to the opcua address space (e.g incrementing the position value while in the jog state).

The address space creates the opcua nodes on initialisation, and has properties (getters and setters) for the node values.
It uses an XML UANodeSet to configure the address space. 
It also has a method to register a callback that will be triggered when the COMMAND node is written to.

For example:

```python
address_space.register_callback(NODE_COMMAND_VALUES.DISABLE, lambda: print("DISABLED"))
```

This will print "DISABLED" when the COMMAND node is written to with the value of DISABLE.

`MyServer` registers callbacks that attempt to transition the FSM when the COMMAND node is written to. 