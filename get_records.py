import os.path
import re

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

SS_SHEET = '1mVSI74yhPZqOHm-2U-GkNeg1Dwck8tcdsmN_-niQeeI' # test sheet
SS_SHEET_2 = '1OCmqfE_kTYVaFoZLsXmjtawKyEAIUZOOVZwakLuH25I' # test sheet w/ "new" wrs
RANGE = 'Singlestar!B:E'

record_parse = re.compile(r'=HYPERLINK\("(?P<link>.+)";"(?P<time>.+)"\)')

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
    for i in range(len(values)):
        try:
            # Check if next row is an IGT record.
            # If so, then skip ahead to that
            cur_is_igt = values[i][0] == '' and values[i][2] == '---'
            next_is_igt = values[i+1][0] == '' and values[i+1][2] == '---'
            rt_igt_tied = False

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
            if not next_is_igt or rt_igt_tied:
                res = record_parse.search(values[i][2])
            if cur_is_igt and not rt_igt_tied:
                res = record_parse.search(values[i][3])

            record = res.group('time').replace('""', '.').replace("'", ':')

            # Check if time is already in records
            if record not in [i[0] for i in records]:
                records.append((record + IGT_TEXT, res.group('link'), values[i][0]))
                IGT_TEXT = ''
        # If not a time, skip over the row
        except IndexError:
            continue
        except AttributeError:
            pass
    return records


def get_ss_records() -> tuple[str, str, str]:
    '''
    Gets new WRs from (spreadsheet/discord) and creates
    a list of tuples that hold the new times, links, and
    star names
    '''
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

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = sheet_2 = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SS_SHEET,
                 range=RANGE, valueRenderOption='FORMULA').execute()
        result_2 = sheet.values().get(spreadsheetId=SS_SHEET_2,
                 range=RANGE, valueRenderOption='FORMULA').execute()
        values = result.get('values', [])
        values_2 = result_2.get('values', [])

        if not values:
            print('No data found in sheet #1.')
            return
        if not values_2:
            print('No data found in sheet #2.')
            return

        records = parse_values(values)
        records_2 = parse_values(values_2)

    except HttpError as err:
        print(err)

    # remove everything from records except the new wrs
    for record, record_2 in zip(records, records_2):
        temp_time = record[0]
        temp_time_2 = record_2[0]

        if 'IGT' in record[0]:
            temp_time = record[0][:-6]
        if 'IGT' in record_2[0]:
            temp_time_2 = record_2[0][:-6]

        if ':' in record[0]:
            temp_time = remove_mins_place(temp_time)
        if ':' in record_2[0]:
            temp_time_2 = remove_mins_place(temp_time_2)

        if record == record_2:
            del record
            del record_2
        # if the new wr is faster or if there's a new video link
        elif float(temp_time) > float(temp_time_2) or temp_time[1] != temp_time_2[1]:
            records = record_2

    print(records, '\n')
    return records

if __name__ == '__main__':
    get_ss_records()