import os.path
import re

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from ast import literal_eval

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

TEST_SS_SHEET = '1mVSI74yhPZqOHm-2U-GkNeg1Dwck8tcdsmN_-niQeeI' # test sheet
TEST_SS_SHEET_2 = '1OOqBAHO6HDvB2BIz5ljHNZgnqey7w_eg71z1jifNplE' # test sheet w/ "new" wrs
# SS_SHEET = '1_cOIEnuKIQ-3LA_U0ygpiL87PTSBPlHmKDId0vC7alo'
SS_RANGE = 'Singlestar!B:E'

RTA_SHEET = '1MLCoRkzXvQwPCnJsQL6NJRfkIStPnYjjiRPPX5vu8is'
RTA_RANGE = 'Ultimate Star Spreadsheet v2!A:B'

record_parse = re.compile(r'=HYPERLINK\("(?P<link>.+)?";"(?P<time>.+)"\)')

def get_creds() -> Credentials:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def remove_mins_place(record: str):
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

def parse_values(values: list[str]) -> list[tuple[str, str, str]]:
    '''
    Parses raw spreadsheet values, formats each star's
    information (time, link, name) into tuples, and returns
    a list containing said tuples
    '''
    records = []
    IGT_TEXT = ''
    last_star_name = ''
    for i in range(len(values)):
        try:
            # Check if next row is an IGT record.
            # If so, then skip ahead to that
            cur_is_igt = values[i][0] == '' and values[i][2] == '---'
            rt_igt_tied = False
            # If the next_is_igt check fails with an IndexError,
            # then the next row is a separator row, and we should
            # disregard this IndexError so that we don't skip over
            # the last star row of each stage
            next_is_igt = None
            try:
                next_is_igt = values[i+1][0] == '' and values[i+1][2] == '---'
            except IndexError:
                next_is_separator = True

            if cur_is_igt and next_is_igt:
                continue
            if next_is_igt:
                # Prioritize first real-time record if there are
                # tied IGT record(s) or tied real-time record(s)
                cur_igt = values[i][3].replace('"', '.').replace("'", ':')
                next_igt = record_parse.search(values[i+1][3]).group('time') \
                           .replace('""', '.').replace("'", ':')
                if ':' in cur_igt:
                    cur_igt = remove_mins_place(cur_igt)
                if ':' in next_igt:
                    next_igt = remove_mins_place(next_igt)

                if float(cur_igt) == float(next_igt):
                    rt_igt_tied = True
                else:
                    IGT_TEXT = ' (IGT)'
                    continue
            if not next_is_igt or rt_igt_tied or next_is_separator:
                res = record_parse.search(values[i][2])
            if cur_is_igt and not rt_igt_tied:
                res = record_parse.search(values[i][3])

            time = res.group('time').replace('""', '.').replace("'", ':')
            link = res.group('link')

            # Check if star name is already in records
            if link not in [i[1] for i in records]:
                # If the star name is blank and it's an IGT record,
                # then use the star name from the previous row
                star_name = values[i][0] if values[i][0] else values[i-1][0]
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

def get_ss_records(creds: Credentials) -> tuple[str, str, str]:
    '''
    Gets new Single Star WRs from spreadsheet and creates
    a list of tuples that hold the new times, links, and
    star names
    '''
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=TEST_SS_SHEET_2,
                 range=SS_RANGE, valueRenderOption='FORMULA').execute()
        values = result.get('values', [])

        if not values:
            print('No data found in sheet #2.')
            return

        # Read locally stored records
        local_records = []
        with open('last_saved_ss.txt', 'r') as file:
            for line in file:
                local_records.append(literal_eval(line.strip('\n')))
        # Parse records pulled from spreadsheet
        cur_records = parse_values(values)

        # Write current records to local file
        with open('last_saved_ss.txt', 'w+') as file:
            for record in cur_records:
                file.write(str(record)+'\n')

    except HttpError as err:
        print(err)

    # Remove everything from records except the new wrs
    for record, record_2 in zip(local_records, cur_records):
        temp_time = record[0]
        temp_time_2 = record_2[0]

        if 'IGT' in record[0]:
            temp_time = record[0][:-6]
        if 'IGT' in record_2[0]:
            temp_time_2 = record_2[0][:-6]

        if ":" in record[0]:
            temp_time = remove_mins_place(temp_time)
        if ":" in record_2[0]:
            temp_time_2 = remove_mins_place(temp_time_2)

        if record == record_2:
            del record
            del record_2
        # If the new wr is faster or if there's a
        # new video link, then update the record
        elif float(temp_time) > float(temp_time_2) or str(temp_time)[1] != str(temp_time_2)[1]:
            records = record_2
    return records

def get_rta_records(creds: Credentials) -> tuple[str, str, str]:
    '''
    Gets new RTA WRs from spreadsheet and creates
    a list of tuples that hold the new times, links, and
    row labels
    '''
    try:
        service = build('sheets', 'v4', credentials=creds)
        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=RTA_SHEET,
                 range=RTA_RANGE, valueRenderOption='UNFORMATTED_VALUE').execute()
        # result_2 = sheet.values().get(spreadsheetId=SS_SHEET_2,
        #          range=RTA_RANGE, valueRenderOption='FORMULA').execute()
        values = result.get('values', [])
        # values_2 = result_2.get('values', [])

        if not values:
            print('No data found in sheet #1.')
            return
        # if not values_2:
        #     print('No data found in sheet #2.')
        #     return

        # records = parse_values(values)
        # records_2 = parse_values(values_2)

        print(values)

    except HttpError as err:
        print(err)

# Test Driver Code
if __name__ == '__main__':
    CREDS = get_creds()
    get_ss_records(CREDS)