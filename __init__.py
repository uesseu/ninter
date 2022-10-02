import interpreter

def start_deno() -> interpreter.Interpreter:
    return interpreter.Interpreter(
        interpreter.DenoCommand(), interpreter.DenoObject)

def start_r() -> interpreter.Interpreter:
    return interpreter.Interpreter(
        interpreter.RCommand(), interpreter.RObject)
