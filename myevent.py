# basic event class which can have multiple handler objects added to it
# usage example:
# event1 = myevent.Event()
# event1.add(handler)
# or
# event1 += handler
# (handler must be an callable object: function, method or object with __call__)
# if it should be signalized that an event1 has happened call:
# event1()
# --> then the code of the registered handlers will be executed!!
class Event(object):

    def __init__(self):
        self.handlers = []

    def add(self, handler):
        self.handlers.append(handler)
        return self

    def remove(self, handler):
        self.handlers.remove(handler)
        return self

    def fire(self, sender, earg=None):
        for handler in self.handlers:
            handler(sender, earg)

    __iadd__ = add
    __isub__ = remove
    __call__ = fire
