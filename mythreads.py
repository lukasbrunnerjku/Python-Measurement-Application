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



class Fifo:
    """FIFO ... First In First Out buffer
    in such a buffer the threads will temporaly store the data
    the access is synchronized wich is needed when multiple threads accessing it
    with Lock.acquire() and Lock.release() used internally we ensure that only
    one thread at a time can access the fifo buffer -> no data corruption possible
    """
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
        if self.count == 0:
            print(self, "has already finished the work")
        else:
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
        self.container.update(self.container.new_measurement_init())

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
