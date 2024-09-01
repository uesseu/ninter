'''
Base objects of ninter.
'''
from typing import Any, Optional, List, Union, Tuple, Callable, cast, Dict
from abc import abstractmethod
from subprocess import Popen, PIPE, STDOUT
import time
import uuid
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

    def close(self) -> None:
        self.inter.terminate()

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
    def make_let_command(self, name: str, value: str) -> str:
        '''
        Make const in interpreter.
        If there is no let in the interpreter, it does not anything.
        '''
        return ''

    @abstractmethod
    def make_const_command(self, name: str, value: str) -> str:
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

    def _setitem(self, name: str, value, make_command: Callable) -> None:
        if debug:
            print('code:', make_command(name, value))
        if isinstance(value, self.ObjectClass):
            self.get(make_command(name, value.name))
        elif isinstance(value, InterpreterObject):
            self.get(make_command(
                name,
                self.ObjectClass._convert_to_interpreter(value.to_python())))
        else:
            self.get(make_command(
                name,
                self.ObjectClass._convert_to_interpreter(value)))

    def __setitem__(self, name: str, value: Any) -> None:
        '''
        Set object to interpreter.
        '''
        self._setitem(name, value, self.command.make_send_command)

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

    def let(self, name: str, value: Any) -> None:
        if debug:
            print(self.command.make_let_command(name, value))
        self._setitem(name, value, self.command.make_let_command)

    def const(self, name: str, value: str) -> None:
        if debug:
            print(self.command.make_let_command(name, value))
        self._setitem(name, value, self.command.make_const_command)

    def close(self) -> None:
        self.send(';' + self.command.close() + ';\n')
        self.flush()
        self.command.inter.wait()
        self.command.close()


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

    def __getattr__(self, name: str) -> 'InterpreterObject':
        return self[name]

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

        In rare case, you may use 'to_python' method or member.
        If you want to use such a thing, you can use [].
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

    def _operator(self, obj: Any, operator: str) -> 'InterpreterObject':
        if not isinstance(obj, InterpreterObject):
            obj = self.__class__._convert_to_interpreter(obj)
        code = f'({self._code} {operator} {obj})'
        time_stamp = str(uuid.uuid1()).replace('-', '_')
        tmp_name = self._inter.make_tmp_variable(time_stamp)
        self._inter.send(f'try{{{tmp_name} = {code};}}catch(er){{{tmp_name}=er}}')
        self._inter.flush()
        return self.__class__(name=code, code=tmp_name, interpreter=self._inter)

    def __iadd__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '+')

    def __isub__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '-')

    def __imul__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '*')

    def __add__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '+')

    def __sub__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '-')

    def __mul__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '*')

    def __div__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '/')

    def __idiv__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '/')

    def __mod__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '%')

    def __imod__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '%')

    def __or__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '||')

    def __and__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '&&')

    def __lt__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '<')

    def __le__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '<=')

    def __gt__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '>')

    def __ge__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '>=')

    def __eq__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '===')

    def __ne__(self, obj: Any) -> 'InterpreterObject':
        return self._operator(obj, '!==')

class Bridge:
    '''
    Just a wrapper object to use Interpreter object
    like python object.
    '''

    def __init__(self, inter: Interpreter):
        object.__setattr__(self, '_inter', inter)

    def __getattr__(self, key: str) -> Any:
        return object.__getattribute__(self, '_inter')[key]

    def __setattr__(self, key: str, obj: Any) -> None:
        self._inter[key] = obj

    def __getitem__(self, key: str) -> Any:
        return self._inter[key]

    def __setitem__(self, key: str, obj: Any) -> None:
        self._inter[key] = obj

    def close(self):
        object.__getattribute__(self, '_inter').close()


class Let:
    '''
    A object to send variable to other interpreter
    with declaration statement like 'let'.

    It works with any interpreter.
    It should get Bridge object at first.

    >>> from ninter import R, Deno, Bridge, Let
    >>> r = Bridge(R)
    >>> Let(r).my_object = 'hoge'
    >>> print(r.my_object)
    '''

    def __init__(self, obj: Bridge) -> None:
        self._inter: Interpreter
        object.__setattr__(self, '_inter', obj._inter)

    def __setattr__(self, key: str, obj: Any) -> None:
        self._inter.let(key, obj)


class Const:
    '''
    A object to send variable to other interpreter
    with declaration statement like 'const'.

    It works with any interpreter.
    It should get Bridge object at first.
    '''

    def __init__(self, obj: Bridge) -> None:
        self._inter: Interpreter
        object.__setattr__(self, '_inter', obj._inter)

    def __setattr__(self, key: str, obj: Any) -> None:
        self._inter.const(key, obj)
