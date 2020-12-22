# Astro scripting 0.1
![](https://img.shields.io/badge/Implementation-Python%203.9-important)
![](https://img.shields.io/badge/Version-0.1-%2333aa33)
![](https://img.shields.io/tokei/lines/github/xyLotus/Astro-Scripting?label=Total%20lines)

Astro Scripting (short: ASX), is a simple, interpreted scripting language implemented in Python.


## Syntax
### Variables
Because Astro is an dynamic typed language, so you don't have to specify the types.
```
var = 12
x = 12 * var
```
### Comments
```
-- Single line comments
/-- Multi
    line
    comments --/
```

### Functions 
```
#function_name(param):
      say "something"
      return param
      

-- Function calling
function_name(12)
```

### Arrays
This will print `2`, as elements in the array are counted from 0.
```
array = [1, 2, "a string"]
say array[1]

```

### Conditions
```
if 1 == 2:
    say "Something is wrong here!"
elif 1 >= 3:
    say "This is even worse"
else:
    say "Math works!"
```


## Statements
* `say <data>` - outputs the passed data to stdout
* `wait <seconds>` - waits / pausees the program for the selected time


## Data types
* String `"a string"`
* Number `7.1`
* Boolean `True` / `False`
* Array `[1, 2, "3"]`
Note: arrays can be multi-type
