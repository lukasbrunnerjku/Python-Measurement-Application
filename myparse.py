# --- parse a measurement file ---

def file_to_csv_lines(filename, header=True):
    """Takes a filename as argument and yield it's lines
    in csv style with/without header!
    optional argument: header=True (default) or header=False
    """
    with open(filename, "r") as file:
        if header:
            header_str = file.readline()
            is_first = True
            # slicing a list: start, stop, step!
            for label in file.readline().split(" ")[::2][:-1]:
                # get rid of the comma:
                label = label[:-1]
                if is_first:
                    header_str += label
                    is_first = False
                else:
                    header_str += ", " + label

            # yield the optional first line of the parsed file
            yield header_str


        is_first_line = True
        # File objects are iterable and yield lines until EOF
        for line in file:
            # skip the first line, because it only contains the
            # information about the start date and time of a measurement:
            if is_first_line:
                is_first_line = False
                continue
            is_first_entry = True
            parsed_line = ""
            # build the parsed_line:
            for entry in line.split(",")[:-1]:
                # (the last entry is newline character \n therefore [:-1])
                if is_first_entry:
                    parsed_line += entry.split(" ")[1]
                    is_first_entry = False
                else:
                    parsed_line += "," + entry.split(" ")[2]
            # yield all the other lines for the parsed file
            yield parsed_line

def file_to_csv(in_filename, out_filename, **kwargs):
    """Takes a measurement data filename and the filename the parsed file
    should have... optional parameter: header=True/False as keyword argument!
    """
    with open(out_filename, "w+") as file:
        # for further information on yield see: python generator
        for parsed_line in file_to_csv_lines(in_filename, **kwargs):
            file.write(parsed_line + "\n")

def copy_file(in_filename, out_filename):
    """Copies the content of one file into the other
    """
    in_file = open(in_filename, "r")
    out_file = open(out_filename, "w+")
    for line in in_file:
        out_file.write(line)
    in_file.close()
    out_file.close()

if __name__ == '__main__':
    out_filename = "ParsedFileAsCSV2.txt"
    in_filename = "SaveFileDataSet.txt"
    # parse a file and save that in an other file:
    file_to_csv(in_filename, out_filename, header=False)
