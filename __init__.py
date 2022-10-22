"""
Objects to use other interpreters like python.
Now, R and Deno is available.
"""
import interpreter

class R(interpreter.Interpreter):
    def __init__(self) -> None:
        super().__init__(
            interpreter.RCommand(),
            interpreter.RObject
        )

class Deno(interpreter.Interpreter):
    def __init__(self) -> None:
        super().__init__(
            interpreter.DenoCommand(),
            interpreter.DenoObject
        )
