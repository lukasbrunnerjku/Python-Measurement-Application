from tkinter import *
from tkinter import ttk
from mypages import *
from mythreads import *


# create tabed window with custom pages:
root = Tk()
root.wm_title("TextileUX Measurement")
# width x height + x offset + y offset
# note for offset: (0,0) is upper left corner of our screen
root.geometry("1000x600+300+50")

notebook = ttk.Notebook(root)

# we need to get data from the MeasurementPage to the GraphPage,
# and therefore we use the Fifo class which implements synchronized
# data access(needed when working with threads):
buffer = Fifo()

# for sending information of selected Instruments to the GraphPage:
class_info = []

# --- create custom pages ---
#
# this is the filename of the file we want to save the measured data in:
filename = "SaveFile.txt"
measurement = MeasurementPage(notebook, buffer, class_info, filename, bg="grey")
# change the graph title here:
title = "28 nodes, overall resistance(all parallel) over temperature"
graph = GraphPage(notebook, buffer, class_info, title, bg="grey")

notebook.add(measurement, text="measurement")
notebook.add(graph, text="graph")

notebook.pack(expand=True, fill="both")

root.mainloop()
