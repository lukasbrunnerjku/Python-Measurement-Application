import threading
import time
# we will need the next import for the DrawingProcess and the Lock
# -> note: threading.Lock works with threads only while the
# multiprocessing.Lock will work with both threads and processes!
import multiprocessing

# this is only use to get fake instrument data into the buffer:
import random

# this is for the event handling e.g. of an error event in the MeasurementThread:
from myevent import Event


# FIFO ... First In First Out
# in such a buffer the threads will temporaly store the data
# the access is synchronized wich is needed when multiple threads accessing it
# with acquire() and release() we ensure that only one thread at a time
# can access the fifo buffer -> no data corruption possible:
class Fifo:

    def __init__(self):
        self.data = []
        # self.lock = threading.Lock()
        # the above code is for pure thread use only, with processes we need:
        # (nothing else changes due to the same interface of both Lock implementations)
        self.lock = multiprocessing.Lock()

    def has_item(self) -> bool:
        return len(self.data) > 0

    # a higher order function that executes an access function synchronized:
    def synchronized_access(self, access_function, *args):
        obj = None
        try:
            self.lock.acquire()
            # here an error could be raised!
            obj = access_function(*args)
        except Exception as e:
            print(e)
        finally:
            # make sure to release the lock even in error case or
            # it will block forever!
            self.lock.release()
        return obj

    def _clear_data(self):
        self.data.clear()

    def clear_data(self):
        self.synchronized_access(self._clear_data)

    def _push(self, data):
        self.data.append(data)

    def push(self, data):
        self.synchronized_access(self._push, data)

    def _pop(self):
        return self.data.pop(0)

    def pop(self) -> object:
        return self.synchronized_access(self._pop)

# --- start of test code ---
"""
The following DrawingThread isn't working because matplotlib isn't thread safe
and the DrawingProcess isn't working because the graph object must be created
inside the Process (tkinter objects can't be parameters of a process! -> pickle error
because processes don't share memory with the main process we run the other code in...
so there will be sent an copy of the objects e.g. the graph and interval object
to the DrawingProcess! This objects need to be serialized to be sent and that's
not possible for tkinter objects!
--> so the graph needs to be created inside the process
--> therefore we can't integrate a automatically updating graph feature in this
application like that!
"""
# basic drawing functionality with drawing method we will call every interval
# seconds the update method of the given Graph object!
class BasicDrawing():

    def __init__(self, graph, interval):
        self.graph = graph
        self.interval = interval
        self.flag = True

    def drawing(self):
        print("Starting the drawing...")
        while self.flag:
            start = time.time()

            # do the drawing of fresh data here with the graph object:
            print("Updating the Graph object...")
            self.graph.update()

            dur = time.time() - start
            if dur < self.interval:
                time.sleep(self.interval - dur)
        print("Drawing has stopped!")

    def stop(self):
        self.flag = False

# we inherite from the Thread class and the BasicDrawing class to keep our code DRY
class DrawingThread(threading.Thread, BasicDrawing):

    def __init__(self, graph, interval):
        threading.Thread.__init__(self)
        BasicDrawing.__init__(graph, interval)

    def run(self):
        self.drawing()

# we inherite from the Process class and the BasicDrawing class to keep our code DRY
class DrawingProcess(multiprocessing.Process, BasicDrawing):

    def __init__(self, graph, interval):
        multiprocessing.Process.__init__(self)
        BasicDrawing.__init__(graph, interval)

    def run(self):
        self.drawing()

# only used to get fake instrument data with thread into the buffer as it will
# be the case in the real measurement application:
# (note: this is for test purpose only)
class FakeDataThread(threading.Thread):

    def __init__(self, fifo, count, interval):
        threading.Thread.__init__(self)
        self.fifo = fifo
        self.interval = interval
        self.count = count
        self.flag = True
        self.start_time = None

    def run(self):
        self.start_time = time.time()

        while self.count > 0 and self.flag:
            bundle = []
            self.count -= 1
            start = time.time()

            # here we simulate the measurement of 4 values,
            # time and 3 instrument values
            time.sleep(0.1)
            bundle.append(time.time() - self.start_time)
            for i in range(0, 3):
                bundle.append(random.random())

            # store the fake data on the fifo buffer:
            self.fifo.push(bundle)

            dur = time.time() - start
            if dur < self.interval:
                time.sleep(self.interval - dur)

    def stop(self):
        print("Fake data production has stopped!")
        self.flag = False

# --- end of test code ---

class MeasurementThread(threading.Thread):

    def __init__(self, name, interval, count, instrument, noe, fifo, error_routine):
        threading.Thread.__init__(self)
        # noe ... number of errors --> this must be >= 0
        assert noe>=0,"Number of errors must be >= 0!"

        self.name = name
        self.interval = interval
        # count ... numer of measurements we want to do
        self.count = count
        self.instrument = instrument
        self.noe = noe
        # a fifo buffer object to save the measured data in:
        self.fifo = fifo
        # a flag to stop the thread, call thread.stop() to set the flag to False
        self.run_flag = True
        # every MeasurementThread has an event object which can have multiple
        # handlers registered (added) to it... this handlers will execute their
        # code if the event is fired!
        self.error_event = Event()
        self.error_event.add(error_routine)
        # save the arguments in a tuple for the error_event handling!
        self.args = (name, interval, count, instrument, noe, fifo, error_routine)
        # if an error occurs in one thread than the other should wait with the
        # measurement of new data:
        self.wait_flag = False
        print("Created", self)

    def run(self):
        while self.count > 0 and self.run_flag:
            self.count -= 1
            success = False
            start = time.time()
            # the function can have errors from time to time, try count times
            # e.g. could happen when fetching data from an instrument
            while not success:
                try:
                    if self.wait_flag and self.run_flag:
                        # go into idle state, this should be done if one thread
                        # triggered the error event!
                        time.sleep(0.2)
                        # here we don't set success to True as long as wait is True!
                    elif self.run_flag:
                        # call the instruments measure function, here an error could happen:
                        value = self.instrument.measure()
                        # we only get here if we succesfuly called the function!
                        success = True
                    else:
                        # if stop button is pressed meanwhile we can leave the loop
                        break
                except Exception as e:
                    print(self, "function call failed!")
                    print("Error message:")
                    print(e)
                    self.noe -= 1
                    # try again after 1 second!
                    time.sleep(1)
                # if more failures then specified raise RuntimeError:
                if self.noe < 0:
                    print(self, "failed multiple times!")
                    # stop the thread:
                    self.stop()
                    print("Starting error routine...")
                    self.error_event(self, earg=self.args)
                    break

            if success == False:
                # if we don't do that the last succesfully measured value
                # will be pushed on data queue in error case!
                break
            # put the result of the measure method on the fifo buffer:
            self.fifo.push(value)
            print(self, "put value:", value, "on data queue!")

            # for timing control of measurement:
            dur = time.time() - start
            print("{} needed {}s to execute measurement succesfuly!".format(self, dur))
            if dur < self.interval:
                time.sleep(self.interval - dur)
                
        # if stop button pressed we will come to this point, where the thread
        # really has stopped!
        print(self, "has stopped!")

    def stop(self):
        print(self, "trying to stopp!")
        self.run_flag = False

    def wait(self):
        print(self, "will go into idle mode!")
        self.wait_flag = True

    def go(self):
        print(self, "will go into measurement mode!")
        self.wait_flag = False

    def __repr__(self):
        return "MeasurementThread: {} with id: {}".format(self.name, id(self))

class UpdateThread(threading.Thread):

    def __init__(self, fps, container, fifos, instruments, buffer):
        threading.Thread.__init__(self)
        # interval ... interval in which the thread calls container.update()
        self.interval = 1.0/fps
        # the container object which should be updated,
        # must have a update() and a create_header() method!
        self.container = container
        # fifos are the fifo buffers where all the different Instrument values
        # where collected, this is a list containing Fifo objects!
        self.fifos = fifos
        self.start_time = None
        # a list containing Instrument objects:
        self.instruments = instruments
        # we need the buffer to collect all the data and send it to the GraphPage:
        self.buffer = buffer
        # a flag to stop the thread, call thread.stop() to set the flag to False
        self.run_flag = True
        self.wait_flag = False
        print("Created", self)

    def run(self):
        #  we need a reference time:
        self.start_time = time.time()
        # update the container with the header message:
        self.container.update(self.container.create_header())

        while self.run_flag:
            start = time.time()
            all_have_item = True

            # for debbug purpose only:
            for fifo in self.fifos:
                print(fifo.data)

            for fifo in self.fifos:
                if not fifo.has_item():
                    all_have_item = False
                    # if one fifo has no item we can escape the for loop:
                    break

            # when all fifos have items:
            if all_have_item:
                # a bundle of all the measured data we also want to get plotted:
                bundle = []
                # create a message containing all the measurement information:
                # (time is trunctated to only show 3 digits after comma)
                time_ = float("%.3f" % (time.time() - self.start_time))
                bundle.append(time_)
                msg = "Time: {}, ".format(bundle[-1])
                # zip returns an iterator of tuples, so we can loop through
                # multiple lists in parallel:
                for fifo, instrument in zip(self.fifos, self.instruments):
                    # synchronized data access:
                    bundle.append(fifo.pop())
                    msg += "{}: {}, ".format(instrument.__class__.__name__, bundle[-1])
                # call the update function of the container:
                self.container.update(msg)
                # add the bundle of data to the buffer for the GraphPage,
                # synchronized data access:
                self.buffer.push(bundle)
                print("Data bundle sent to GraphPage:", bundle)

            # for timing control of the updates:
            dur = time.time() - start
            if dur < self.interval:
                time.sleep(self.interval - dur)

            # going into idle mode, if meanwhile the stop button is pressed
            # we leave the loop!
            while self.wait_flag and self.run_flag:
                print(self, "waiting...")
                # idle mode do nothing while wait is True!
                time.sleep(0.2)

        # if stop button pressed we will come to this point, where the thread
        # really has stopped!
        print(self, "has stopped!")

    def stop(self):
        print(self, "trying to stopp!")
        self.run_flag = False

    def wait(self):
        print(self, "in idle mode!")
        self.wait_flag = True

    def go(self):
        print(self, "in update mode!")
        self.wait_flag = False

    def __repr__(self):
        return "UpdateThread with id: {}".format(id(self))
