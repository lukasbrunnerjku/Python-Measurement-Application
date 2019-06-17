# --- module for custom widgets ---

import os
import PIL
from PIL import ImageTk
import tkinter
from tkinter import *
import json
from tkinter import messagebox
from tkinter import filedialog
from myparse import *

# for the Graph:
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib import style
style.use("ggplot")
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)

# to create the time information for the header in the Container widget:
import time


class Graph():
    """An abstract Graph class for all custom Graph classes to inherite from!"""
    def update(self):
        raise NotImplementedError("No method: update() implemented on", self.__class__.__name__)

    def clear(self):
        raise NotImplementedError("No method: clear() implemented on", self.__class__.__name__)


class FancyGraph(Graph):
    """A fancy graph, 3 different colors and markers are used for better visual
    distinguishability. It is designed for a maximum of 3 y-Axes to preserve
    readability -> AssertionError is raised if at any point the attempt would
    be made to create a 4 or more axes graph by selecting 4 or more Instrument
    classes for example!
    """
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
        # raises an AssertionError if there are more than 3 Instruments selected
        assert len(class_info) <= 3, "A maximum of 3 axes at once are supported!"

        for cls in self.class_info:
            y_label, y_legend_label = cls.get_labels()
            self.y_labels.append(y_label)
            self.y_legend_labels.append(y_legend_label)


class Container():
    """Abstract class for a Container object which should have the update method
    and should be able to create a header with time info about measurement
    """
    def update(self, msg):
        raise NotImplementedError("No method: update() implemented on", self.__class__.__name__)

    def create_header(self) -> str:
        ftime = time.strftime("%d.%B.%Y - %H:%M:%S", time.localtime())
        return "Starting new measurement at {}".format(ftime)


class Terminal(Text, Container):
    """Create a terminal class which inherites from tkinter.Text class and
    from the abstract class Container which is the interface we
    need to pass an object as a container to the UpdateThread!
    """
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


class Checkbuttons(Frame):
    """A widget that holds a Checkbutton object for each Instrument class available
    in the myinstruments module
    """
    def __init__(self, parent, classes, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.classes = classes
        self.vars = []
        self.cbs = []
        for cls in classes:
            # for each instrument we need an Integer variable:
            self.vars.append(IntVar())
            self.cbs.append(Checkbutton(self, text=cls.__name__, variable=self.vars[-1], **kwargs))

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


class SettingsBox(Frame):
    """A Frame for editing settings where every entry is labeled,
    the settings are saved as a dictionary where the label is the key and
    the value of the entry is the dictionary's value!
    """
    def __init__(self, parent, labels, info, *args, **kwargs):

        Frame.__init__(self, parent, *args, **kwargs)
        self._settings = None
        self._path = None

        # --- define label colors here ---
        entry_bg_color = "salmon1"
        entry_fg_color = "black"
        header_bg_color = "yellow"
        header_fg_color = "blue"
        # --------------------------------

        # a label which gives a hint what the settings are used for!
        label = Label(self,text=info, bg=header_bg_color, fg=header_fg_color)
        label.grid(row=0, column=0, columnspan=3, sticky=N+E+S+W)

        next_free_row_index, self.widgets = self.create_widgets(labels,
                                                                1,
                                                                bg=entry_bg_color,
                                                                fg=entry_fg_color)

        self.apply_btn = Button(self, text="Apply", command=self.apply)
        self.apply_btn.grid(row=next_free_row_index, column=0, sticky=N+E+S+W)
        self.save_btn = Button(self, text="Save", command=self.save)
        self.save_btn.grid(row=next_free_row_index, column=1, sticky=N+E+S+W)
        self.load_btn = Button(self, text="Load", command=self.load)
        self.load_btn.grid(row=next_free_row_index, column=2, sticky=N+E+S+W)

    def get_settings(self) -> dict:
        """Returns a copy of the dictionary where the currently applied
        settings are saved! There is no constant keyword so we return a
        copy to be sure the current _settings object won't be manipulated!
        If there were no settings applied then the _settings variable points to
        a None object and None will be returned!
        """
        if self._settings == None:
            return None
        else:
            return dict(self._settings)

    def create_widgets(self, labels, index, **lkwargs):
        """Creates setting widgets with given labels and at the given
        start row position (=index)
        Returns the next free row index and the widget list!
        """
        widgets = []
        for label in labels:
            widgets.append(Label(self, text=label, **lkwargs))
            widgets.append(Entry(self))

        for i, widget in enumerate(widgets):
            widget.grid(row = index,
                        column=i%2,
                        columnspan=2 if i%2==1 else 1,
                        sticky=N+E+S+W)
            if i%2 == 1:
                index += 1
        return index, widgets

    def get_in_filename(self, path):
        # note: file has to have extension!
        return filedialog.askopenfilename(initialdir=path,
                                          title="Select setting file you want to open",
                                          filetypes=(("text files","*.txt"),("all files","*.*")))

    def get_out_filename(self, path):
        # note: file has to have extension!
        return filedialog.asksaveasfilename(initialdir=path,
                                            title="Select setting file location you want to save the current settings",
                                            filetypes=(("text files","*.txt"),("all files","*.*")))

    def get_current_directory_path(self):
        self._path = os.path.dirname(os.path.abspath( __file__ ))
        print("Current directory:", self._path)

    def _fetch(self) -> dict:
        """Returns a dictionary with the text labels as keys and the entry values
        as values!
        """
        return {self.widgets[i].cget("text"):self.widgets[i+1].get() for i in range(0, len(self.widgets), 2)}

    def apply(self):
        """Applies the current settings to be used in the application we can use
        this instead of save() if we don't wan't to save the current settings to
        a file!
        """
        self._settings = self._fetch()
        print("SettingsBox._settings = {}".format(self._settings))

    def save(self):
        """Save the dictionary with the settings to the file with the given
        filename using JSON(Java Script Notation Objects)
        """
        self.apply()

        if self._path == None:
            self.get_current_directory_path()
        filename = self.get_out_filename(self._path)

        with open(filename, "w+") as f:
            try:
                f.write(json.dumps(self._settings))
            except Exception as e:
                print("Couldn't save settings to file!")
                print(e)

    def load(self):
        """Load the dictionary with the settings from the file with the given
        filename using JSON(Java Script Notation Objects)
        """
        answer = messagebox.askquestion("Confirm loading operation",
                                        "Unsaved settings will be lost!\nReally want to load settings?")
        # return with no changes made:
        if answer == "no":
            return

        if self._path == None:
            self.get_current_directory_path()
        filename = self.get_in_filename(self._path)

        try:
            with open(filename, "r") as f:
                json_str = f.read()
                self._settings = json.loads(json_str)
                print("SettingsBox._settings = {}".format(self._settings))

        except Exception as e:
            print("Couldn't load settings from file!")
            print(e)

        try:
            i = 0
            for key, value in self._settings.items():
                self.widgets[i].config(text=key)
                self.widgets[i+1].delete(0, END)
                self.widgets[i+1].insert(0, value)
                i += 2

        except Exception as e:
            print("Couldn't set widgets accordingly!")
            print(e)


class PreviewBox(Frame):
        """Given a list of image filename strings the PreviewBox uses them
        to load the images
        """
        def __init__(self, parent, selected, *args, **kwargs):

            Frame.__init__(self, parent, *args, **kwargs)
            self.image = None
            # IntVar to save last pressed button selection code:
            self.selected = selected
            # Canvas needed to show an Image:
            self.canvas = Canvas(self)
            self.canvas.grid(row=0, column=0, columnspan=3, sticky="nesw")
            # a list of all button widgets:
            self.buttons = []
            # buttons to switch between previews:
            self.my_format_btn = Button(self,
                                        text="My format",
                                        command=lambda: self.show_image("my_format.png", 0))
            self.my_format_btn.grid(row=1, column=0, sticky="ew")
            self.buttons.append(self.my_format_btn)

            # get the standard background color of a button:
            self.default_bg_color = self.my_format_btn.cget("bg")
            # set the color for button selected:
            self.selection_bg_color = "green"
            # the my_format_btn should be the default selection:
            self.my_format_btn.config(bg=self.selection_bg_color)

            self.csv_wo_header_btn = Button(self,
                                            text="CSV without header",
                                            command=lambda: self.show_image("csv_wo_header.png", 1))
            self.csv_wo_header_btn.grid(row=1, column=1, sticky="ew")
            self.buttons.append(self.csv_wo_header_btn)
            self.csv_w_header_btn = Button(self,
                                           text="CSV with header",
                                           command=lambda: self.show_image("csv_w_header.png", 2))
            self.csv_w_header_btn.grid(row=1, column=2, sticky="ew")
            self.buttons.append(self.csv_w_header_btn)

            # default view of the PreviewBox:
            self.show_image("my_format.png", 0)

        def show_image(self, image, selection):
            # set the IntVar:
            self.selected.set(selection)
            # reset all button colors:
            for button in self.buttons:
                button.config(bg=self.default_bg_color)
            # change color of the button to green indicating it's the last one pressed:
            if selection == 0:
                self.my_format_btn.config(bg=self.selection_bg_color)
            elif selection == 1:
                self.csv_wo_header_btn.config(bg=self.selection_bg_color)
            elif selection == 2:
                self.csv_w_header_btn.config(bg=self.selection_bg_color)
            # get the image in a format tkinter can handle it:
            self.image = ImageTk.PhotoImage(PIL.Image.open(image))
            # resize the canvas to be as large as the image:
            self.canvas.config(width=self.image.width(), height=self.image.height())
            self.canvas.create_image(0, 0, image=self.image, anchor="nw")
            self.canvas.image = self.image


class ParsingBox(Frame):
    """A Frame for parsing a selected measurement file from the system explorer,
    (this is in my own format I used for logging the measured data)
    --> this Frame contains a preview of the parsed output for the currently
    selected output format using my PreviewBox class!
    """
    def __init__(self, parent, *args, **kwargs):

        Frame.__init__(self, parent, *args, **kwargs)
        # IntVar to save last pressed button selection code of PreviewBox:
        self.selected = IntVar()
        self.previewbox = PreviewBox(self, self.selected)
        self.previewbox.grid(row=0, column=0, columnspan=3)
        self.convert_btn = Button(self,
                           text="Convert measurement data file",
                           command=self.convert,
                           bg="orange")
        self.convert_btn.grid(row=1, column=0, columnspan=3, sticky="ew")

    def get_in_filename(self, path):
        # note: file has to have extension!
        return filedialog.askopenfilename(initialdir=path,
                                          title="Select measurement file",
                                          filetypes=(("text files","*.txt"),("all files","*.*")))

    def get_out_filename(self, path):
        # note: file has to have extension!
        return filedialog.asksaveasfilename(initialdir=path,
                                            title="Select parsed file location",
                                            filetypes=(("text files","*.txt"),("all files","*.*")))

    def convert(self):
        print("Option choosen:", self.selected.get())
        path = os.path.dirname(os.path.abspath( __file__ ))
        print("Current directory:", path)
        in_filename = self.get_in_filename(path)
        print("Filename for input:", in_filename)
        out_filename = self.get_out_filename(path)
        print("Filename for output:", out_filename)
        # just make a copy of the original file:
        if self.selected.get() == 0:
            copy_file(in_filename, out_filename)
        # parse as CSV without header:
        elif self.selected.get() == 1:
            file_to_csv(in_filename, out_filename, header=False)
        # parse as CSV with header:
        elif self.selected.get() == 2:
            file_to_csv(in_filename, out_filename, header=True)
