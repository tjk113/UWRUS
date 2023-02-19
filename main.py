import requests
import json

from itertools import zip_longest
from time import sleep

from replace_record import replace_record, replace_record_bowser, replace_record_multi_100c
from get_records import get_ss_records, get_rta_records, get_creds
from log import Log

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
    log = Log()
    SHEETS_CREDS = get_creds()
    # test_page = 'User:Tjk113'
    # test_new_wr = ('0.00', 'https://www.youtube.com/watch?v=9yjZpBq1XBE')
    new_rta_records = get_rta_records(SHEETS_CREDS)
    new_ss_records = get_ss_records(SHEETS_CREDS)

    if new_rta_records == None:
        msg = 'Failed to retrieve data from RTA spreadsheet!'
        log.add_error_message(msg)
        log.out()
        print(f'{bcolors.FAIL}Error:{bcolors.ENDC} {msg}')
        return
    if new_ss_records == None:
        msg = 'Failed to retrieve data from single star spreadsheet!'
        log.add_error_message(msg)
        log.out()
        print(f'{bcolors.FAIL}Error:{bcolors.ENDC} {msg}')
        return
    if new_ss_records == [] and new_rta_records == []:
        log.set_nothing_to_update(True)
        log.out()
        print('No new single star or RTA records to update...')
        return
    if new_ss_records == []:
        print('No new single star records to update...')
    if new_rta_records == []:
        print('No new RTA records to update...')

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
        log.set_error_message(f'Failed to login to {BOT_USER}!')
        log.out()
        print(f'{bcolors.FAIL}Failed{bcolors.ENDC}')
        return

    # Thank you itertools!
    for new_rta_record, new_ss_record in zip_longest(new_rta_records, new_ss_records, fillvalue=None):

        sleep(1)

        new_record_star_name = new_rta_record[2] if new_rta_record != None else new_ss_record[2]
        is_bowser_course_record = False
        is_bowser_reds_record = False
        is_first_100c_record = False
        is_second_multi_100c_record = False

        if new_record_star_name[:6] == 'Bowser':
            if 'Course' in new_record_star_name:
                new_record_star_name = new_record_star_name[:-9]
                is_bowser_course_record = True
            else:
                new_record_star_name = new_record_star_name[:-10]
                is_bowser_reds_record = True
        elif '100' in new_record_star_name:
            if 2 not in [i for i in new_rta_record]:
                is_first_100c_record = True
            else:
                is_second_multi_100c_record = True

        req_params = {
            'action'       : 'query',
            'meta'         : 'tokens',
            'titles'       : 'RTA Guide/' + new_record_star_name, # page name
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
            msg = f"Couldn't get page content for star '{new_record_star_name}'"
            log.add_update_result(msg)
            print(f"{msg}: {bcolors.FAIL}Failed{bcolors.ENDC}")
            continue

        BASE_TIMESTAMP  = response['query']['pages'][0]['revisions'][0]['timestamp']
        START_TIMESTAMP = response['curtimestamp']
        CSRF_TOKEN = response['query']['tokens']['csrftoken']

        # Bowser stage records handling...
        if is_bowser_course_record:
            page_text, summary = replace_record_bowser(page_text, new_rta_course_record=new_rta_record, new_ss_course_record=new_ss_record)
        elif is_bowser_reds_record:
            page_text, summary = replace_record_bowser(page_text, new_rta_reds_record=new_rta_record, new_ss_reds_record=new_ss_record)
        # Multi-strategy 100c records handling...
        elif is_first_100c_record:
            page_text, summary = replace_record_multi_100c(page_text, new_rta_100c_record_1=new_rta_record, new_ss_record=new_ss_record)
        elif is_second_multi_100c_record:
            page_text, summary = replace_record_multi_100c(page_text, new_rta_100c_record_2=new_rta_record, new_ss_record=new_ss_record)
        # Normal record handling
        else:
            page_text, summary = replace_record(page_text, new_rta_record=new_rta_record, new_ss_record=new_ss_record)
        
        print(page_text)
        print(summary)

        # page_text will be None if the record is
        # already updated (or has a faster time due
        # to me ignoring the extensions sheet for now), 
        # so just skip ahead to the next record in the list
        if page_text == None:
            # I did it like this because I wanted to
            msg = '"age is either already updated or has a faster time than was provided!"'
            log.add_update_result('P'+msg)
            print(f"{new_record_star_name}'s p{msg} Skipping record...")
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
            log.add_update_result('Success')
            print(f'{bcolors.OKGREEN}Success{bcolors.ENDC}')
        else:
            log.add_update_result(f"\"Failed to edit page 'RTA Guide/{new_record_star_name}'\"")
            print(f'{bcolors.FAIL}Failed{bcolors.ENDC}')
    log.out()

if __name__ == '__main__':
    main()