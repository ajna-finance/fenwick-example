# Fenwick Example

A simple reference implementation of scaled Fenwick Trees and a prototype of Ajna in Python.

`fenwickscaletree.py` is a library of scaled Fenwick tree functions

`ajnasimple.py` is a prototype implementation a simple subset of core Ajna functionality using the scaled Fenwick tree library

`main.py` contains another implementation of Ajna with similar interface and limited functionality, using arrays and iteration

For an explanation of scaled Fenwick trees, refer to https://ieeexplore.ieee.org/document/10196100

## Development
### Requirements
- `python` 3.0+
- `numpy`


## Tests
### Forge tests
- run tests of scaled Fenwick tree
```
python fenwickscaletree.py
```

- run sim of a few transactions of the Ajn prototype using scaled Fenwick Trees
```
python ajnasimple.py
```

- run test of Ajna prototype using arrays and iteration
```
python main.py
```
