# --- parse a measurement file ---


# Note: file_to_csv is a Generator not a regular function!...
#
# takes a filename as argument and yield it's content
# in csv style with/without header!
# optional argument: header=True (default) or header=False
def file_to_csv_lines(filename, header=True):
    with open(filename, "r") as file:
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

        # set file pointer to the start of the file again:
        file.seek(0)

        if header:
            # yield the optional first line of the parsed file
            yield header_str

        # File objects are iterable and yield lines until EOF
        for line in file:
            is_first = True
            parsed_line = ""
            # build the parsed_line:
            for entry in line.split(",")[:-1]:
                # (the last entry is newline character \n therefore [:-1])
                if is_first:
                    parsed_line += entry.split(" ")[1]
                    is_first = False
                else:
                    parsed_line += "," + entry.split(" ")[2]
            # yield all the other lines for the parsed file
            yield parsed_line


# takes a string in csv style and convert it to a list of float values:
def csv_line_to_values(line):
    return [float(value) for value in line.split(",")]


if __name__ == '__main__':
    #filename = input("Name of file(with extension): ")
    out_filename = "ParsedFileAsCSV.txt"
    with open(out_filename, "w+") as file:
        # for further information on yield see: python generator
        in_filename = "SaveFile.txt"
        for parsed_line in file_to_csv_lines(in_filename):
            file.write(parsed_line + "\n")
