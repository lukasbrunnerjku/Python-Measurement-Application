# --- module for general utility functions ---
import os

def swap(list, old, new):
    """Swaps the old element of a list with the new element"""
    index = list.index(old)
    list.remove(old)
    list.insert(index, new)

def open_hadware_manager():
    """Opens the hardware manager under windows!"""
    os.system("devmgmt.msc")

def delete_empty_dict_entries(dictionary) -> dict:
    """Takes a dictionary as input parameter and deletes all empty entries
    from that dictionary, then returns it"""
    assert type(dictionary) == dict, "Argument must be of type dictionary!"
    invalid_keys = []
    for key, value in dictionary.items():
        # if a entry was left empty we want to use the default values, so
        # mark such entries as invalid
        if value == "":
            invalid_keys.append(key)

    # delete invalid entries from dictionary:
    for key in invalid_keys:
        del dictionary[key]
    print("Empty entries got deleted, new dictionary:", dictionary)
    return dictionary

if __name__ == '__main__':
    # this works:
    settings = {"Interval": "1000", "Count": "", "Number of errors": "", "Fps": "2"}
    settings = delete_empty_dict_entries(settings)
    # raises AssertionError: Argument must be of type dictionary!
    settings = delete_empty_dict_entries([1, 2])
