# general imports:
from tkinter import *

# for the graph page:
import multiprocessing
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib import style
style.use("ggplot")
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)

# for the measurement page:
from tkinter import messagebox
from myinstruments import *
from mythreads import *
import time
import threading
# for retrieving all the classes of the myinstruments modul:
import sys, inspect

# --- custom frames ---

class GraphPage(Frame):
    """
    A GraphPage which supports up to 3 y-Axes that share the same x-Axis (Time)
    """

    # an abstract Graph class for all custom Graph classes to inherite from:
    class Graph():

        def update(self):
            raise NotImplementedError("No method: update() implemented on", self.__class__.__name__)

        def clear(self):
            raise NotImplementedError("No method: clear() implemented on", self.__class__.__name__)

    # e.g. this is the Graph class for the DrawingProcess:
    class FancyGraph(Graph):

        def __init__(self, frame, buffer, title, x_label, class_info):
            # contains the information what Instruments are selected in the MeasurementPage:
            self.class_info = class_info
            # a frame in which we want to have a graph with
            # update and clear functionality:
            self.frame = frame
            # the fifo buffer from which we get data:
            self.buffer = buffer
            # set up the graph:
            self.figure = Figure(figsize=(6,5), dpi=100)
            # some text to display on the graph:
            self.title = title
            self.x_label = x_label
            # will be filled later in setup_axes:
            self.y_labels, self.y_legend_labels, self.axes = [], [], []
            # pre defined styles so that the data points are visually destinguishable,
            # see the matplotlib docs to create your own styles for the axes:
            self.styles = [
            ("red", "r+-"),
            ("blue", "bx-"),
            ("green", "go-")
            ]
            # if we want to draw a line between the points we need to know the previous point:
            self.prev_data = None

            # set the axes up with all the properties defined above:
            self.setup_axes()

            self.canvas = FigureCanvasTkAgg(self.figure, master=self.frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
            toolbar = NavigationToolbar2Tk(self.canvas, self.frame)
            toolbar.update()

        def make_patch_spines_invisible(self, ax):
            ax.set_frame_on(True)
            ax.patch.set_visible(False)
            for sp in ax.spines.values():
                sp.set_visible(False)

        def setup_axes(self):
            # we need at least one axe to plot our data:
            axe = self.figure.add_subplot(111)
            axe.set_title(self.title)
            axe.set_xlabel(self.x_label)
            self.axes.append(axe)

            # get all the labels acording to the Instruments selected in the MeasurementPage:
            # (renews the y_labels and the y_legend_labels)
            self.renew_labels()

            # now add the other axes which should all share the same x axis:
            # (range: start index inclusive, end index exclusive)
            # e.g.: you want to have 3 axes so you have 3 labels: index _ = 1 then 2 then stop
            for _ in range(1, len(self.y_labels)):
                self.axes.append(axe.twinx())

            lines = []
            axe_nr = 0

            for axe, y_label, style, y_legend_label in zip(self.axes,
                                                           self.y_labels,
                                                           self.styles,
                                                           self.y_legend_labels):
                axe_nr += 1
                color, format = style
                # to name the axis and give it a color
                axe.set_ylabel(y_label, color=color)
                # this will disable the use of an offset or scientific notation:
                axe.ticklabel_format(useOffset=False, style='plain')
                # remove the grid lines
                axe.grid(b=False)
                # set the graph up with no data and the legend labels:
                # (plot returns a -> list <- of line objects)
                line, = axe.plot([], [], format, label=y_legend_label)
                lines.append(line)
                # if we have already set up 2 axes then for the third axis we need
                # to draw the spine on a different position or they will overlap:
                if axe_nr == 3:
                    # spine position for axes: first: 0, second: 1, thrid: 1.2
                    # -> first and second get position implicitly, thrid and above would
                    # be drawn over the previously drawn axes
                    axe.spines["right"].set_position(("axes", 1.2))
                    self.make_patch_spines_invisible(axe)
                    axe.spines["right"].set_visible(True)
                    self.figure.subplots_adjust(right=0.75)
            # show a legend with the labels specified in plot(...)
            # must be called on the host axis:
            axe.legend(lines, self.y_legend_labels, loc="upper left")

        def update(self):
            # instr1, instr2 ... measured data from each instrument,
            # the buffer data looks like: [[time, instr1, instr2,...], [...], ...]
            while self.buffer.has_item():
                data = self.buffer.pop()
                print("Data:", data)
                # the isntrument data starts at index 1 of data buffer:
                index = 1
                for axe, style in zip(self.axes, self.styles):
                    # we don't need the color here just the format of the points:
                    _, format = style
                    # auto scale is normally enabled but if we want to move around
                    # and zoom with the toolbar the autoscaling gets disabled and
                    # then we won't see the new plotted data because it's off screen
                    # with autoscale we will always see every data point on screen!
                    axe.autoscale(enable=True, axis='both', tight=None)
                    # if we have no previous data or we don't want to have a line,
                    # else we will draw a line which is why we need previous data
                    if self.prev_data == None or "-" not in format:
                        axe.plot(data[0], data[index], format)
                    else:
                        axe.plot((self.prev_data[0], data[0]),
                                 (self.prev_data[index], data[index]),
                                 format)
                    index += 1
                self.prev_data = data
            self.canvas.draw()

        def clear(self):
            # clear all the previously made axes:
            for axe in self.axes:
                axe.clear()
            # setting things up again:
            self.prev_data = None
            # clear the axes list:
            self.axes.clear()
            # set the axe up acordingly using the y_labels and y_legend_labels:
            self.setup_axes()
            # needs to be called after every change that should be drawn:
            self.canvas.draw()

        def renew_labels(self):
            # start with empty lists:
            self.y_labels.clear()
            self.y_legend_labels.clear()

            # in class_info there are all Instrument classes we want to plot measured data from!
            print("Classes used:", self.class_info)
            for cls in self.class_info:
                y_label, y_legend_label = cls.get_labels()
                self.y_labels.append(y_label)
                self.y_legend_labels.append(y_legend_label)


    def __init__(self, parent, buffer, class_info, title, *args, **kwargs):

        Frame.__init__(self, parent, *args, **kwargs)
        # this is needed for drawing the right labels acording to the selected
        # Instruments on the MeasurementPage:
        # (directly specify what Instruments you want axe/legend labels from, OR use
        # and empty list that is filled with the Instrument classes before calling show_page!)
        self.class_info = class_info

        self.buffer = buffer

        self.graph = None

        # the title for the graph:
        self.title = title
        # the labels of the axes:
        self.x_label = "Time in s"
        # the next two will be filled but we need to now which Instruments that
        # will be selected in the MeasurementPage!
        self.y_labels = []
        self.y_legend_labels = []

        # a label with an important hint:
        self.hint = Label(master=self,
                          text="After changing the Instruments press reset once before update!",
                          fg="red")
        # one button for the manual update:
        self.update_btn = Button(master=self, text="Update", command=self.update)
        # and one to clear the graph:
        self.clear_btn = Button(master=self, text="Clear", command=self.clear)
        # and one to show the graph when the Instruments are selected:
        self.show_btn = Button(master=self, text="Show graph", command=self.show_page)
        self.show_btn.pack()

    def update(self):
        self.graph.update()

    def clear(self):
        self.graph.clear()

    def show_page(self):
        # get rid of the show button:
        self.show_btn.pack_forget()

        # create a graph object:
        # params: frame, buffer, title, x_label, class_info
        self.graph = GraphPage.FancyGraph(self,
                                          self.buffer,
                                          self.title,
                                          self.x_label,
                                          self.class_info)
        self.update_btn.pack(side=LEFT)
        self.clear_btn.pack(side=LEFT)
        self.hint.pack(side=LEFT)

class MeasurementPage(Frame):
    """
    A measurement page where one can select different Instruments from the
    myinstruments.py module (if an Instrument is added there it will automatically
    show that Instrument as available option in the Checkbuttons widget!)

    The Terminal widget takes care of the storing the data into an file and
    showing the data directly in the measurement page!
    """

    def swap(list, old, new):
        # swaps the old element of a list with the new element:
        index = list.index(old)
        list.remove(old)
        list.insert(index, new)


    # if a measurement of a thread fails multiple times we close the Instrument's
    # connection and open it again!... then starting a new MeasurementThread!
    def error_routine(self, sender, earg):
        """
        If one thread has a problem to get data from an Instrument and calling
        the measure() method of that Instrument multiple times still doesn't work
        we restart the Instruments connection and let all the other threads go
        into idle mode,... then creating a new MeasurementThread with the same
        properties as the old one! We clear all the fifo buffers too because the
        data in them is incomplete and then we can finally let all the threads leave
        the idle mode and the newly created MeasurementThread can be started!

        --> this error routine should work for arbitrary Instruments asuming
        that the measurement has worked in the first place! (connection errors
        can happen from time to time, normally for short measurements they won't
        even occur, one has to be very unlucky... but for longer measurements
        such routine is totally necessary!)
        """
        print("Handle the error from:", sender)
        # the earg (event argument) is a tuple of all parameters the MeasurementThread
        # has got!
        name, interval, count, instrument, noe, fifo, error_routine = earg
        # close the Instrument's connection:
        instrument.close()
        # let all the currently running threads go into idle mode:
        # (this has no effect on the thread which fired the error event
        # since this thread has been stopped already)
        self.threads_lock.acquire()
        for thread in self.threads:
            thread.wait()
        self.threads_lock.release()

        # open the Instrument's connection:
        instrument.open()
        # sender is the Thread object that fired an error_event!
        # and MeasurementPage.threads is a list of all currently running thread objects
        # so we need to swap the old thread object with the new one!
        old = sender
        new = MeasurementThread(name,
                                interval,
                                count,
                                instrument,
                                noe,
                                fifo,
                                error_routine)

        # update the list of currently used thread objects:
        # but do that in synchronized way:
        self.threads_lock.acquire()
        print("Before:", self.threads)
        MeasurementPage.swap(self.threads, old, new)
        print("After:", self.threads)

        # before we start again, clear all the fifo buffers since the values
        # aren't complete:
        print("Clearing the buffered data of all fifos...")
        for fifo in self.fifos:
            fifo.clear_data()

        for thread in self.threads:
            # leave idle mode and go again!
            # (this call has no effect on the newly created threads since
            # the threads are on creation set to the "go" mode)
            thread.go()
        self.threads_lock.release()

        # if the stop button should have been pressed while we were in the error
        # routine we don't need to start the new thread:
        if self.stop_btn_pressed:
            print("Stopp button pressed during error routine, new thread won't be started!")
            return
        # finally start the new MeasurementThread:
        new.start()
        print("Error handled, normal mode of operation restored!")



    # abstract class for a Container object which should have the update method
    # and should be able to create a header with time info about measurement:
    class Container():

        def update(self, msg):
            raise NotImplementedError("No method: update() implemented on", self.__class__.__name__)

        def create_header(self) -> str:
            ftime = time.strftime("%d.%B.%Y - %H:%M:%S", time.localtime())
            return "Starting new measurement at {}".format(ftime)

    # create a terminal class which inherites from tkinter.Text class and
    # from the abstract class Container which is the interface we
    # need to pass an object as a container to the UpdateThread!
    class Terminal(Text, Container):

        def __init__(self, parent, filename, *args, **kwargs):
            Text.__init__(self, parent, *args, **kwargs)
            # filename in which the measured data will be safed:
            self.filename = filename

        def update(self, msg):
            # save msg to file (append data if file already filled with content,
            # or create file if no file with that name exists)
            with open(self.filename, "a+") as f:
                f.write(msg + "\n")
            # show msg in the terminal:
            self.insert(END, msg + "\n")
            # for autoscrolling to the bottom position:
            self.yview_moveto(1)

    # a widget that holds a Checkbutton object for each Instrument class available
    # in the myinstruments module:
    class Checkbuttons(Frame):

        def __init__(self, parent, classes, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.classes = classes
            self.vars = []
            self.cbs = []
            for cls in classes:
                # for each instrument we need an Integer variable:
                self.vars.append(IntVar())
                self.cbs.append(Checkbutton(self, text=cls.__name__, variable=self.vars[-1]))

        # this is used to get all the class objects in a list:
        def get_selected_classes(self) -> list:
            print("Selected buttons:", [var.get() for var in self.vars])
            selection = []
            for cls, var in zip(self.classes, self.vars):
                # a selected button has a variable value of 1, 0 otherwise!
                if var.get():
                    # append class if selected:
                    selection.append(cls)
            # return a list of class objects of the selected classes:
            return selection

        def _packChildren(self):
            # as we created the Checkbutton objects we said that the parent
            # of our Checkbutton is self -> and self is the Checkbuttons object
            # which is itself a tkinter Frame object!
            # when we call pack() on the Checkbutton objects they will get
            # packed inside the Checkbuttons Frame widget:
            for cb in self.cbs:
                cb.pack()

        def pack(self, *args, **kwargs):
            self._packChildren()
            # after we pack the children (Checkbutton objects) we need to
            # pack the Frame the children are inside too:
            # (will be packed inside the parent widget, see constructor parameters)
            Frame.pack(self, *args, **kwargs)

        def grid(self, *args, **kwargs):
            self._packChildren()
            # see pack() method above... same aplies here but using other
            # method to place the Checkbuttons Frame (which holds all the Checkbutton objects)
            # inside the parent widget:
            Frame.grid(self, *args, **kwargs)

        class MyEntryBox(Frame):

            def __init__(self, *args, **kwargs):
                Frame.__init__(self, *args, **kwargs)



    # the filename is used to create an file with that name for data saving or
    # if such file does exist it appends any new data to it!
    def __init__(self, parent, buffer, class_info, filename, *args, **kwargs):

        Frame.__init__(self, parent, *args, **kwargs)
        # this is needed for drawing the right labels acording to the selected
        # Instruments on the MeasurementPage:
        # (a list of all instrument classes we want an object from, this must be
        # an empty list at the beginning)
        assert type(class_info) == list and len(class_info) == 0, "An empty list object excepted!"
        self.classes = class_info

        # the FIFO buffer for exchanging data between the GraphPage and the
        # MeasurementPage:
        self.buffer = buffer

        # a list of measurement instruments, will be appended later:
        self.instruments = []

        # later append the threads for automated measurement in the threads list:
        self.threads = []
        # in the error_routine if 2 threads try to access the self.threads list
        # we need to synchronize this access
        self.threads_lock = multiprocessing.Lock()

        # FIFO(First In First Out) buffers for temporaly storing measured data:
        self.fifos = []

        # reference time at which we started the measurement:
        self.start_time = None
        # for the error routine to signal the stopp button has been pressed meanwhile:
        self.stop_btn_pressed = False

        # get all the available instrument classes of the myinstruments modul:
        all_available_classes = []
        for entry in inspect.getmembers(sys.modules["myinstruments"], inspect.isclass):
            name, cls = entry
            # skip the append class part if it's the abstract base class!
            if name == "Instrument":
                continue
            all_available_classes.append(cls)
        print("All available Instruments are:")
        print(all_available_classes)

        self.checkbuttons = MeasurementPage.Checkbuttons(self, all_available_classes)
        self.checkbuttons.grid(row=2, column=0, columnspan=1, sticky=N+E+S+W)

        self.apply_btn = Button(master=self, text="Apply", command=self.apply)
        self.apply_btn.grid(row=3, column=0, columnspan=1, sticky=E+W)

        # create all measurement widgets:
        self.init_btn = Button(master=self,
                               text="Initialize",
                               command=self.init_measurement,
                               state=DISABLED)
        self.init_btn.grid(row=0, column=0, sticky=E+W)

        self.status_label = Label(self, text="Not initialized", bg="red", fg="white")
        self.status_label.grid(row=0, column=1, sticky=E+W)

        self.measurement_btn = Button(master=self,
                                      text="One shot measurement",
                                      command=self.measurement,
                                      state=DISABLED)
        self.measurement_btn.grid(row=1, column=0)

        self.auto_measure_btn = Button(master=self,
                                       text="Automated measurement",
                                       command=self.atomated_measurement,
                                       state=DISABLED)
        self.auto_measure_btn.grid(row=1, column=1)

        self.scrollbar = Scrollbar(self)
        self.scrollbar.grid(row=2, column=4, sticky=N+S)

        self.terminal = MeasurementPage.Terminal(self,
                                                 filename,
                                                 yscrollcommand=self.scrollbar.set,
                                                 width=80)
        self.terminal.grid(row=2, column=3)
        self.scrollbar.config(command=self.terminal.yview)

        self.stop_btn = Button(master=self,
                               text="Stop measurement",
                               command=self.stop,
                               state=DISABLED)
        self.stop_btn.grid(row=3, column=3, sticky=W)

        self.terminal_label = Label(self, text="Measurement terminal")
        self.terminal_label.grid(row=1, column=3, sticky=N+E+S+W)

    # parameters: doing <count> measurements every <interval> seconds
    # noe ... number of errors that can occur before the error_routine is started
    # fps ... frames per second we want the screen to try to update with new values
    # (see mythreads module for further information)
    def init_measurement(self, interval=15, count=11520, noe=3, fps=2):
        # reset the flag:
        self.stop_btn_pressed = False
        # an empty list is not an valid option:
        if not self.classes:
            messagebox.showinfo("Select Instrument(s)", "Please select at least one Instrument!")
            return
        # in the classes list are all class names of instruments we want to
        # create an object from:
        for cls in self.classes:
            # create objects of instruments using default settings,
            # the initialization of the instruments happens on the __init__ call,
            # and then append the instrument objects to the instruments list:
            self.instruments.append(cls())
            # for each instrument we want to have a FIFO data buffer:
            self.fifos.append(Fifo())
            # and for each instrument we need a MeasurementThread:
            self.threads.append(MeasurementThread(self.instruments[-1].__class__.__name__,
                                                  interval,
                                                  count,
                                                  self.instruments[-1],
                                                  noe,
                                                  self.fifos[-1],
                                                  self.error_routine))

        # create an UpdateThread to update the terminal and the save file
        # with the new measured data:
        self.threads.append(UpdateThread(fps,
                                         self.terminal,
                                         self.fifos,
                                         self.instruments,
                                         self.buffer))

        # update the status of initialization:
        self.status_label.config(text="Finished initialization", bg="green", fg="white")
        # enable all measurement related button:
        self.measurement_btn.config(state=NORMAL)
        self.auto_measure_btn.config(state=NORMAL)
        self.stop_btn.config(state=NORMAL)
        # and disable the initialization button:
        # (will be enabled in stop method when stop button pushed!)
        self.init_btn.config(state=DISABLED)
        # while measuring no need to press apply button to change Instruments:
        # (will be enabled in stop method when stop button pushed!)
        self.apply_btn.config(state=DISABLED)

    def apply(self):
        # clear the Instrument class list:
        self.classes.clear()

        # enable the init_btn:
        self.init_btn.config(state=NORMAL)

        # this classes will be used in the init_measurement method!
        self.classes.extend(self.checkbuttons.get_selected_classes())
        print("Following classes were selected:")
        print(self.classes)


    def atomated_measurement(self):
        # we don't want manualy measured data while doing atomatic measurements:
        self.measurement_btn.config(state=DISABLED)
        # and force the user to not press buttons when it makes no sense:
        self.auto_measure_btn.config(state=DISABLED)
        self.apply_btn.config(state=DISABLED)

        # start the threads which will do the measurement and the update of the
        # terminal and the data saveing file:
        for thread in self.threads:
            thread.start()

    # this is used for doing measurements on each button click!
    def measurement(self):
        try:
            # if it's the first time we measured we need a reference time:
            if self.start_time == None:
                self.start_time = time.time()
                # and we create a header for the new measurement with time info:
                self.terminal.update(self.terminal.create_header())

            # we need to send the measured data to the GraphPage as a bundle:
            bundle = []
            bundle.append(float("%.3f" % (time.time() - self.start_time)))
            # create a message containing all the measurement information:
            msg = "Time: {}, ".format(bundle[-1])
            for instrument in self.instruments:
                bundle.append(instrument.measure())
                msg += "{}: {}, ".format(instrument.__class__.__name__, bundle[-1])

            # save that to the shared FIFO buffer for drawing on the graph
            # (shared between this page and the GraphPage)
            self.buffer.push(bundle)
            print("Data bundle sent to GraphPage:", bundle)

            # show the measured data in the terminal and save it to a file:
            self.terminal.update(msg)
        except Exception as e:
            print(e)

    def stop(self):
        # to ensure it wasn't a missclick:
        answer = messagebox.askquestion("Stop?", "Really want to stop measurement?")
        # if no -> return and do nothing
        if answer == "no":
            return

        # if yes ->
        # to signal the error routine we don't need to start a new thread now:
        self.stop_btn_pressed = True
        # disable measurement and stop measurement button:
        self.measurement_btn.config(state=DISABLED)
        self.auto_measure_btn.config(state=DISABLED)
        self.stop_btn.config(state=DISABLED)
        # and enable the apply button again to select different Instruments:
        self.apply_btn.config(state=NORMAL)
        # clear terminal:
        self.terminal.delete(1.0, END)
        # reset status label:
        self.status_label.config(text="Not initialized", bg="red", fg="white")
        # resest the start time:
        self.start_time = None

        self.threads_lock.acquire()
        # close all threads:
        for thread in self.threads:
            thread.stop()

        # wait till they are really closed (will block GUI meanwhile):
        for thread in self.threads:
            # try block so if we didn't started the threads we will get an
            # error here like: can't join thread which never started
            try:
                thread.join()
            except Exception as e:
                print(e)
        self.threads_lock.release()

        # let the garbage collector destroy the measurement instrument objects,
        # since this was the only reference we have to the instruments by now
        # (MeasurementThreads had references too but the are stopped above,
        # and so is the UpdateThread) if reference count of an object is 0
        # the garbage collector will do it's work:
        self.instruments.clear()
        # the same applies for the other obects, the memory will be freed again:
        # (note: no lock necessary since all threads are stopped and joined!)
        self.fifos.clear()
        self.threads.clear()

        # ask if the data stored in the buffer which sends measurement data to
        # the GraphPage should be cleared:
        answer = messagebox.askquestion("Clear drawing buffer?", "Want to clear the drawing buffer?")
        # if yes -> clear the drawing buffer
        if answer == "yes":
            self.buffer.clear_data()
        # if no -> do nothing
        # then enable initialization button again:
        self.init_btn.config(state=NORMAL)
