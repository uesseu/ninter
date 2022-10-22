"""
Test code of this package.
This is... just my hobby and may not be a good test code.
"""
from interpreter import (RCommand, RObject, DenoObject,
                         DenoCommand, Interpreter, InterpreterException,
                         )
import pandas as pd
from __init__ import Deno, R


def r_test() -> None:
    r = Interpreter(RCommand(), RObject)
    print('R Assign test')
    assert(r['3'].to_python() == 3.0)
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
    assert t_test(r_vector, [1, 2, 4, 5], options={'paired': True})[
        'p.value'].to_python() == 0.5285172
    r['long_data'] = list(range(200))
    assert r['long_data'].to_python() == [float(i) for i in range(200)]
    r['long_data'] = list(range(10000))
    assert r['long_data'].to_python() == [float(i) for i in range(10000)]


def error_test() -> None:
    print('R error test')
    r = Interpreter(RCommand(), RObject)
    try:
        r['ho'].to_python()
    except InterpreterException as er:
        assert "Error in try(ho) : object 'ho' not found" in str(er)
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
    print('Deno test')
    deno = Interpreter(DenoCommand(), DenoObject)
    deno.let('fuga', '4')
    deno['fuga'] = 5
    print('Assign test')
    assert(deno['fuga'].to_python() == 5)
    deno['fuga'] = [4, 5, 5, 3]
    print('Convert to deno test')
    assert(deno['fuga'].to_python() == [4, 5, 5, 3])
    assert(deno['Array'](4, 5).to_python() == [4, 5])
    print('Function test')
    assert(deno['Array'](4, 5)['join'](3).to_python() == '435')
    deno_id = deno['Array'](4, 5)['join'](3).code
    assert(deno[deno_id].to_python() == '435')
    array = deno['Array']
    print('Lambda function test')
    assert (array(*list(range(10)))['map'](deno['x=>x*8']).to_python()
            == [0, 8, 16, 24, 32, 40, 48, 56, 64, 72])
    print('Error reporting test')
    try:
        print(array(deno['hi']).to_python())
    except:
        print('Error could reported successfully')
    try:
        print(deno['ho'].to_python())
    except:
        print('Error could reported successfully')


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
    print(t_test(x, y, options={'paired': True})['p.value'].to_python())



def main() -> None:
    r_test()
    error_test()
    deno_test()
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
    deno.send('class Hoge{constructor(){} fuga(){return "fuga"}}')
    deno.send('let hoge=new Hoge()')
    print(deno['hoge.fuga()'].to_python())
    deno.send('close()')


if __name__ == '__main__':
    main()
