"""
Concrete classes to use other interpreter.

The way to build a interface is like below.
- Inherit Command class and override them.
    + is_not_input_head
    + make_key_pair
    + make_code
    + is_not_input_head
- Inherit InterpreterObject class and override ABCmethods.
- Inherit Interpreter class which catches arguments like below.
    + Instance of class inherited from Command object.
    + Class inherited from InterpreterObject class.

Not very easy.
It may be big class to fit interpreter perfectly.
"""
from typing import Any, Optional, List, Union, Tuple, Dict, cast
from os import environ
from subprocess import Popen, PIPE, STDOUT
from io import StringIO
import uuid
import csv
import json
import numpy as np
import pandas as pd
from .base import Command, InterpreterObject, InterpreterException, Interpreter


class RCommand(Command):
    def __init__(self) -> None:
        self.inter = Popen(['R', '--vanilla', '--quiet', '--no-readline'],
                           stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        to_send, to_get = self.make_key_pair(
            str(uuid.uuid1()).replace('-', '_'))
        self.write(to_send)
        self.flush()
        while True:
            if self.readline() == to_get:
                break

    def make_code(self, code: str) -> str:
        return f'try({code})' + '\n'

    def make_key_pair(self, time_stamp: str) -> Tuple[str, str]:
        return (
            f'print("{self.make_stamp(time_stamp)}")\n',
            f'[1] "{self.make_stamp(time_stamp)}"\n'
        )

    def make_send_command(self, name: str, value: str) -> str:
        return f'class({name} <- {value})'

    def make_let_command(self, name: str, value: Any) -> str:
        '''
        Make 'let' in interpreter.
        If there is no let in the interpreter, it does not anything.
        '''
        return f'class({name} <- {value})'

    def make_const_command(self, name: str, value: Any) -> str:
        '''
        Make 'let' in interpreter.
        If there is no let in the interpreter, it does not anything.
        '''
        return f'class({name} <- {value})'

    def close(self) -> None:
        return f'q("yes")'


class DenoCommand(Command):
    def __init__(self) -> None:
        environ['NO_COLOR'] = '1'
        self.inter = Popen(['deno'],
                           stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        self.write('let PythonObjects = {};')
        to_send, to_get = self.make_key_pair(
            str(uuid.uuid1()).replace('-', '_'))
        self.write(to_send)
        self.flush()
        while True:
            if self.readline() == to_get:
                break

    def make_key_pair(self, time_stamp: str) -> Tuple[str, str]:
        return (
            f'"{self.make_stamp(time_stamp)}"\n',
            f'"{self.make_stamp(time_stamp)}"\n'
        )

    def make_send_command(self, name: str, value: str) -> str:
        return f'{name} = {value};'

    def make_code(self, code: str) -> str:
        return f'{code}' + ';'

    def make_let_command(self, name: str, value: Any) -> str:
        '''
        Make const in interpreter.
        If there is no let in the interpreter, it does not anything.
        '''
        if isinstance(value, DenoObject):
            return f"let {name} = {value._code}"
        elif isinstance(value, InterpreterObject):
            return f"let {name} = JSON.parse('{json.dumps(value.to_python())}')"
        return f"let {name} = JSON.parse({json.dumps(value)})"

    def make_const_command(self, name: str, value: Any) -> str:
        '''
        Make const in interpreter.
        If there is no const in the interpreter,
        it is same as let in the interpreter.
        '''
        if isinstance(value, DenoObject):
            return f"const {name} = {value._code}"
        elif isinstance(value, InterpreterObject):
            return f"const {name} = JSON.parse('{json.dumps(value.to_python())}')"
        return f"const {name} = JSON.parse({json.dumps(value)})"

    def make_tmp_variable(self, stamp: str) -> str:
        '''
        Make tmp variable.
        '''
        return f'PythonObjects.py{stamp}'

    def close(self) -> None:
        return f'close()'


class RObject(InterpreterObject):
    '''
    Wrapper of R object to deal it in python world.
    This object is little bit complicated
    because of nature of R language.
    '''

    def __init__(self, name: str, interpreter: Interpreter,
                 code: Optional[str] = None,
                 value: Optional[str] = None) -> None:
        self._name = name
        self._code = code if code else name
        self._value = value
        self._inter = interpreter
        self._inter_indent = 4

    def __call__(self, *args: Any, kwargs: dict = {}) -> 'RObject':
        '''
        This method lets python object perform like R function.
        It can takes both of RObject and python object.
        If it has taken RObject, it just sends it to R world.
        If it has taken python object,
        it converts the object to R code.
        Then, it sends the code to via pipe between python and R.
        And so, it can treat python object
        and RObject simultaneously.
        Optional arguments must be given as 'kwargs' because
        in R world, '.' is one of normal character and
        this nature leads syntax error of python.

        >>> r = Interpreter(RCommand(), RObject)
        >>> # Callable object like python!
        >>> t_test = r['t.test']
        >>> # Sending a object.
        >>> r['r_vector_int'] = [9, 4, 5, 1]
        >>> # Then, run the function.
        >>> result = t_test(r['r_vector_int'], [1, 2, 4, 5], kwargs={'paired': True}) 
        >>> print(0.5285171 < result['p.value'].to_python() < 0.5285173)
        True
        '''
        code_args = ",".join(
            arg._code if isinstance(arg, RObject)
            else RObject._convert_to_interpreter(arg)
            for arg in args)
        code_kwargs = ",".join([
            f'{key}={kwargs[key].code}'
            if isinstance(kwargs[key], RObject)
            else f'{key}={RObject._convert_to_interpreter(kwargs[key])}'
            for key in kwargs])
        if kwargs:
            code = f'{self._code}({code_args}, {code_kwargs})'
        else:
            code = f'{self._code}({code_args})'
        time_stamp = str(uuid.uuid1()).replace('-', '_')
        tmp_name = self._inter.make_tmp_variable(time_stamp)
        self._inter.send(f'{tmp_name} <- {code}')
        self._inter.flush()
        return RObject(name=code, code=tmp_name,
                       interpreter=self._inter)

    def __getitem__(self, name: Union[int, str, tuple]) -> 'RObject':
        '''
        Gets elements of items in R by name.
        It returns as RObject.
        For example, $ or [[1]] operators.

        Slice function is not developped well.
        '''
        if self._inter.get(f'is.list({self._code})').strip() == '[1] TRUE':
            if isinstance(name, str):
                code = f'{self._code}${name}'
            elif isinstance(name, int):
                code = f'{self._code}[[{name}]]'
            elif isinstance(name, slice):
                if name.start and name.stop:
                    code = f'{self._code}[{name.start}:{name.stop}]'
                else:
                    raise BaseException('Slice is not good for R')
            else:
                raise BaseException('Slice or getting item could not work')
        else:
            if isinstance(name, int):
                code = f'{self._code}[{int(name)+1}]'
            else:
                raise BaseException(
                    'In this case, slice should be int or slice')
        return RObject(name=code, code=code, interpreter=self._inter)

    def _operator(self, obj: Any, operator: str) -> 'InterpreterObject':
        if not isinstance(obj, RObject):
            obj = RObject._convert_to_interpreter(obj)
        code = f'({self._code} {operator} {obj})'
        time_stamp = str(uuid.uuid1()).replace('-', '_')
        tmp_name = self._inter.make_tmp_variable(time_stamp)
        # print(f'{tmp_name} <- {code};')
        return RObject(name=code, code=tmp_name, interpreter=self._inter)

    def __setitem__(self, key: str, obj: Any) -> None:
        code = f'{self._code}${key} <- {self._convert_to_interpreter(obj)}'
        self._inter.send(code)

    def __setattr__(self, key: str, obj: Any) -> None:
        InterpreterObject.__setattr__(self, key, obj)

    def __str__(self) -> str:
        return f'RObject[{self._name}: {self._code}]'

    def _convert_character(self) -> Union[List[str], str]:
        '''
        Convert strings of R into RObject.
        '''
        length = self._inter.get(
            f'length({self._name})')[self._inter_indent:].strip()
        if length == '1':
            value = self._inter.get(self._name).strip()
            return value[self._inter_indent+1:len(value)-1]
        value = self._inter.get(
            f'write.csv({self._name}, row.names=FALSE)').strip()
        return [s[1:-1] for s
                in value[self._inter_indent:len(value)].split('\n')]

    def _convert_numeric(self) -> Union[float, list]:
        '''
        Convert numeric of R into RObject.
        '''
        r_key = self._inter.send(self._name)
        length_key = self._inter.send(f'length({self._name})')
        self._inter.flush()
        value = self._inter.receive_by_key(r_key).strip()
        length = self._inter.receive_by_key(
            length_key)[self._inter_indent:].strip()
        if length == '1':
            return float(self._remove_index(value)[0])
        return [float(i) for i in
                ' '.join(self._remove_index(value)).split(' ')
                if i != '']

    def _remove_index(self, text: str) -> List[str]:
        return [line[line.index(']')+1:] for line in
                text.split('\n')]

    def _convert_matrix(self) -> np.array:
        '''
        Convert matrix of R into RObject.
        '''
        value = self._inter.get(f'write.csv({self._name})').strip()
        return np.array(list(csv.reader(value.strip().split('\n'))))

    def _convert_dataframe(self) -> pd.DataFrame:
        '''
        Convert data.frame of R into RObject.
        '''
        value = self._inter.get(
            f'write.csv({self._name}, row.names=FALSE)').strip()
        with StringIO(value) as data:
            df = pd.read_csv(data)
        return df

    def to_python(self) -> Any:
        '''
        This method just takes some R object from world of R.
        It does not record any objects in python world.
        '''
        name_key = self._inter.send(f'class({self._name})')
        self._inter.send(f'typeof({self._name})')
        self._inter.send(f'is.vector({self._name})')
        self._inter.send(f'class(try({self._name}))')
        self._inter.flush()

        inter_class = self._inter.receive_by_key(
            name_key)[self._inter_indent:].strip()
        inter_type = self._inter.receive_one()[1][
            self._inter_indent:].strip()
        is_vector = self._inter.receive_one()[1][
            self._inter_indent:].strip() == 'TRUE'
        error = self._inter.receive_one()[1].strip().split('\n')
        if error[-1][self._inter_indent:].strip() == '"try-error"':
            raise InterpreterException('\n'+'\n'.join(error[0:-1]))

        if is_vector:
            if inter_class == '"character"':
                return self._convert_character()
            elif inter_class == '"numeric"':
                return self._convert_numeric()
        else:
            if inter_class == '"matrix"':
                return self._convert_matrix()
            elif inter_class == '"data.frame"':
                return self._convert_dataframe()
            elif inter_class == '"function"' or inter_class == '"list"':
                return self
            else:
                return self._inter.get(self._name).strip()

    @classmethod
    def _convert_to_interpreter(cls, obj: Any) -> str:
        if isinstance(obj, InterpreterObject):
            obj = obj.to_python()
        if isinstance(obj, str):
            return f'"{obj}"'
        elif isinstance(obj, bool):
            return 'TRUE' if obj else 'FALSE'
        elif isinstance(obj, (int, float)):
            return str(obj)
        elif isinstance(obj, (tuple, list)):
            return f'c{tuple(obj)}'
        if isinstance(obj, pd.DataFrame):
            csv_tmp = obj.to_csv(columns=None, index=False)
            return f'read.csv(header=TRUE,sep=",",text="{csv_tmp}")'
        else:
            return ''

class DenoObject(InterpreterObject):
    def __init__(self, name: str, interpreter: Interpreter,
                 code: Optional[str] = None,
                 value: Optional[str] = None) -> None:
        self._name = name
        self._code = code if code else name
        self._value = value
        self._inter = interpreter

    @classmethod
    def _convert_to_interpreter(cls, obj: Any) -> str:
        if isinstance(obj, InterpreterObject):
            obj = obj.to_python()
        return json.dumps(obj)

    def __str__(self) -> str:
        return f'DenoObject[{self._name}: {self._code}]'

    def to_python(self) -> Any:
        key = self._inter.send(
            f'''try{{console.log(JSON.stringify({self._name}))}}catch(e){{console.log("JS error:", e)}}'''
        )
        self._inter.flush()
        result = self._inter.receive_by_key(key)
        try:
            return json.loads(result)
        except json.decoder.JSONDecodeError as er:
            raise InterpreterException(result)

    def __call__(self, *args: Any, **kwargs: Dict) -> 'DenoObject':
        '''
        This method lets python object perform like Deno function.
        It can takes both of DenoObject and python object.
        If it has taken DenoObject, it just sends it to Deno world.
        If it has taken python object,
        it converts the object to Javascript code.
        Then, it sends the code via pipe between python and Deno.
        And so, it can treat python object
        and DenoObjects simultaneously.
        '''
        code_args = ",".join(
            arg._code if isinstance(arg, DenoObject)
            else DenoObject._convert_to_interpreter(arg)
            for arg in args)
        code_kwargs = ",".join([
            f'{key}={cast(DenoObject, kwargs[key]).code}'
            if isinstance(kwargs[key], DenoObject)
            else f'{key}={DenoObject._convert_to_interpreter(kwargs[key])}'
            for key in kwargs])
        if kwargs:
            code = f'({self._code})({code_args}, {code_kwargs})'
        else:
            code = f'({self._code})({code_args})'
        time_stamp = str(uuid.uuid1()).replace('-', '_')
        tmp_name = self._inter.make_tmp_variable(time_stamp)
        self._inter.send(f'try{{{tmp_name} = {code};}}catch(er){{{tmp_name}=er}}')
        self._inter.flush()
        return DenoObject(name=code, code=tmp_name, interpreter=self._inter)

    def _operator(self, obj: Any, operator: str) -> 'DenoObject':
        if not isinstance(obj, DenoObject):
            obj = DenoObject._convert_to_interpreter(obj)
        code = f'({self._code} {operator} {obj})'
        time_stamp = str(uuid.uuid1()).replace('-', '_')
        tmp_name = self._inter.make_tmp_variable(time_stamp)
        # self._inter.send(f'try{{{tmp_name} = {code};}}catch(er){{{tmp_name}=er}}')
        # self._inter.flush()
        return DenoObject(name=code, code=tmp_name, interpreter=self._inter)

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

    def __getitem__(self, key: str) -> Any:
        code = f'{self._code}["{key}"]'
        return DenoObject(name=code, code=code, interpreter=self._inter)

    def __setitem__(self, key: str, obj: Any) -> None:
        code = f'{self._code}["{key}"] = {self._convert_to_interpreter(obj)}'
        self._inter.send(code)

    def __setattr__(self, key, obj) -> None:
        InterpreterObject.__setattr__(self, key, obj)


class R(Interpreter):
    def __init__(self) -> None:
        super().__init__(
            RCommand(),
            RObject
        )


class Deno(Interpreter):
    def __init__(self) -> None:
        super().__init__(
            DenoCommand(),
            DenoObject
        )


def get_code(obj: InterpreterObject) -> str:
    return obj._code


def get_name(obj: InterpreterObject) -> str:
    return obj._name
