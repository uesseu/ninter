'''
Base objects of ninter.
'''
from typing import Any, Optional, List, Union, Tuple, Callable, cast, Dict
from abc import abstractmethod
from subprocess import Popen, PIPE, STDOUT
import time
from collections import deque
debug = False

class Command:
    '''
    Base object of commands.
    Inherit this to make interface between
    python and other languages.
    These methods should be overwritten.
    - is_not_input_head
    - make_key_pair
    - make_code
    - is_not_input_head
    '''

    def __init__(self) -> None:
        self.inter: Popen

    def write(self, text: str) -> None:
        '''
        Wrapper to write text.
        '''
        if debug:
            print('write', text)
        self.inter.stdin.write(text.encode())

    def readline(self) -> str:
        '''
        Wrapper to read line.
        '''
        result = self.inter.stdout.readline().decode()
        if debug:
            print('got', result)
        return result

    def make_stamp(self, time_stamp: str) -> str:
        '''
        Make stamp code to talk with other language.
        The default value is
        f'Python code: Time[{time_stamp}]'
        The stamp may overlap, but it is rare.
        '''
        return f'Python code: Time[{time_stamp}]'

    def make_tmp_variable(self, time_stamp: str) -> str:
        '''
        Make a variable name to send something to python
        which has no name in other interpreter.
        '''
        return f'Python_tmp_object_{time_stamp}'

    def flush(self) -> None:
        '''
        Just a wrapper of flush of stdin for other interpreter.
        '''
        self.inter.stdin.flush()

    def is_not_input_head(self, text: str) -> bool:
        '''
        If the subprocess displays '>' at the top of input,
        the line including '>' at the head of it should be
        igonred.
        This method judges whether the line should be
        isgnored or not.

        text: str
            Line from subprocess.
        ====================
        Returns bool
        '''
        return len(text) != 0 and text[0] != '>'

    def make_code(self, code: str) -> str:
        '''
        ABC method to make code to send something to interpreter.
        It needs to be inherited.
        For example, in case of R, you need to send
        'try({code})'
        because if you send the raw code and error was occured,
        the interpreter cannot tell python error.
        '''
        return code

    @abstractmethod
    def make_key_pair(self, key: str) -> Tuple[str, str]:
        '''
        Abstract method to make key pair.
        It is not easy to divide codes in pipe stream.
        This program makes some words and catch it.
        '''
        pass

    @abstractmethod
    def getitem(self, name: str, interpreter: 'Interpreter') -> Any:
        '''
        Get object from interpreter.
        '''
        pass

    @abstractmethod
    def make_send_command(self, name: str, value: Any) -> str:
        '''
        Abstract method to make command.
        For example, in case of R, it appends try function.
        try([code])
        This procedure avoids interpreter stack and
        get stdin properly.
        '''
        pass

    @abstractmethod
    def make_let(self, name: str, value: str) -> str:
        '''
        Make const in interpreter.
        If there is no let in the interpreter, it does not anything.
        '''
        return ''

    @abstractmethod
    def make_const(self, name: str, value: str) -> str:
        '''
        Make const in interpreter.
        If there is no const in the interpreter,
        it is same as let in the interpreter.
        '''
        return ''


class InterpreterException(Exception):
    '''
    Exception class which should be raised
    when interpreter put a exception.
    '''
    def __init__(self, *args: str) -> None:
        self.args = args

    def __str__(self) -> str:
        ex_str = '\n    '.join(''.join(self.args).split('\n'))
        return f'\n\nInterpreter-Exception: {ex_str}'

class Interpreter:
    '''
    Wrapper of pipe between other interpreter and python.
    It offers interface between primitive pipe and
    language specific procedure.
    It is heigher level object than Command.

    This class is the basic object of this package.
    '''

    def __init__(self, command: Command, ObjectClass: type) -> None:
        self.command = command
        self.key_q: deque = deque()
        self.q_num = 0
        self.ObjectClass = ObjectClass

    def send(self, code: str) -> str:
        '''
        Send something.
        After sending, flush should be done before receive.
        code: str
            code to send
        Returns
        ==========
        Key of the sended object. The type is string.
        '''
        self.q_num += 1
        time_stamp = str(time.time())
        self.command.write(self.command.make_code(code))
        key_to_send, key = self.command.make_key_pair(time_stamp)
        self.command.write(key_to_send)
        self.key_q.append(key)
        return cast(str, key)

    def flush(self) -> None:
        '''
        Wrapper to flush stdout.
        '''
        self.command.flush()

    def receive_by_key(self, request_key: str) -> str:
        '''
        Receive str from interpreter until request key was catched.
        It ignores any lines or keys until the key was catched.
        '''
        while True:
            key, value = self.receive_one()
            if key == request_key:
                return value

    def get(self, name: str) -> str:
        '''
        Get output from interpreter.
        '''
        key = self.send(name)
        self.flush()
        return self.receive_by_key(key)

    def receive_one(self) -> Tuple[str, str]:
        '''
        Receive method to get one string with key.
        '''
        if self.q_num == 0:
            return '', ''
        strings: List[str] = []
        key = self.key_q.popleft()
        while True:
            tmp = self.command.readline()
            if tmp == key:
                break
            if self.command.is_not_input_head(tmp):
                strings.append(tmp)
        self.q_num -= 1
        result = ''.join(strings)
        return key, result

    def __setitem__(self, name: str, value: Any) -> None:
        '''
        Set object to interpreter.
        '''
        if isinstance(value, self.ObjectClass):
            self.get(self.command.make_send_command(name, value.name))
        elif isinstance(value, InterpreterObject):
            self.get(self.command.make_send_command(
                name,
                self.ObjectClass._convert_to_interpreter(value.to_python())))
        else:
            self.get(self.command.make_send_command(
                name,
                self.ObjectClass._convert_to_interpreter(value)))

    def __getitem__(self, name: str) -> 'InterpreterObject':
        '''
        Get object from interpreter.
        '''
        return self.ObjectClass(name=name, interpreter=self)

    def make_tmp_variable(self, time_stamp: str) -> str:
        '''
        Make a variable name to send something to python
        which has no name in other interpreter.
        '''
        return self.command.make_tmp_variable(time_stamp)

    def let(self, name: str, value: str) -> None:
        key = self.send(self.command.make_let(name, value))
        self.flush()
        self.receive_by_key(key)

    def const(self, name: str, value: str) -> None:
        key = self.send(self.command.make_const(name, value))
        self.flush()
        self.receive_by_key(key)

    def __del__(self) -> None:
        self.command.inter.kill()

class InterpreterObject:
    '''
    ABC to make object from other interpreter
    perform like python object.
    '''

    def __init__(self, name: str, interpreter: Interpreter,
                 code: Optional[str] = None,
                 value: Optional[str] = None) -> None:
        self.inter = interpreter
        self.code = code
        self.value = value

    @classmethod
    @abstractmethod
    def _convert_to_interpreter(cls, obj: Any) -> str:
        '''
        Class method to make some python object
        to be a string to send to interpreter.
        '''
        return ''

    @abstractmethod
    def to_python(self) -> Any:
        '''
        This method takes some object from other interpreter.
        It does not record any objects in python world.
        '''
        pass

    @abstractmethod
    def __del__(self) -> Any:
        '''
        Delete the object.
        If the object has no deleting function, do nothing.
        '''
        pass

    @abstractmethod
    def _is_function(self, ) -> bool:
        '''
        Check whether it is callable or not.
        '''
        return True

