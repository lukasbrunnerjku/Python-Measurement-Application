from tkinter import *
from tkinter import ttk
from mypages import *
from mythreads import *


# create tabed window with custom pages:
root = Tk()
root.wm_title("TextileUX Measurement")
# width x height + x offset + y offset
# note for offset: (0,0) is upper left corner of our screen
root.geometry("1200x600+300+50")

notebook = ttk.Notebook(root)

# we need to get data from the MeasurementPage to the GraphPage,
# and therefore we use the Fifo class which implements synchronized
# data access(needed when working with threads), the Fifo uses a deque
# in the background, last "maxlen" elements are saved for plotting:
buffer = Fifo(maxlen=1000)

# for sending information of selected Instruments to the GraphPage:
class_info = []

# --- create custom pages ---
measurement = MeasurementPage(notebook, buffer, class_info, bg="snow3")
# change the graph title here:
title = "Measurement Plot"
graph = GraphPage(notebook, buffer, class_info, title, bg="snow3")
# here we can parse a file to different formats:
parsing = ParsingPage(notebook, bg="snow3")

notebook.add(measurement, text="measurement")
notebook.add(graph, text="graph")
notebook.add(parsing, text="parsing")

notebook.pack(expand=True, fill="both")

root.mainloop()
