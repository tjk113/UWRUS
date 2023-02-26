class bcolors:
    '''Used for output coloring'''
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def prefix_print(str: str, end: str = '\n') -> None:
    '''
    Prints provided string with a '[UWRUS]: ' prefix
    '''
    print(f'[{bcolors.OKCYAN}UWRUS{bcolors.ENDC}]: {str}', end=end)

def remove_mins_place(record: str) -> float:
    '''
    Converts records longer than 1 minute 
    from a X:XX.XX format to a XX.XX format
    '''
    record_list = record.split(':')
    # Cast the array elements to floats
    record_list = [float(i) for i in record_list]
    # Convert the minutes place (record_list[0])
    # into seconds, and add that 
    # to the existing seconds place
    return record_list[0]*60 + record_list[1]