# hardware control protocol imports:
import minimalmodbus
import serial
import visa


# --- abstract class which we want all innstrument classes to inherite ---
class Instrument():
    """Every instrument must inherite from the Instrument class and therefore must
    implement:
    -> the measure method
    -> the open method
    -> the close method
    -> the get_y_label method
    ...or a NotImplementedError is raised if the app will call one of those methods!
    """
    # of cause we want the Instrument to measure something!
    def measure(self) -> float:
        raise NotImplementedError("No method: measure() implemented on", self.__class__.__name__)

    # every Instrument must have some sort of connection to the PC so we
    # need a method for opening and closing this connection!
    def open(self):
        raise NotImplementedError("No method: open() implemented on", self.__class__.__name__)

    def close(self):
        raise NotImplementedError("No method: close() implemented on", self.__class__.__name__)

    # a class method that tells the MeasurementPage
    # whether we can set the port settings in the GUI or not!
    # override this method so that it returns True if port settings make sense
    # for the Instrument
    def has_port_settings():
        return False

    # this is used for labeling the axis(and legend) when plotting the data measured with measure!
    # note: this is a class function!
    def get_labels() -> str:
        raise NotImplementedError("No method: get_labels() implemented!")


# --- custom instruments ---

class Eurotherm2416(minimalmodbus.Instrument, Instrument):

    def __init__(self, port="COM7", baudrate=9600):

        # we will open a serial port inside the minimalmodbus.Instrument __init__
        # with the baudrate constant of the module so we need to set this:
        minimalmodbus.BAUDRATE = baudrate

        print("Starting", self.__class__.__name__, "initialization...")
        # 1 is the slaveadress (1 to 247)
        minimalmodbus.Instrument.__init__(self, port, 1)

        # check the instrument properties, this will
        # call __repr__ of minimalmodbus.Instrument:
        print(self)
        print("Finished", self.__class__.__name__, "initialization...")

    def has_port_settings():
        return True

    def open(self):
        print("Opening connection of:", self.__class__.__name__, "again...")
        # in minimalmodbus.Instrument.__init__(self, port, 1) we create a Serial object:
        # self.serial = serial.Serial(port=port, baudrate=BAUDRATE, parity=PARITY,
        # bytesize=BYTESIZE, stopbits=STOPBITS, timeout=TIMEOUT)
        # so let's open this connection here again:
        self.serial.open()
        if self.serial.is_open:
            print("Connection of instrument:", self.__class__.__name__, " has been opened!")
        else:
            raise IOError("Failed to open connection of instrument:", self.__class__.__name__)

    def close(self):
        print("Closing connection of:", self.__class__.__name__)
        self.serial.close()
        if not self.serial.is_open:
            print("Connection of instrument:", self.__class__.__name__, " has been closed!")
        else:
            raise IOError("Failed to close connection of instrument:", self.__class__.__name__)

    def measure(self) -> float:
        # arguments of read_register() method:
        # > register address we want to read from
        # > number of decimals
        # --> see docs:
        # If a value of 77.0 is stored internally in the slave register as 770,
        # then use numberOfDecimals=1 which will divide the received data
        # by 10 before returning the value
        temp = self.read_register(289, 1)
        print(self.__class__.__name__, "response:", temp)
        return temp

    def get_labels() -> str:
        # the first is for the axis label, the second for the legend label:
        return ("Temperature in °C", "Temperature")


class FMI220(Instrument):
    """ Most common commands:
    AD ... actual value mode
    AG ... units in N
    AA ... set current force value to null point
    BA ... one shot force measurement
    """
    def __init__(self, port="COM6", baudrate=9600, timeout=0.5):

        self.serial = serial.Serial(port=port,
                                    baudrate=baudrate,
                                    timeout=timeout,
                                    bytesize=serial.EIGHTBITS,
                                    parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE)

        print("Starting FMI220 initialization...")
        # check instrument properties by calling __repr__ implicitly:
        print(self)
        # for further information see most command command list above
        self.query("AD")
        self.query("AG")
        self.query("AA")
        print("Finished FMI220 initialization...")

    def has_port_settings():
        return True

    def open(self):
        print("Opening connection of:", self.__class__.__name__, "again...")
        self.serial.open()
        if self.serial.is_open:
            print("Connection of instrument:", self.__class__.__name__, " has been opened!")
        else:
            raise IOError("Failed to open connection of instrument:", self.__class__.__name__)

    def close(self):
        print("Closing connection of:", self.__class__.__name__)
        self.serial.close()
        if not self.serial.is_open:
            print("Connection of instrument:", self.__class__.__name__, " has been closed!")
        else:
            raise IOError("Failed to close connection of instrument:", self.__class__.__name__)

    def __repr__(self):
        # string representaion of FMI220 object:
        return "{}.{}<id=0x{:x}, serial={}>".format(self.__module__, self.__class__.__name__, id(self), self.serial)

    def query(self, command) -> str:
        # clear buffer of eventual remaining content:
        self.serial.reset_input_buffer()
        # write command to instrument:
        bytes_writen = self.serial.write((command+"\r").encode("ascii"))
        # wait till all data is written:
        self.serial.flush()
        if command=="BA":
            # one shot measurement:
            msg = self.serial.read(size=12).decode("ascii").replace("\r","")[4:]
        else:
            # change settings:
            msg = self.serial.read(size=3).decode("ascii")
            print("FMI220 query response:", msg)
        return msg

    def measure(self) -> float:
            force = float(self.query("BA"))
            print("FMI220 response:", force)
            return force

    def get_labels() -> str:
        return ("Force in N", "Force")

class Keithley2000(Instrument):
    # TODO: implement voltage measurement
    RESISTANCE = 0
    VOLTAGE = 1

    # choose what you want to measure by the corresponding function code:
    # (note: the function code has to match the function code in the get_labels method!)
    def __init__(self, function=0):
        self.n = 0

        # self.gpib will be a obect of: pyvisa.resources.Resource
        # with the open and close method of that resource we can open and close
        # a session!
        self.gpib = None
        self.function = function
        print("Starting Keithley2000 initialization...")
        self.open_gpib_connection()

        if self.function == Keithley2000.RESISTANCE:
            init_code = ["*rst; status:preset; *cls;",
                         "configure:fresistance",
                         "fresistance:range:auto ON",
                         "sense:fresistance:nplcycles 0.01"]
        elif self.function == Keithley2000.VOLTAGE:
            init_code = []
            raise NotImplementedError("Voltage measurement not implemented yet!")
        else:
            raise ValueError("Function number not supported!")

        print("Keithley2000 info:", self.gpib.query('*IDN?'))
        print("Initialize Keithley2000 with code:")
        print(init_code)

        for command in init_code:
            self.gpib.write(command)

        print("Check measurement properties on Keithley2000:")
        if self.function == Keithley2000.RESISTANCE:
            print("Range auto:", self.gpib.query("fresistance:range:auto?"))
            print("Cycles:", self.gpib.query("fresistance:nplcycles?"))
        elif self.function == Keithley2000.VOLTAGE:
            pass

        print("Finished Keithley2000 initialization...")

    def open_gpib_connection(self):
        rm = visa.ResourceManager()
        resource_list = rm.list_resources()

        for resource in resource_list:
            if "GPIB" in resource:
                print("Trying to open gpib connection...", resource)
                self.gpib = rm.open_resource(resource)

        if self.gpib == None:
            raise RuntimeError("No gpib connection found!")

    def open(self):
        print("Opening connection of:", self.__class__.__name__, "again...")
        self.gpib.open()
        print("Connection of instrument:", self.__class__.__name__, " has been opened!")
        print(self.gpib.resource_info)


    def close(self):
        print("Closing connection of:", self.__class__.__name__)
        self.gpib.close()
        print("Connection of instrument:", self.__class__.__name__, " has been closed!")

    def measure(self) -> float:
        if self.function == Keithley2000.RESISTANCE:
            response = float(self.gpib.query("read?")[:-1])
        elif self.function == Keithley2000.VOLTAGE:
            pass

        print("Keithley2000 response:", response)
        return response

    # a function to get the string label which should be used for plotting data
    # measured from this instrument:
    # (note: the function code has to match the function code in the init method!)
    def get_labels(function=0) -> str:
        if function == Keithley2000.RESISTANCE:
            return ("Resistance in OHM", "Resistance")
        elif function == Keithley2000.VOLTAGE:
            return ("Voltage in V", "Voltage")
