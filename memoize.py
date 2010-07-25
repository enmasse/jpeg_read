# memoize.py
# Shamelessly copied from http://programmingzen.com/2009/05/18/memoization-in-ruby-and-python/

def memoize(function):
    cache = {}
    def decorated_function(*args):
        try:
            return cache[args]
        except KeyError:
            val = function(*args)
            cache[args] = val
            return val
    return decorated_function

