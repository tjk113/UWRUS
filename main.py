import requests
import json

from itertools import zip_longest
from time import sleep

from get_records import get_ss_records, get_rta_records, get_creds
from replace_record import replace_record

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

def main():
    SHEETS_CREDS = get_creds()
    # test_page = 'User:Tjk113'
    # test_new_wr = ('0.00', 'https://www.youtube.com/watch?v=9yjZpBq1XBE')
    new_ss_records = get_ss_records(SHEETS_CREDS)
    # new_rta_records = get_rta_records(SHEETS_CREDS)
    new_rta_records = [None]

    if new_ss_records == None:
        print(f'{bcolors.FAIL}Error:{bcolors.ENDC} Failed to retrieve data from single star spreadsheet!')
        return
    if new_rta_records == None:
        print(f'{bcolors.FAIL}Error:{bcolors.ENDC} Failed to retrieve data from RTA spreadsheet!')
        return
    if new_ss_records == [] and new_rta_records == []:
        print('No new single star or RTA records to update...')
        return

    BOT_USER = ''
    BOT_PASS = ''
    API = 'https://ukikipedia.net/mediawiki/api.php'
    SESSION = requests.Session()
    req_params = {
        'action': 'query',
        'meta'  : 'tokens',
        'type'  : 'login',
        'format': 'json'
    }
    print(f'Logging in to "{BOT_USER}"...', end='')
    response = SESSION.get(url=API, params=req_params).json()
    LOGIN_TOKEN = response['query']['tokens']['logintoken']

    sleep(1)

    req_params = {
        'action'    : 'login',
        'lgname'    : BOT_USER,
        'lgpassword': BOT_PASS,
        'lgtoken'   : LOGIN_TOKEN,
        'format'    : 'json'
    }
    response = SESSION.post(API, data=req_params).json()
    if response['login']['result'] == 'Success':
        print(f'{bcolors.OKGREEN}Success{bcolors.ENDC}')
    else:
        print(f'{bcolors.FAIL}Failed{bcolors.ENDC}')
        return
    # assert response['login']['result'] == 'Success'

    # Need to determine which list is longer
    # so we can pull star names from the
    # correct list
    # if len(new_ss_records) > len(new_rta_records):
    #     longest_list = new_ss_records
    # else:
    #     longest_list = new_rta_records

    # Thank you itertools!
    for new_ss_record, new_rta_record in zip_longest(new_ss_records, new_rta_records, fillvalue=None):

        sleep(1)

        new_record_star_name = new_ss_record[2] if new_ss_record != None else new_rta_record[2]

        req_params = {
            'action'       : 'query',
            'meta'         : 'tokens',
            'titles'       : 'RTA Guide/' + new_record_star_name, # star name
            'prop'         : 'revisions',
            'rvslots'      : 'main',
            'rvprop'       : 'content|timestamp',
            'formatversion': 2,
            'curtimestamp' : True,
            'format'       : 'json'
        }
        response = json.loads(SESSION.get(url=API, params=req_params).text)
        page_text = response['query']['pages'][0]['revisions'][0]['slots']['main']['content']
        if not '{{speedrun_infobox' in page_text or '{{speedrun_infobox_bowser_level' in page_text:
            print(f"Couldn't get page content for star '{new_record_star_name}': {bcolors.FAIL}Failed{bcolors.ENDC}")
            continue

        BASE_TIMESTAMP  = response['query']['pages'][0]['revisions'][0]['timestamp']
        START_TIMESTAMP = response['curtimestamp']
        CSRF_TOKEN = response['query']['tokens']['csrftoken']

        page_text, summary = replace_record(page_text, new_ss_record=new_ss_record, new_rta_record=new_rta_record)
        # page_text will be None if the record is
        # already updated (or has a faster time due
        # to me ignoring the extensions sheet for now), 
        # so just skip ahead to the next record in the list
        if page_text == None:
            print(f"{new_record_star_name}'s page is either already updated or has a faster time than was provided. Skipping record...")
            continue

        sleep(1)

        req_params = {
            'action'        : 'edit',
            'title'         : 'RTA Guide/' + new_record_star_name,
            'token'         : CSRF_TOKEN,
            'basetimestamp' : BASE_TIMESTAMP,
            'starttimestamp': START_TIMESTAMP,
            'bot'           : True,
            'text'          : page_text,
            'summary'       : summary,
            'format'        : 'json'
        }
        print(f'Editing page "RTA Guide/{new_record_star_name}"...', end='')
        response = SESSION.post(API, data=req_params).json()
        if response['edit']['result'] == 'Success':
            print(f'{bcolors.OKGREEN}Success{bcolors.ENDC}')
        else:
            print(f'{bcolors.FAIL}Failed{bcolors.ENDC}')
        # assert response['edit']['result'] == 'Success'

if __name__ == '__main__':
    main()