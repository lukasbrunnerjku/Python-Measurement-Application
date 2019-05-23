# --- module for testing instrument classes ---

from myinstruments import *
import time

def test(instr_cls):
    # initialize the instrument:
    instr = instr_cls()

    # measure 3 times:
    for _ in range(0, 3):
        time.sleep(0.5)
        print(instr.measure())

    # close connection:
    instr.close()

    # open connenction again:
    instr.open()

    # measure 3 times:
    for _ in range(0, 3):
        time.sleep(0.5)
        print(instr.measure())

    # close connenction again:
    instr.close()

if __name__ == '__main__':
    test(Eurotherm2416) # check!
    test(Keithley2000) # check!
    test(FMI220) # check!
