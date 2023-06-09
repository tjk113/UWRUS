import json
import os
import re

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from ast import literal_eval

from common import prefix_print, remove_mins_place, bcolors

# Google Sheets API access scope (should be readonly)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Single Star Spreadsheet ID and column range
SS_SHEET = '1_cOIEnuKIQ-3LA_U0ygpiL87PTSBPlHmKDId0vC7alo'
SS_RANGE = 'Singlestar!B:E'
# RTA Spreadsheet ID and column range
RTA_SHEET = '1J20aivGnvLlAuyRIMMclIFUmrkHXUzgcDmYa31gdtCI'
RTA_RANGE = ['Ultimate Star Spreadsheet v2!A:B']

# Current records lists to be saved
RTA_RECORDS_TO_SAVE = SS_RECORDS_TO_SAVE = []
# Records not to save (because they encountered
# some error in the main script)
RTA_RECORDS_NOT_TO_SAVE = SS_RECORDS_NOT_TO_SAVE = []

# Note: it'd be nice to use named tuples, but given that literal_eval
# can't parse user-defined types, the extra code required to make them
# work with the local record files isn't worth the effort, especially 
# considering the relatively small section of code that could actually
# be rewritten with them.

def get_creds() -> Credentials:
    '''
    Retrieve Google Sheets API Credentials, or renew
    them if necessary
    '''
    global SCOPES
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('.\\sheets_api\\token.json'):
        creds = Credentials.from_authorized_user_file('.\\sheets_api\\token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        prefix_print('Updating Google Sheets API credentials...', end='')
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '.\\sheets_api\\credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('.\\sheets_api\\token.json', 'w') as token:
            token.write(creds.to_json())
        print(f'{bcolors.OKGREEN}Success{bcolors.ENDC}')
    return creds

def get_new_records(local_records: list[tuple[str, str, str]], \
                    cur_records:   list[tuple[str, str, str]]) \
                    -> list[tuple[str, str, str]]:
    '''
    Return only the new records as compared
    to the current local records list
    '''
    # Remove everything from local_records except the new records
    # (Iterate over copies of lists so that we can delete items
    # from the actual lists while iterating)
    local_records_cpy = local_records.copy()
    cur_records_cpy = cur_records.copy()
    for local_record, cur_record in zip(local_records_cpy, cur_records_cpy):
        local_time = local_record[0]
        cur_time = cur_record[0]

        if 'IGT' in local_record[0]:
            local_time = local_record[0][:-6]
        if 'IGT' in cur_record[0]:
            cur_time = cur_record[0][:-6]

        if ":" in local_record[0]:
            local_time = remove_mins_place(local_time)
        if ":" in cur_record[0]:
            cur_time = remove_mins_place(cur_time)

        # If the wr is unchanged or the wr pulled from the sheet
        # is slower than the local wr, then remove the record
        if local_record == cur_record or float(cur_time) > float(local_time):
            local_records.remove(local_record)
            cur_records.remove(cur_record)
        # If there's a new video link, then update the record
        elif local_record[1] != cur_record[1]:
            # There should never ever be special case
            # handling in this function! That being said...
            if local_record[2] == 'RR 100 Coins':
                local_records.remove(local_record)
                cur_records.remove(cur_record)
                continue
            cur_records[cur_records.index(cur_record)] = (local_record[0], cur_record[1], local_record[2])
    return cur_records

def parse_ss_values(values: list[str]) -> list[tuple[str, str, str]]:
    '''
    Parses raw single star spreadsheet values, formats each
    star's information (time, link, name) into tuples, and
    returns a list containing said tuples
    '''
    record_parse = re.compile(r'=HYPERLINK\("(?P<link>.+)?";"(?P<time>.+)"\)')
    records = []
    IGT_TEXT = ''
    last_star_name = ''
    for i in range(len(values)):
        try:
            cur_is_igt = values[i][1] == 'Best IGT' and values[i][2] == '---'
            rt_igt_tied = False

            # Check if next row is an IGT record.
            # If so, then skip ahead to that
            has_igt = False
            j = 0
            try:
                # Emulating a do while loop (the loop can
                # go to the end of the current stage)
                while values[i+j]:
                    # This assumes every record has a real-time run... probably safe
                    if values[i+j][1] == 'Best IGT' and values[i+j][2] == '---' and j != 0:
                        has_igt = True
                        break
                    if values[i+j+1][0]:
                        break
                    j += 1
            # If the next_is_igt check fails with an IndexError,
            # then the next row is a separator row, and we should
            # disregard this IndexError so that we don't skip over
            # the last star row of each stage
            except IndexError:
                next_is_separator = True

            if cur_is_igt and has_igt:
                continue
            if has_igt:
                # Prioritize first real-time record if there are
                # tied IGT record(s) or tied real-time record(s)
                cur_igt = values[i][3].replace('"', '.').replace("'", ':')
                # Pretty much just to handle Snowman's Lost His Head
                # (and maybe In the Deep Freeze)
                try:
                    next_igt = record_parse.search(values[i+j][3]).group('time') \
                               .replace('""', '.').replace("'", ':')
                except AttributeError:
                    next_igt = values[i+1j][3].replace('"', '.').replace("'", ':')

                if ':' in cur_igt:
                    cur_igt = remove_mins_place(cur_igt)
                if ':' in next_igt:
                    next_igt = remove_mins_place(next_igt)

                if float(cur_igt) == float(next_igt):
                    rt_igt_tied = True
                else:
                    IGT_TEXT = ' (IGT)'
                    continue
            if not has_igt or rt_igt_tied or next_is_separator:
                res = record_parse.search(values[i][2])
            if cur_is_igt and not rt_igt_tied:
                res = record_parse.search(values[i][3])

            time = res.group('time').replace('""', '.').replace("'", ':')
            link = res.group('link')

            # Check if video link is already in records
            if link not in [i[1] for i in records]:
                if values[i][0]:
                    star_name = values[i][0]
                else:
                    # Iterate back up the list
                    # until we find the star name
                    # (This is for stars that have
                    # multiple tied real-time records
                    # and/or IGT records)
                    j = 1
                    while not values[i-j][0]:
                        j += 1
                    star_name = values[i-j][0]

                if star_name and star_name != last_star_name:
                    records.append((time + IGT_TEXT, link, star_name))
                last_star_name = star_name
                IGT_TEXT = ''
        # If not a time, skip over the row
        except IndexError:
            continue
        except AttributeError:
            pass
    return records

def get_ss_records(creds: Credentials = None) -> list[tuple[str, str, str]]:
    '''
    Gets new Single Star WRs from spreadsheet and creates
    a list of tuples that hold the new times, links, and
    star names
    '''
    global SS_SHEET, SS_RANGE, SS_RECORDS_TO_SAVE, SS_RECORDS_NOT_TO_SAVE
    try:
        if creds:
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            # For each row in the specified column range, get the cell formula
            result = sheet.values().get(spreadsheetId=SS_SHEET,
                     range=SS_RANGE, valueRenderOption='FORMULA').execute()
            values = result.get('values', [])

            if not values:
                print('No data found in sheet')
                return

        # Read locally stored records
        local_records = []
        with open('.\\local_records\\last_saved_ss.txt', 'r') as file:
            for line in file:
                local_records.append(literal_eval(line.strip('\n')))
        if creds:
            # Parse records pulled from spreadsheet
            cur_records = parse_ss_values(values)
        elif creds == 'DEBUG':
            # For Debug / Testing
            cur_records = []
            with open('.\\test_pages\\test_ss_raw.txt', 'r') as file:
                for line in file:
                    cur_records.append(line)
            cur_records = parse_ss_values(cur_records)
        else:
            return

        # Save records if it's the first time running
        # or if the file somehow gets deleted
        if not os.path.exists('.\\local_records\\last_saved_ss.txt'):
            save_ss_records()

    except HttpError as err:
        prefix_print(f'{bcolors.FAIL}Google Sheets API Error:{bcolors.ENDC} {err}')
        return

    new_records = get_new_records(local_records, cur_records)
    # Set RECORDS_TO_SAVE, and
    # reset RECORDS_NOT_TO_SAVE
    SS_RECORDS_TO_SAVE = cur_records.copy()
    SS_RECORDS_NOT_TO_SAVE = []
    return new_records

def set_ss_record_not_to_save(record: tuple[str, str, str]) -> None:
    '''
    Mark a single star record not to be saved to local file
    '''
    global SS_RECORDS_NOT_TO_SAVE
    SS_RECORDS_NOT_TO_SAVE.append(record)

def save_ss_records() -> None:
    '''
    Write current single star records to local file
    (minus records set not to save)
    '''
    global SS_RECORDS_TO_SAVE, SS_RECORDS_NOT_TO_SAVE
    if SS_RECORDS_TO_SAVE:
        records_to_save = [i for i in SS_RECORDS_TO_SAVE if i not in SS_RECORDS_NOT_TO_SAVE]
        local_records = []
        with open('.\\local_records\\last_saved_ss.txt', 'w+') as file:
            # Load local records into list
            for line in file:
                local_records.append(literal_eval(line.strip('\n')))
            # "Find and replace" local records with new records
            for i, local_record in enumerate(local_records):
                for new_record in records_to_save:
                    if new_record[2] == local_record[2]:
                        local_records[i] = new_record
            # Write updated local records to file
            file.seek(0)
            for record in records_to_save:
                file.write(str(record)+'\n')

def parse_rta_values(values: dict) -> list[tuple[str, str, str]]:
    '''
    Parses raw RTA spreadsheet values, formats each
    star's information (time, link, name) into tuples, and
    returns a list containing said tuples
    '''
    row_label_parse = re.compile(r'\[(?P<strategy_index>\d)\]')
    records = []

    prev_row = (f"{float('inf')}", '', '') # placeholder values
    cur_star_name = ''
    cur_star_strategy_count = 0
    prev_strategy_index = '0'
    best_star_time = float('inf') # placeholder value
    # Interating over rows in spreadsheet
    for i in values['sheets'][0]['data'][0]['rowData']:
        # If there is a time in the row...
        if i and len(i['values']) > 1:
            # And a link...
            if 'hyperlink' in i['values'][1]:
                is_bold = 'userEnteredFormat' in i['values'][0]
                # After all the strategies for the previous star
                # have been iterated over and the fastest has been
                # set as cur_row (which prev_row is set to), append
                # the row to records and reset cur_star_strategy_count
                if is_bold and cur_star_strategy_count >= 1:
                    records.append(prev_row)
                    cur_star_strategy_count = 0
                
                row_label = i['values'][0]['effectiveValue']['stringValue']
                # Skip over Stage RTA rows
                if 'RTA' in row_label:
                    continue

                # The number in the brackets at the start of a row label
                strategy_index = row_label_parse.search(row_label)
                # If the regex returned None, the row format
                # was likely [x|x], some variation of that,
                # or a blank row
                if strategy_index == None:
                    # Special case handling for Bowser stage red coin
                    # stars, where we do actually want to parse
                    # the [x|x]-indexed x-cam records...
                    if 'Bowser' in cur_star_name and 'Red Coins' in cur_star_name:
                        strategy_index = '3'
                    else:
                        continue
                else:
                    strategy_index = strategy_index.group('strategy_index')

                # Skip over non-full-star rows (still allows
                # for cases where there may only be one
                # strategy for a row, meaning there will be
                # two consecutive rows labels starting with [1])
                if strategy_index == prev_strategy_index and not is_bold:
                    continue

                # Make sure the star name being stored in the
                # final record tuple will be the actual star's
                # name, and not a strategy name
                if strategy_index == '1':
                    cur_star_name = row_label

                # Update best strategy time for the current star if
                # a faster time is parsed, or if this is the first
                # iteration
                time = i['values'][1]['effectiveValue']['stringValue']
                if ':' in time:
                    time_f = remove_mins_place(time)
                else:
                    time_f = float(time)
                if time_f < best_star_time or cur_star_strategy_count == 0:
                    cur_row = ((time, i['values'][1]['hyperlink'], cur_star_name))
                    best_star_time = time_f

                prev_strategy_index = strategy_index
                prev_row = cur_row
                cur_star_strategy_count += 1
        # Don't track castle movement rows (idk why the logic has to be weird like this)
        elif i and 'effectiveValue' in i['values'][0]:
            if i['values'][0]['effectiveValue']['stringValue'] == '17. Castle (Lobby)':
                break

    for i in range(len(records)-6): # -6 because we are going to remove 6 entries
        # Remove the [1] from the star name
        cur_star_name = records[i][2][4:]

        # Special case handling (worst design of all time award)...
        if cur_star_name == 'Big Penguin Race + 100c (JP)':
            records.remove(records[i])
        elif cur_star_name == 'Race + 100c atmpas special route (JP)':
            cur_star_name = 'Big Penguin Race + 100c (JP)'
        elif '(No log firsty)' in cur_star_name:
            cur_star_name = cur_star_name[:-16]
        elif cur_star_name == 'Go on a Ghost Hunt (US)' \
             or cur_star_name == 'Reds + 100c Pond spindrift early (JP)' \
             or cur_star_name == "Scary 'Shrooms, Red Coins + 100c (JP)" \
             or cur_star_name == 'Reds + 100c 5 coins pole route (JP)':
            records.remove(records[i])
            # Removing a record essentially increments
            # i by 1, so we have to reset cur_star_name
            cur_star_name = records[i][2][4:]
        if cur_star_name == 'Reds + 100c Spawn red star late route (JP)':
            cur_star_name = "Scary 'Shrooms, Red Coins + 100c (JP)"
        elif cur_star_name == 'Reds + 100c 11 coins route (JP)':
            # Doing this again because reasons...
            records.remove(records[i])
            cur_star_name = records[i][2][4:]
        
        # Plunder in the Sunken Ship special case handling...
        if cur_star_name == 'Plunder in the Sunken Ship (Normal ending)':
            cur_star_name = cur_star_name.replace(' (Normal ending)', '')

        # Remove 'JP' or 'US' from star name
        if 'JP' in cur_star_name or 'US' in cur_star_name:
            # Special case handling...
            if cur_star_name[:11] == 'BitS Battle':
                cur_star_name = cur_star_name[:-20]
            else:
                cur_star_name = cur_star_name[:-5]

        # Doing this here so that the names of the RTA and 
        # single star sheet row labels are the same for
        # Bowser course records, which makes life easier
        # in the main script when parsing record names
        if 'Course' in cur_star_name:
            cur_star_name = cur_star_name.replace('(', '').replace(')', '')

        # Converting from spreadsheet 100 coin naming scheme
        # to Ukiki 100 coin naming scheme
        if '100c' in cur_star_name:
            match(cur_star_name):
                case 'Find the 8 Red Coins + 100c':
                    cur_star_name = 'BoB 100 Coins'
                case 'Red Coins on the Floating Isle + 100c':
                    cur_star_name = 'WF 100 Coins'
                case 'Red Coins on the Ship Afloat + 100c':
                    cur_star_name = 'JRB 100 Coins'
                case "Slip Slidin' Away + 100c" | 'Big Penguin Race + 100c':
                    cur_star_name = 'CCM 100 Coins'
                case 'Seek the 8 Red Coins + 100c':
                    cur_star_name = 'BBH 100 Coins'
                case 'Elevate for 8 Red Coins + 100c':
                    cur_star_name = 'HMC 100 Coins'
                case 'Hot-Foot-It into the Volcano + 100c':
                    cur_star_name = 'LLL 100 Coins'
                case 'Pyramid Puzzle + 100c':
                    cur_star_name = 'SSL 100 Coins'
                case 'Pole-Jumping for Red Coins + 100c':
                    cur_star_name = 'DDD 100 Coins'
                case "Shell Shreddin' for Red Coins + 100c":
                    cur_star_name = 'SL 100 Coins'
                case 'Secrets in the Shallows & Sky + 100c' | 'Go to Town for Red Coins + 100c':
                    cur_star_name = 'WDW 100 Coins'
                case "Scary 'Shrooms, Red Coins + 100c":
                    cur_star_name = 'TTM 100 Coins'
                case "Wiggler's Red Coins + 100c":
                    cur_star_name = 'THI 100 Coins'
                case 'Stomp on the Thwomp + 100c':
                    cur_star_name = 'TTC 100 Coins'
                case 'The Big House in the Sky + 100c':
                    cur_star_name = 'RR 100 Coins'

        # If cur_star_name is already in records, append a 1 and a 2 to the
        # end of the tuples of the respective records (this is to distinguish
        # between multi-strategy 100c stars)
        for j, record in enumerate(records):
            # Special case handling...
            if record[2] == cur_star_name and cur_star_name != 'Through the Jet Stream':
                records[j] = (record[0], record[1], record[2], 1)
        if cur_star_name in [j[2] for j in records] and cur_star_name != 'Through the Jet Stream':
            parsed_record = (records[i][0], records[i][1], cur_star_name, 2)
        else:
            parsed_record = (records[i][0], records[i][1], cur_star_name)
        records[i] = parsed_record

    return records

def get_rta_records(creds: Credentials = None) -> list[tuple[str, str, str]]:
    '''
    Gets new RTA WRs from spreadsheet and creates
    a list of tuples that hold the new times, links, and
    row labels
    '''
    global RTA_SHEET, RTA_RANGE, RTA_RECORDS_TO_SAVE, RTA_RECORDS_NOT_TO_SAVE
    try:
        # TODO: have to get extensions sheet data as well...
        # otherwise faster times that exist on there will
        # never be updated unless someone updates it
        # manually, which the avoidance of is the whole
        # purpose of this program...
        # the algorithm for syncing the extensions sheet
        # rows with the main sheet's rows can't just look
        # at star names either, because some rows are just
        # named by strategy, with no mention of star name :|

        if creds:
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            # For each row in the specified column range, get the following attributes: (boldness, hyperlink, displayed text)
            result = sheet.get(spreadsheetId=RTA_SHEET,
                     ranges=RTA_RANGE,
                     fields='sheets/data/rowData/values(userEnteredFormat/textFormat/bold,hyperlink,effectiveValue/stringValue)').execute() # monstrosity

            if not result:
                print('No data found in sheet')
                return

        # Read locally stored records
        local_records = []
        with open('.\\local_records\\last_saved_rta.txt', 'r') as file:
            for line in file:
                local_records.append(literal_eval(line.strip('\n')))
        if creds:
            # Parse records pulled from spreadsheet
            cur_records = parse_rta_values(result)
        elif creds == 'DEBUG':
            # For Debug / Testing
            json_test_wrs = {}
            with open('.\\test_pages\\j2.json', 'r') as file:
                json_test_wrs = json.load(file)
                cur_records = parse_rta_values(json_test_wrs)
        else:
            return

        # Save records if it's the first time running
        # or if the file somehow gets deleted
        if not os.path.exists('.\\local_records\\last_saved_rta.txt'):
            save_rta_records()

    except HttpError as err:
        prefix_print(f'{bcolors.FAIL}Google Sheets API Error:{bcolors.ENDC} {err}')
        return

    new_records = get_new_records(local_records, cur_records)
    # Set RECORDS_TO_SAVE, and
    # reset RECORDS_NOT_TO_SAVE
    RTA_RECORDS_TO_SAVE = cur_records.copy()
    RTA_RECORDS_NOT_TO_SAVE = []
    return new_records

def set_rta_record_not_to_save(record: tuple[str, str, str]) -> None:
    '''
    Mark an RTA record not to be saved to local file
    '''
    global RTA_RECORDS_NOT_TO_SAVE
    RTA_RECORDS_NOT_TO_SAVE.append(record)

def save_rta_records() -> None:
    '''
    Write current RTA records to local file
    (minus records set not to save)
    '''
    global RTA_RECORDS_TO_SAVE, RTA_RECORDS_NOT_TO_SAVE
    if RTA_RECORDS_TO_SAVE:
        records_to_save = [i for i in RTA_RECORDS_TO_SAVE if i not in RTA_RECORDS_NOT_TO_SAVE]
        local_records = []
        with open('.\\local_records\\last_saved_rta.txt', 'r+') as file:
            # Load local records into list
            for line in file:
                local_records.append(literal_eval(line.strip('\n')))
            # "Find and replace" local records with new records
            for i, local_record in enumerate(local_records):
                for new_record in records_to_save:
                    if new_record[2] == local_record[2]:
                        local_records[i] = new_record
            # Write updated local records to file
            file.seek(0)
            for record in local_records:
                file.write(str(record)+'\n')

# Test Driver Code
if __name__ == '__main__':
    CREDS = get_creds()
    new_records = get_rta_records(CREDS)
    save_rta_records()
    # print('New records:')
    # for record in new_records:
    #     print(record)
    # new_records = get_ss_records(CREDS)
    # save_ss_records()
    # print('New records:')
    # for record in new_records:
    #     print(record)