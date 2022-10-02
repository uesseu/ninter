# Ninter
Ninter is a python package to use interpreter.  
This is my hobby project and may be buggy.  
Currently, it can use R and Deno.  
Ninter has a ability to manipulate other interpreters  
like python code by 'get' method.  
For example...  

```python
from ninter import start_r, start_deno
r = start_r()
deno = start_deno()

array = deno['Array']  # Deno object
x = array(*range(5))  # Deno object
y = array(3, 3, 4, 5, 6).get()  # Python object got from Deno
t_test = r['t.test']  # R function was imported

# And then... Deno and Python object was processed by R function!
result = t_test(x, y, options={'paired': True})['p.value']

# Finally, the result was received.
print(result.get())
>>> 0.0003881713
```

# Usage
## Start
Make instances of interpreter.
```python
from ninter import start_r
r = start_r()
r['hoge'] = 3
```
## Set item
Instances can get something by braces of 'set item'.

```python
from ninter import start_r
r = start_r()
r['hoge'] = 3
```

## Get item
'get item' braces returns interpreter specific object.
The item in the brace must be a string.

```python
from ninter import start_r
r = start_r()
result = r['3']
print(result.get())
```

You can get function by such braces, too.
And such functions can run in python.
In case of R, you should use 'options' keyword because
R script allows dot in name of variables.
In case of Deno, you can use keyword arguments like python.

```python
from ninter import start_r
r = start_r()
t_test = r['t.test']
t_test(list(range(4)), list(range(2, 5)),
    options={})
```

# Sending commands
If you want to send command to interpreter, you can write like this.

```python
from ninter import start_deno
deno = start_deno()
deno.send('class Hoge{constructor(){} fuga(){return "fuga"}}')
deno.send('let hoge=new Hoge()')
print(deno['hoge.fuga()'].get())
```

In this case, class is defined in deno and it worked well.

# Higher-order function
If the interpreter supports higher-order function, it can run the function.

# Objects
You can manipulate object in Deno and item in R like python dict.
In case of Deno, it converts '\[\]' to '.'.
In case of R, it converts '\[\]' to '$'.

```python
from ninter import start_deno
Array = deno['Array']
assert(deno['Array'](4, 5)['join'](3).get() == '435')
```

# Algorithm
It is very simple. Just using pipe.  

- Convert python object to string
- Send some keyword to other interpreter
- Let other interpreter print the keyword
- Get stdout between keyword and other keyword
- Convert the stdout to python object

It depends on keyword and if you write print or console.log function  
perfectly, this package cannot work,  
however I think such situation is very very rare.
