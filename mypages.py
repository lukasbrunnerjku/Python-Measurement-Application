# --- module for custom pages ---

# general imports:
from tkinter import *
from mywidgets import *

# for general utility functions:
from myutils import *

# for the measurement page:
import multiprocessing
from tkinter import messagebox
from myinstruments import *
from mythreads import *
# for retrieving all the classes of the myinstruments module:
import sys, inspect


class GraphPage(Frame):
    """
    A GraphPage which supports up to 3 y-Axes that share the same x-Axis (Time)
    using the FancyGraph widget!
    """
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
                          text="After changing the Instruments press clear once before update, it will reset the graph accordingly!",
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
        self.graph = FancyGraph(self,
                                self.buffer,
                                self.title,
                                self.x_label,
                                self.class_info)
        self.update_btn.pack(side=LEFT)
        self.clear_btn.pack(side=LEFT)
        self.hint.pack(side=LEFT)

class MeasurementPage(Frame):
    """A measurement page where one can select different Instruments from the
    myinstruments.py module (if an Instrument is added there it will automatically
    show that Instrument as available option in the Checkbuttons widget!)

    The Terminal widget takes care of the storing the data into an file and
    showing the data directly in the measurement page!
    """
    def error_routine(self, sender, earg):
        """If a measurement of a thread fails multiple times we close the Instrument's
        connection and open it again!... then starting a new MeasurementThread!

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
        swap(self.threads, old, new)
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


    def __init__(self, parent, buffer, class_info, filename, *args, **kwargs):
        """The filename is used to create an file for data saving or
        if such file does exist it appends any new data to it!
        The buffer and class_info is used for communication between the
        MeasurementPage and the GraphPage!
        """
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

        measurement_labels = ["Interval", "Count", "Number of errors", "Fps"]
        self.settingsbox1 = SettingsBox(self, measurement_labels, "Settings for the threads:")
        self.settingsbox1.grid(row=2, column=1, columnspan=1, sticky=N+E+S+W)

        # get the labels for all Instruments who have implemented the set_port method!
        # for this Instruments it is possible to have different port names on different
        # hardware, so we are able to set these parameters easly in the GUI
        connection_labels = []
        for cls in all_available_classes:
            if cls.has_port_settings():
                connection_labels.append(cls.__name__ + " port")

        self.settingsbox2 = SettingsBox(self, connection_labels, "Settings of Instrument ports:")
        self.settingsbox2.grid(row=3, column=1, columnspan=1, sticky=N+E+S+W)

        self.checkbuttons = Checkbuttons(self, all_available_classes, bg="dark khaki")
        self.checkbuttons.grid(row=2, column=0, columnspan=1, rowspan=2, sticky=N+E+S+W)

        self.apply_btn = Button(master=self, text="Apply", command=self.apply)
        self.apply_btn.grid(row=4, column=0, columnspan=1, sticky=E+W)

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
        self.auto_measure_btn.grid(row=1, column=1, sticky=E+W)

        self.scrollbar = Scrollbar(self)
        self.scrollbar.grid(row=2, column=4, rowspan=2, sticky=N+S)

        self.terminal = Terminal(self,
                                 filename,
                                 yscrollcommand=self.scrollbar.set,
                                 width=80)
        self.terminal.grid(row=2, column=3, rowspan=2)
        self.scrollbar.config(command=self.terminal.yview)

        self.stop_btn = Button(master=self,
                               text="Stop measurement",
                               command=self.stop,
                               state=DISABLED)
        self.stop_btn.grid(row=4, column=3, sticky=W)

        self.port_btn = Button(master=self,
                               text="Open hadware manager under windows",
                               command=open_hadware_manager,
                               bg="saddle brown",
                               fg="white")
        self.port_btn.grid(row=4, column=1, sticky=W+E)

        self.terminal_label = Label(self, text="Measurement terminal")
        self.terminal_label.grid(row=1, column=3, sticky=N+E+S+W)

    def init_measurement(self, interval=15, count=11520, noe=3, fps=2):
        """Parameters: doing <count> measurements every <interval> seconds
        noe ... number of errors that can occur before the error_routine is started
        fps ... frames per second we want the screen to try to update with new values
        (see mythreads module for further information)
        """
        # reset the flag:
        # (to signal the error routine if we need to start a new thread or not)
        self.stop_btn_pressed = False
        # an empty list is not an valid option:
        if not self.classes:
            messagebox.showerror("No Instrument selected",
                                 "Please select at least one Instrument!")
            return

        # settings is a dictionary like:
        # note: "Count" has an empty entry, we will handle that case too
        # {"Interval": "1000", "Count": "", "Number of errors": "1", "Fps": "2"}
        settings = self.settingsbox1.get_settings()

        # if no settings were applied than use default settings
        if settings != None:
            settings = delete_empty_dict_entries(settings)

            # use the values from method arguments above as default values if
            # there is no dictionary entry with the given key
            try:
                interval = float(settings.get("Interval", interval))
                count = float(settings.get("Count", count))
                noe = int(settings.get("Number of errors", noe))
                fps = int(settings.get("Fps", fps))
            except Exception as e:
                messagebox.showerror("Couldn't set the thread settings!",
                                     "Error message:\n{}".format(e))
                return

        # in any case (thread settings set in GUI or not -> use default ones) show
        # what thread settings will be used:
        print("--- thread settings ---")
        print("Interval:", interval,
              "Count:", count,
              "Number of errors:", noe,
              "Fps:", fps)

        # now settings is a dict with the port names as values and
        # keys like: Eurotherm2416 port -> Instrument name in key!
        # note: here we can have empty entries too, but we will handle that
        settings = self.settingsbox2.get_settings()
        # if no settings were applied than use default port settings of the
        # Instrument's __init__ methods! but if there is a settings dictionary
        # then delete the empty entries:
        if settings != None:
            settings = delete_empty_dict_entries(settings)

        # in the classes list are all class names of instruments we want to
        # create an object from:
        for cls in self.classes:
            # create objects of instruments using settings from the settingsbox2,
            # the initialization of the instruments happens on the __init__ call
            try:
                # use default port settings if the dictionary hasn't the
                # given key in it (that's the case if the entry was left empty):
                if cls.has_port_settings() and settings != None:
                    temp = cls(port=settings.get(cls.__name__ + " port", None))
                else:
                    # this is used for Instrument classes where it makes no sense
                    # to use port settings, e.g. the Keithley2000 is connected over
                    # GPIB and it is the only Instrument with GPIB so it simply searches
                    # for an Ni Visa resource with GPIB in it
                    temp = cls()
            except Exception as e:
                hint = ("Hint: If a resource is blocked press the stop measurement" +
                " button to free the resource and then go for the initialization again!" +
                " That's the case if a PermissionError is raised!")
                messagebox.showerror("Instrument initialization error!",
                                     "Error message:\n{}\n\n{}".format(e, hint))
                # if an Instrument will raise an error here may there are other
                # Instruments which were successfully created and the connection
                # established, so in such case we want to enable the stop button
                # then we can easily fix the original problem and press the stop
                # measurement button to free all resources and then we can go
                # for a new initialization!
                self.stop_btn.config(state=NORMAL)
                return

            # and then append the instrument objects to the instruments list:
            self.instruments.append(temp)
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
        """Uses the current Instrument selection for upcomming initialization!"""
        # clear the Instrument class list:
        self.classes.clear()

        # enable the init_btn:
        self.init_btn.config(state=NORMAL)

        # this classes will be used in the init_measurement method!
        self.classes.extend(self.checkbuttons.get_selected_classes())
        print("Following classes were selected:")
        print(self.classes)


    def atomated_measurement(self):
        """This method is used for doing measurements on certain timings and
        for a certain number of times

        --> on such measurement the error routine will get called if the
        Instrument still can't measure successfully after multiple tries!
        """
        # we don't want manualy measured data while doing atomatic measurements:
        self.measurement_btn.config(state=DISABLED)
        # and force the user to not press buttons when it makes no sense:
        self.auto_measure_btn.config(state=DISABLED)
        self.apply_btn.config(state=DISABLED)

        # start the threads which will do the measurement and the update of the
        # terminal and the data saveing file:
        for thread in self.threads:
            thread.start()

    def measurement(self):
        """This method is used for doing measurements on each button click!

        --> here no error routine is used, just restart manually!
        """
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
        """Stops the automated measurement manually and clears the Terminal screen,
        asks if the data shown in the Terminal (which hasn't been plotted yet) will
        be used for plotting --> if not the clear this "drawing buffer"

        note: No data saved in the files will be deleted of course!
        """
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

class ParsingPage(Frame):
    """A Page containing a ParsingBox widget for converting and saving a
    measurement data files having the comfort of a GUI to select files, it
    also contains an example image of how the output will be formatted!
    """
    def __init__(self, parent, *args, **kwargs):

        Frame.__init__(self, parent, *args, **kwargs)
        self.parsingbox = ParsingBox(self)
        self.parsingbox.grid(row=0, column=0)
