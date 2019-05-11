import os
import tkinter
from tkinter import *
import json
from tkinter import messagebox

root = Tk()
root.geometry("500x500+100+100")

class SettingsBox(Frame):
    """A Frame for editing settings where every entry is labeled,
    the settings are saved as a dictionary where the label is the key and
    the value of the entry is the dictionary's value!
    """
    def __init__(self, parent, labels, *args, **kwargs):

        Frame.__init__(self, parent, *args, **kwargs)
        self._settings = None

        next_free_row_index, self.widgets = self.create_widgets(labels)

        Label(self, text="Save as:").grid(row=next_free_row_index,
                                          column=0,
                                          sticky=N+E+S+W)
        self.entry = Entry(self)
        self.entry.insert(0, "example.txt")
        self.entry.grid(row=next_free_row_index, column=1, sticky=N+E+S+W)

        self.apply_btn = Button(self, text="Apply", command=self.apply)
        self.apply_btn.grid(row=next_free_row_index, column=2)
        self.save_btn = Button(self, text="Save", command=self.save)
        self.save_btn.grid(row=next_free_row_index, column=3)
        self.load_btn = Button(self, text="Load", command=self.load)
        self.load_btn.grid(row=next_free_row_index, column=4)

    def create_widgets(self, labels):
        """Creates setting widgets and returns the next free row index and
        the widgets list!
        """
        widgets = []
        for label in labels:
            widgets.append(Label(self, text=label))
            widgets.append(Entry(self))
        index = 0
        for i, widget in enumerate(widgets):
            widget.grid(row = index, column=i%2, sticky=N+E+S+W)
            if i%2 == 1:
                index += 1
        return index, widgets

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
        filename = self.entry.get()
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
        filename = self.entry.get()
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
        def __init__(self, parent, labels, *args, **kwargs):

            Frame.__init__(self, parent, *args, **kwargs)


class ParsingBox(Frame):
    """A Frame for parsing a selected measurement file from the system explorer,
    (this is in my own format I used for logging the measured data)
    --> this Frame contains a preview of the parsed output for the currently
    selected output format using my PreviewBox class!
    """
    def __init__(self, parent, labels, *args, **kwargs):

        Frame.__init__(self, parent, *args, **kwargs)

labels = [
"Interval",
"Count",
"Number of errors",
"Fps",
]
sb = SettingsBox(root, labels)
sb.pack()

images = [
"my_format.png"
"csv_wo_header.png",
"csv_w_header.png"
]
pb = ParsingBox(root, images)

root.mainloop()
