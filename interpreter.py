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
import time
import csv
import json
import numpy as np
import pandas as pd
from doctest import testmod
from base import Command, InterpreterObject, InterpreterException, Interpreter


class RCommand(Command):
    def __init__(self) -> None:
        self.inter = Popen(['R', '--vanilla', '--quiet', '--no-readline'],
                           stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        to_send, to_get = self.make_key_pair(str(time.time()))
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


class DenoCommand(Command):
    def __init__(self) -> None:
        environ['NO_COLOR'] = '1'
        self.inter = Popen(['deno'],
                           stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        self.write('let PythonObjects = {};')
        to_send, to_get = self.make_key_pair(str(time.time()))
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

    def make_let(self, name: str, value: str) -> str:
        '''
        Make const in interpreter.
        If there is no let in the interpreter, it does not anything.
        '''
        return f'let {name} = JSON.parse({json.dumps(value)});'

    def make_const(self, name: str, value: str) -> str:
        '''
        Make const in interpreter.
        If there is no const in the interpreter,
        it is same as let in the interpreter.
        '''
        return f'const {name} = JSON.parse({json.dumps(value)});'

    def make_tmp_variable(self, stamp:str) -> str:
        '''
        Make tmp variable.
        '''
        return f'PythonObjects.py{stamp}'

class RObject(InterpreterObject):
    '''
    Wrapper of R object to deal it in python world.
    This object is little bit complicated
    because of nature of R language.
    '''

    def __init__(self, name: str, interpreter: Interpreter,
                 code: Optional[str] = None,
                 value: Optional[str] = None) -> None:
        self.name = name
        self.code = code if code else name
        self.value = value
        self.inter = interpreter
        self.inter_indent = 4

    def __call__(self, *args: Any, options: dict = {}) -> 'RObject':
        '''
        This method lets python object perform like R function.
        It can takes both of RObject and python object.
        If it has taken RObject, it just sends it to R world.
        If it has taken python object,
        it converts the object to R code.
        Then, it sends the code to via pipe between python and R.
        And so, it can treat python object
        and RObject simultaneously.
        Optional arguments must be given as 'options' because
        in R world, '.' is one of normal character.

        >>> r = Interpreter(RCommand(), RObject)
        >>> # Callable object like python!
        >>> t_test = r['t.test']
        >>> # Sending a object.
        >>> r['r_vector_int'] = [9, 4, 5, 1]
        >>> # Then, run the function.
        >>> result = t_test(r['r_vector_int'], [1, 2, 4, 5], options={'paired': True}) 
        >>> print(0.5285171 < result['p.value'].to_python() < 0.5285173)
        True
        '''
        code_args = ",".join(
            arg.code if isinstance(arg, RObject)
            else RObject._convert_to_interpreter(arg)
            for arg in args)
        code_kwargs = ",".join([
            f'{key}={options[key].code}'
            if isinstance(options[key], RObject)
            else f'{key}={RObject._convert_to_interpreter(options[key])}'
            for key in options])
        if options:
            code = f'{self.code}({code_args}, {code_kwargs})'
        else:
            code = f'{self.code}({code_args})'
        time_stamp = str(time.time()).replace('.', '_')
        tmp_name = self.inter.make_tmp_variable(time_stamp)
        self.inter.send(f'{tmp_name} <- {code}')
        self.inter.flush()
        return RObject(name=code, code=tmp_name,
                       interpreter=self.inter)

    def __getitem__(self, name: Union[int, str, tuple]) -> 'RObject':
        '''
        Gets elements of items in R by name.
        It returns as RObject.
        For example, $ or [[1]] operators.

        Slice function is not developped well.
        '''
        if self.inter.get(f'is.list({self.code})').strip() == '[1] TRUE':
            if isinstance(name, str):
                code = f'{self.code}${name}'
            elif isinstance(name, int):
                code = f'{self.code}[[{name}]]'
            elif isinstance(name, slice):
                if name.start and name.stop:
                    code = f'{self.code}[{name.start}:{name.stop}]'
                else:
                    raise BaseException('Slice is not good for R')
            else:
                raise BaseException('Slice or getting item could not work')
        else:
            if isinstance(name, int):
                code = f'{self.code}[{int(name)+1}]'
            else:
                raise BaseException(
                    'In this case, slice should be int or slice')
        return RObject(name=code, code=code, interpreter=self.inter)

    def __str__(self) -> str:
        return f'RObject[{self.name}: {self.code}]'

    def _convert_character(self) -> Union[List[str], str]:
        '''
        Convert strings of R into RObject.
        '''
        length = self.inter.get(
            f'length({self.name})')[self.inter_indent:].strip()
        if length == '1':
            value = self.inter.get(self.name).strip()
            return value[self.inter_indent+1:len(value)-1]
        value = self.inter.get(
            f'write.csv({self.name}, row.names=FALSE)').strip()
        return [s[1:-1] for s
                in value[self.inter_indent:len(value)].split('\n')]

    def _convert_numeric(self) -> Union[float, list]:
        '''
        Convert numeric of R into RObject.
        '''
        r_key = self.inter.send(self.name)
        length_key = self.inter.send(f'length({self.name})')
        self.inter.flush()
        value = self.inter.receive_by_key(r_key).strip()
        length = self.inter.receive_by_key(
            length_key)[self.inter_indent:].strip()
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
        value = self.inter.get(f'write.csv({self.name})').strip()
        return np.array(list(csv.reader(value.strip().split('\n'))))

    def _convert_dataframe(self) -> pd.DataFrame:
        '''
        Convert data.frame of R into RObject.
        '''
        value = self.inter.get(
            f'write.csv({self.name}, row.names=FALSE)').strip()
        with StringIO(value) as data:
            df = pd.read_csv(data)
        return df

    def to_python(self) -> Any:
        '''
        This method just takes some R object from world of R.
        It does not record any objects in python world.
        '''
        name_key = self.inter.send(f'class({self.name})')
        self.inter.send(f'typeof({self.name})')
        self.inter.send(f'is.vector({self.name})')
        self.inter.send(f'class(try({self.name}))')
        self.inter.flush()

        inter_class = self.inter.receive_by_key(
            name_key)[self.inter_indent:].strip()
        inter_type = self.inter.receive_one()[1][
            self.inter_indent:].strip()
        is_vector = self.inter.receive_one()[1][
            self.inter_indent:].strip() == 'TRUE'
        error = self.inter.receive_one()[1].strip().split('\n')
        if error[-1][self.inter_indent:].strip() == '"try-error"':
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
                return self.inter.get(self.name).strip()

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
        self.name = name
        self.code = code if code else name
        self.value = value
        self.inter = interpreter

    @classmethod
    def _convert_to_interpreter(cls, obj: Any) -> str:
        if isinstance(obj, InterpreterObject):
            obj = obj.to_python()
        return json.dumps(obj)

    def __str__(self) -> str:
        return f'DenoObject[{self.name}: {self.code}]'

    def to_python(self) -> Any:
        key = self.inter.send(
            f'try{{console.log(JSON.stringify({self.name}))}}catch(e){{console.log("JS error:", e)}}'
        )
        self.inter.flush()
        result = self.inter.receive_by_key(key)
        try:
            return json.loads(result)
        except json.decoder.JSONDecodeError as er:
            raise InterpreterException(result)

    def __getattribute__(self, name: str):
    def __call__(self, *args: Any, **kwargs: Dict) -> 'DenoObject':
        '''
        This method lets python object perform like Deno function.
        It can takes both of DenoObject and python object.
        If it has taken RObject, it just sends it to R world.
        If it has taken python object,
        it converts the object to Javascript code.
        Then, it sends the code to via pipe between python and Deno.
        And so, it can treat python object
        and DenoObjects simultaneously.
        '''
        code_args = ",".join(
            arg.code if isinstance(arg, DenoObject)
            else DenoObject._convert_to_interpreter(arg)
            for arg in args)
        code_kwargs = ",".join([
            f'{key}={cast(DenoObject, kwargs[key]).code}'
            if isinstance(kwargs[key], DenoObject)
            else f'{key}={DenoObject._convert_to_interpreter(kwargs[key])}'
            for key in kwargs])
        if kwargs:
            code = f'({self.code})({code_args}, {code_kwargs})'
        else:
            code = f'({self.code})({code_args})'
        time_stamp = str(time.time()).replace('.', '_')
        tmp_name = self.inter.make_tmp_variable(time_stamp)
        self.inter.send(f'try{{{tmp_name} = {code};}}catch(er){{{tmp_name}=er}}')
        self.inter.flush()
        return DenoObject(name=code, code=tmp_name, interpreter=self.inter)

    def __getitem__(self, key: str) -> Any:
        code = f'{self.code}["{key}"]'
        return DenoObject(name=code, code=code, interpreter=self.inter)


if __name__ == '__main__':
    testmod()
