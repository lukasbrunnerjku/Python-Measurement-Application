# Python-Measurement-Application
 
Quick introduction and go through of my code:
The main file of the programm is "measurement_app.py", by executing this my measurement programm
starts! In here we create the tab-window structure and add our custom pages to it.
The root.mainloop() command will start the Graphical User Interface(=GUI), the start page
is the MeasurementPage where one can select the Instruments used for measuring by clicking
on the checkboxes and the apply button below. 

To have an responsive GUI I used threads, one thread for each Instrument selected(I called them 
MeasurementThreads) and one for updating the screen with the measured Instrument values(called
UpdateThread). A MeasurementThread uses an Instrument object and calls it's measure() method
to get the current Instrument's value(e.g 0.56 from the Fmi, force measuring instrument). Sometimes 
there can happen connection errors between an instrument and the pc, the MeasurementThread will take
care of such events in the following way:
-> try "noe"(number of errors) times to call the measure() method of the Instrument object
...in case that wouldn't lead to an successful measurement either we will
-> fire an error event that will start the given error routine 
...this will call the close() method of the Instrument object, then all MeasurementThreads are 
paused and the Instrument object will restart the connection with the open() method! A new 
MeasurementThread will be created, which will take the place of the old one. All the paused threads
will be unpaused again and the newly created one will be started!
This procedure will always work* although being quite primitive(equivalent of the good old
unplug then plug in again method :D).
*note: will always work if the implementation of the open and close method of the Instrument works,
I created a simple test programm for the Instruments to verify that called "test_instruments.py"

The last thing to mention is that the measured values are pushed onto a buffer and that's 
enough to know about the MearuementThreads. The next step is to use that buffered values and 
therefore we need the UpdateThread which will:
-> pop the values from the buffer(pop = read and remove)
-> all the measured values plus the time info will be used to form a data bundle 
-> the data bundle is sent to the GraphPage which is used for plotting the data using a 
custom Graph object
-> all measured data is used to populate the Terminal on the MeasurementPage with information
like: which time which instrument has measured which value(as text)
-> the same information shown in the Terminal will be automatically save in a textfile called: SaveFile.txt

In the GraphPage we can, using a FancyGraph object, plot up to 3 different Instument data over
time in the same plot. If the FancyGraph doesn't meet your requirements just write a Graph class
of your own which should implement the methods from the abstract class Graph. This new Graph class 
should then be instantiated(=create an object of that class) in the GraphPage like I did it with
the FancyGraph class! -> This modular 
