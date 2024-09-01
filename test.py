"""
Test code of this package.
This is... just my hobby and may not be a good test code.
"""
from ninter.interpreter import (RCommand, RObject, DenoObject,
                         DenoCommand, Interpreter, InterpreterException,
                         )
import pandas as pd
from ninter import Deno, R, Bridge, Let, Const
import unittest
from logging import basicConfig, ERROR
basicConfig(level=ERROR)

class AssignTestBase:
    def test_let_assign(self) -> None:
        inter = self.make_command()
        inter.let('obj', self.send)
        assert inter['obj'].to_python() == self.catch
        inter.close()

    def test_const_assign(self) -> None:
        inter = self.make_command()
        inter.const('obj2', self.send)
        assert inter['obj2'].to_python() == self.catch
        inter.close()

    def test_function(self) -> None:
        inter = self.make_command()
        other = inter[self.function](self.send).to_python()
        answer = self.result
        if isinstance(other, RObject):
            return 0
        assert other == answer
        inter.close()

class RTestBase:

    def make_command(self):
        return Interpreter(RCommand(), RObject)


class RAssignNumber(RTestBase, AssignTestBase, unittest.TestCase):
    send = 3
    catch = 3.0
    function = '''(function (x) { return (x * 2) })'''
    result = 6.0

class RAssignString(RTestBase, AssignTestBase, unittest.TestCase):
    send = 'hoge'
    catch = 'hoge'
    function = '''function (x) { return (paste(x, 'fuga', sep='')) }'''
    result = 'hogefuga'

class DenoTestBase:
    inter = Interpreter(DenoCommand(), DenoObject)
    def make_command(self):
        return Interpreter(DenoCommand(), DenoObject)


class DenoAssignNumber(DenoTestBase, AssignTestBase, unittest.TestCase):
    send = 3
    catch = 3
    function = '''(x) => { return x * 2 }'''
    result = 6

class DenoAssignString(DenoTestBase, AssignTestBase, unittest.TestCase):
    send = 'hoge'
    catch = 'hoge'
    function = '''(x) => { return x + "fuga" }'''
    result = 'hogefuga'

def r_test() -> None:
    r = R()
    print('R Assign test')
    assert(r['3'].to_python() == 3.0)
    assert(r['"3"'].to_python() == '3')
    r['r_string'] = 'hoge'
    r.send('tmp_string <- r_string')
    r.flush()
    assert r['r_string'].to_python() == 'hoge'
    assert r['tmp_string'].to_python() == 'hoge'
    r.send('print("hoge")')
    r.flush()
    assert (r.receive_one()[1] == '[1] "hoge"\n')
    r['r_number'] = 9
    assert r['r_number'].to_python() == 9
    r['r_vector_int'] = [9, 4, 5, 1]
    r_vector = r['r_vector_int']
    assert r['r_vector_int'].to_python() == [9., 4., 5., 1.]
    r['r_dataframe'] = pd.DataFrame([9, 4, 5, 1])
    assert r['names(r_dataframe)'].to_python() == 'X0'
    assert str(r['r_dataframe'].to_python()) == str(
        pd.DataFrame([9, 4, 5, 1], columns=['X0']))
    r['r_dataframe'] = pd.DataFrame([[9, 4, 5, 1], [4, 2, 9, 1]])
    assert (str(r['r_dataframe'].to_python())
            == str(pd.DataFrame([[9, 4, 5, 1], [4, 2, 9, 1]],
                                columns=['X0', 'X1', 'X2', 'X3'])))
    t_test = r['t.test']
    names = r['names']
    assert names(t_test(r_vector, [1, 2, 4]))[0].to_python() == 'statistic'
    r['l'] = [3, 4, '2']
    assert r['l'].to_python() == ['3', '4', '2']
    assert t_test(r_vector, [1, 2, 4, 5], kwargs={'paired': True})[
        'p.value'].to_python() == 0.5285172
    r['long_data'] = list(range(200))
    assert r['long_data'].to_python() == [float(i) for i in range(200)]
    r['long_data'] = list(range(10000))
    assert r['long_data'].to_python() == [float(i) for i in range(10000)]
    print('DF', r['r_dataframe'].to_python())

# def r_bridge_test() -> None:
#     r = Bridge(R())
#     print('R Assign test')
#     r.r_string = 'hoge'
#     r.flush()
#     assert r.r_string.to_python() == 'hoge'
#     r.r_number = 9
#     assert r.r_number.to_python() == 9
#     r.r_vector_int = [9, 4, 5, 1]
#     r_vector = r.r_vector_int
#     assert r.r_vector_int.to_python() == [9., 4., 5., 1.]
#     r.r_dataframe = pd.DataFrame([9, 4, 5, 1])
#     assert str(r.r_dataframe.to_python()) == str(
#         pd.DataFrame([9, 4, 5, 1], columns=['X0']))
#     r.r_dataframe = pd.DataFrame([[9, 4, 5, 1], [4, 2, 9, 1]])
#     assert (str(r.r_dataframe.to_python())
#             == str(pd.DataFrame([[9, 4, 5, 1], [4, 2, 9, 1]],
#                                 columns=['X0', 'X1', 'X2', 'X3'])))
#     t_test = r['t.test']
#     names = r.names
#     assert names(t_test(r_vector, [1, 2, 4]))[0].to_python() == 'statistic'
#     r.l = [3, 4, '2']
#     assert r.l.to_python() == ['3', '4', '2']
#     assert t_test(r_vector, [1, 2, 4, 5], kwargs={'paired': True})[
#         'p.value'].to_python() == 0.5285172
#     r['long_data'] = list(range(200))
#     assert r.long_data.to_python() == [float(i) for i in range(200)]
#     r.long_data = list(range(10000))
#     assert r.long_data.to_python() == [float(i) for i in range(10000)]


def error_test() -> None:
    print('R error test')
    r = Interpreter(RCommand(), RObject)
    try:
        r['ho'].to_python()
    except InterpreterException as er:
        print(er.args)
        assert "\nError : object 'ho' not found" == er.args[0]
    try:
        r['t.test(t.test)'].to_python()
    except InterpreterException as er:
        assert "Error in x[xok] : object of type 'closure' is not subsettable" in str(er)
    try:
        t_test = r['t.test']
        t_test().to_python()
    except InterpreterException as er:
        assert 'Error in t.test.default() : argument "x" is missing, with no default' in str(er)

def deno_test() -> None:
    print('####################')
    print('# Deno test')
    print('####################')
    deno = Interpreter(DenoCommand(), DenoObject)
    print('# Assign test')
    deno.let('fuga', 4)
    assert type(deno['fuga'].to_python()) == int
    deno['fuga'] = 5
    assert(deno['fuga'].to_python() == 5)
    deno['fuga'] = [4, 5, 5, 3]
    print('# Convert to deno test')
    assert(deno['fuga'].to_python() == [4, 5, 5, 3])
    assert(deno['Array'](4, 5).to_python() == [4, 5])
    print('# Function test')
    assert(deno['Array'](4, 5).join(3).to_python() == '435')
    deno_id = deno['Array'](4, 5).join(3)._code
    assert(deno[deno_id].to_python() == '435')
    array = deno['Array']
    print('# Lambda function test')
    assert (array(*list(range(10))).map(deno['x=>x*8']).to_python()
            == [0, 8, 16, 24, 32, 40, 48, 56, 64, 72])
    print('# Error reporting test')
    try:
        print(array(deno['hi']).to_python())
    except BaseException as er:
        if ('ReferenceError: hi is not defined' in er.args[0]):
            print('Error could reported successfully')
        else:
            raise er
    try:
        print(deno['ho'].to_python())
    except BaseException as er:
        if ('ReferenceError: ho is not defined' in er.args[0]):
            print('Error could reported successfully')
        else:
            raise er

def deno_bridge_test() -> None:
    print('Deno test')
    deno = Bridge(Deno())
    Let(deno).fuga = 4
    deno.fuga = 5
    print('Assign test')
    assert(deno.fuga.to_python() == 5)
    deno.fuga = [4, 5, 5, 3]
    print('done')
    print('Convert to deno test')
    assert (deno.fuga.to_python() == [4, 5, 5, 3])
    assert (deno.Array(4, 5).to_python() == [4, 5])
    print('done')
    print('Function test')
    assert (deno.Array(4, 5).join(3).to_python() == '435')
    deno_id = deno.Array(4, 5).join(3)._code
    assert (deno[deno_id].to_python() == '435')
    array = deno.Array
    print('done')
    print('Lambda function test')
    assert (array(*range(10)).map(deno['x=>x*8']).to_python()
            == [0, 8, 16, 24, 32, 40, 48, 56, 64, 72])
    print('done')
    print('Error reporting test')
    try:
        print(array(deno.hi).to_python())
    except:
        print('Error could reported successfully')
    try:
        print(deno.ho.to_python())
    except:
        print('Error could reported successfully')
    print('done')


def inter() -> None:
    r, deno = R(), Deno()
    r['hoge'] = 5
    deno.let('hoge', 'null')
    deno['hoge'] = r['hoge']
    print(deno['hoge'])
    print(deno['hoge'].to_python())
    array = deno['Array']
    x = array(*range(5))
    y = array(3, 3, 4, 5, 6).to_python()
    t_test = r['t.test']
    print(t_test(x, y, kwargs={'paired': True})['p.value'].to_python())



def main() -> None:
    r_test()
#    r_bridge_test()
    error_test()
    deno_test()
#    deno_bridge_test()
    inter()
    deno = Deno()
    print(deno['4'].to_python())
    print(deno['r=>5'](4).to_python())
    print(deno['function(){return 7}'](5).to_python())
    assert(deno['''function(){
  return 7
}'''](5).to_python() == 7)
    deno.send('let hoge=4')
    print(deno['hoge'].to_python())
    deno.send('''
class Hoge{
  constructor(){}
  fuga(){
    return "fuga"
  }
}
''')
    deno.send('let hoge=new Hoge()')
    print(deno['hoge.fuga()'].to_python())
    deno.send('close()')


if __name__ == '__main__':
    # r = Bridge(R())
    # deno_base = Deno()
    # deno = Bridge(deno_base)
    # t_test = r['t.test']
    # Let(deno).piyo = 5
    # # Let(deno).something = list(range(5))
    # deno_base.let('something', list(range(5)))
    # print(type(deno.something.to_python()))
    # deno_base['something'] = list(range(5))
    # print(type(deno.something.to_python()))
    # print(deno.piyo.to_python())
    # deno.something = list(range(5))
    # print(type(deno.something.to_python()))

    # a = deno.Array(*deno.something.to_python())
    # print(a)
    # print(a.to_python())
    # b = [2, 3, 4, 5]
    # print(deno['(x=>x*4)'](4)._code)
    # result = t_test(a, b)#['p.value']
    # print(result._code)
    # print(result.to_python())
    # print(deno.piyo.to_python())
    main()
    r = R()
    r.let('hoge', 4)
    print(r['hoge'])
    print((r['hoge'] * 7).to_python())
    deno = Deno()
    deno.let('hoge', 4)
    print((deno['hoge'] * 9).to_python())
    print(deno['hoge'].code)
    unittest.main()

    # deno = Bridge(Deno())
    # r = Bridge(R())
    # Let(deno).obj = 4
    # deno.obj = 5
    # deno['obj'] = 9
    # deno['let hoge'] = 8
    # summary = r['summary']
    # t_test = r['t.test']
    # print(deno['x => x * 8'](deno.obj).to_python())
    # print((deno.obj * 2 + 4).to_python())
    # print(deno['Array(3,4,5)'].to_python())
    # print(deno['obj'].to_python())
    # print(deno['hoge'].to_python())
    # print(summary(t_test([1, 2, 3, 4], [3.4, 4, 5,6], kwargs=dict(pair=True))).to_python())
    # print(deno['x=>x*4'](4).to_python())
