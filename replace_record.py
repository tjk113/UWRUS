import re

from get_records import remove_mins_place

def replace_page_text(cur_page_text: str, parsed_records: str, \
                      cur_records: list[tuple[str, str]], \
                      new_records: list[tuple[str, str]]) -> tuple[str, str] | tuple[None, None]:
    '''
    Replaces records in page text and returns the new page
    and edit summary (or (None, None) if a record needs to be skipped) 
    '''
    # Have to be kinda quirky with this regex because 
    # findall has fun properties when it comes to groups :D 
    record_text_pattern = re.compile(r'(\d*\:?\d*\.\d+[^\] ]+?I?G?T?\)?) ?\(?(?P<specifier_text>[^\]\)]+)?[^\n]?')
    edit_summary = "Updated WR(s) '"

    # If somehow replace_record is called for a page
    # that is already updated (or has a faster time due
    # to me ignoring the extensions sheet for now),
    # don't bother updating it again.
    parsed_cur_records = record_text_pattern.findall(parsed_records)
    for cur_record, new_record in zip(parsed_cur_records, new_records):
        specifier_text = None
        if len(cur_record) > 1:
            specifier_text = cur_record[1]
        cur_record_time = cur_record[0]
        new_record_time = new_record[0]
        if new_record_time == cur_record_time:
            # Main script expects page_text to be None
            # if it's meant to skip over a given record
            return (None, None)
        if 'IGT' in new_record_time:
            new_record_time = new_record_time[:-6]
        if ':' in new_record_time:
            new_record_time = remove_mins_place(new_record_time)
        new_record_time = float(new_record_time)
        if 'IGT' in cur_record_time:
            cur_record_time = cur_record_time[:-6]
        if ':' in cur_record_time:
            cur_record_time = remove_mins_place(cur_record_time)
        cur_record_time = float(cur_record_time)
        if new_record_time > cur_record_time:
            return (None, None)

    # Replace provided record tuples with properly formatted
    # strings, and update those records in the page text
    new_page_text = cur_page_text
    for cur_record, new_record in zip(cur_records, new_records):
        # Note: this can't handle a scenario in which
        # there is a new rta record and a new best available
        # video. To handle this, there would need to be
        # logic that could search the whole spreadsheet
        # by row for the matching video link, and then use
        # that cell's time in place of new_record[0] in the
        # time comparison below

        # Getting cur_record_time again because I couldn't find an easier way...
        cur_record_time = record_text_pattern.search(cur_record).group(1)
        new_record_time = new_record[0]
        # Annoying that it's being done this way but
        # it's the path of least resistance
        specifier_text = None
        for parsed_cur_record in parsed_cur_records:
            if parsed_cur_record[0] == cur_record_time:
                specifier_text = parsed_cur_record[1]

        if specifier_text:
            if len(specifier_text.split(' ')) > 1 and specifier_text.split(' ')[1] == 'Best':
                # If the best time currently has no video
                # and video and this new entry still isn't
                # faster, just replace the video

                if float(new_record[0]) > float(cur_record_time):
                    new_record = f'{new_record[0]} [{new_record[1]} ({specifier_text})]'
                else:
                    new_record = f'[{new_record[1]} {new_record[0]}]'
            else:
                cur_record_time = record_text_pattern.search(cur_record + ']').group(1)
                if specifier_text == 'IGT':
                    new_record = f'[{new_record[1]} {new_record[0]}]'
                else:
                    new_record = f'[{new_record[1]} {new_record[0]} ({specifier_text})]'
        else:
            new_record = f'[{new_record[1]} {new_record[0]}]'
        igt_text = ' (IGT)' if specifier_text == 'IGT' else ''
        edit_summary += str(cur_record_time) + igt_text + "' to '" + new_record_time + "', '"
        # Update parsed_records with the newly added record, so the next
        # iteration will be looking for the correct string in the page text,
        # and update the page text with the new parsed_records
        new_parsed_records = parsed_records.replace(cur_record, new_record)
        new_page_text = new_page_text.replace(parsed_records, new_parsed_records)
        parsed_records = new_parsed_records
    edit_summary = edit_summary[:-3] # remove final hanging ", '"

    return new_page_text, edit_summary

def replace_record(cur_page_text: str, new_rta_record: tuple[str, str] = None, \
                   new_ss_record: tuple[str, str] = None) -> tuple[str, str] | tuple[None, None]:
    '''
    Replaces specified records in page text (specify record params in call),
    and returns the new page text and edit summary
    '''
    records_pattern = re.compile(r'rta_record=(?P<rta_record>.+[\]\)])\n'
                                 +'\|ss_record=(?P<ss_record>.+[\]\)])\n')
    parsed_records = records_pattern.search(cur_page_text)

    new_records = [i for i in [new_rta_record, new_ss_record] if i != None]
    cur_records = []
    if new_rta_record:
        cur_records.append(parsed_records.group('rta_record'))
    if new_ss_record:
        cur_records.append(parsed_records.group('ss_record'))
    parsed_records = parsed_records.group() # we only need this as a string now

    return replace_page_text(cur_page_text, parsed_records, cur_records, new_records)

def replace_record_bowser(cur_page_text: str, new_rta_course_record: tuple[str, str] = None, \
                          new_rta_reds_record:  tuple[str, str] = None, \
                          new_ss_course_record: tuple[str, str] = None, \
                          new_ss_reds_record:   tuple[str, str] = None, \
                          new_throw_record:     tuple[str, str] = None) -> tuple[str, str] | tuple[None, None]:
    '''
    Replaces specified Bowser stage records in page text (specify record params in call),
    and returns the new page text and edit summary
    '''
    records_pattern = re.compile(r'rta_record=(?P<rta_course_record>.+[\]\)]) \/ '
                                 +'(?P<rta_reds_record>.+[\]\)])\n'
                                 +'\|ss_record=(?P<ss_course_record>.+[\]\)]) \/ '
                                 +'(?P<ss_reds_record>.+[\]\)])\n'
                                 +'\|throw_record=(?P<throw_record>.+[\]\)])\n')
    parsed_records = records_pattern.search(cur_page_text)

    new_records = [i for i in [new_rta_course_record, new_rta_reds_record,
                   new_ss_course_record, new_ss_reds_record, new_throw_record] if i != None]
    cur_records = []
    if new_rta_course_record:
        cur_records.append(parsed_records.group('rta_course_record'))
    if new_rta_reds_record:
        cur_records.append(parsed_records.group('rta_reds_record'))
    if new_ss_course_record:
        cur_records.append(parsed_records.group('ss_course_record'))
    if new_ss_reds_record:
        cur_records.append(parsed_records.group('ss_reds_record'))
    if new_throw_record:
        cur_records.append(parsed_records.group('throw_record'))
    parsed_records = parsed_records.group() # we only need this as a string now

    return replace_page_text(cur_page_text, parsed_records, cur_records, new_records)

def replace_record_multi_100c(cur_page_text: str, new_rta_100c_record_1:  tuple[str, str] = None, \
                              new_rta_100c_record_2: tuple[str, str] = None, \
                              new_ss_record:   tuple[str, str] = None) -> tuple[str, str] | tuple[None, None]:
    '''
    Replaces specified multi-route 100c records in page text (specify record params in call),
    and returns the new page text and edit summary
    '''
    records_pattern = re.compile(r'rta_record=(?P<rta_100c_record_1>.+)\] \/ '
                                 +'(?P<rta_100c_record_2>.+)\]\n'
                                 +'\|ss_record=(?P<ss_record>.+)\]\n')
    parsed_records = records_pattern.search(cur_page_text)

    new_records = [i for i in [new_rta_100c_record_1, new_rta_100c_record_2,
                   new_ss_record] if i != None]
    cur_records = []
    if new_rta_100c_record_1:
        cur_records.append(parsed_records.group('rta_100c_record_1'))
    if new_rta_100c_record_2:
        cur_records.append(parsed_records.group('rta_100c_record_2'))
    if new_ss_record:
        cur_records.append(parsed_records.group('ss_record'))
    parsed_records = parsed_records.group() # we only need this as a string now

    return replace_page_text(cur_page_text, parsed_records, cur_records, new_records)

# Test Driver Code
if __name__ == '__main__':
    page_text = 'reg'
    page_text_cpy = page_text

    if page_text == 'bowser':
        page_text = ''
        with open('test_page_bowser.txt', 'r') as file:
            for line in file:
                page_text += line
    elif page_text == '100':
        page_text = ''
        with open('test_page_100_2.txt', 'r') as file:
            for line in file:
                page_text += line
    elif page_text == 'reg':
        page_text = ''
        with open('test_page.txt', 'r') as file:
            for line in file:
                page_text += line

    if page_text_cpy == '100':
        new_rta_100c_wr = ('1:08.36', 'https://www.youtube.com/watch?v=p8u_k2LIZyo')
        new_ss_100c_wr = ('1:08.36', 'https://www.youtube.com/watch?v=p8u_k2LIZyo')
        new_text, edit_summary = replace_record(page_text, new_rta_record=new_rta_100c_wr, new_ss_record=new_ss_100c_wr)
    elif page_text_cpy == 'bowser':
        new_bowser_course_rta_wr = ('26.30', 'https://www.youtube.com/watch?v=wr4x8ngvhjc')
        new_bowser_reds_rta_wr = ('42.30', 'https://www.youtube.com/watch?v=Do5_wU9X1pc')
        new_bowser_course_ss_wr = ('23.76 (IGT)', 'https://youtu.be/8dwSydGAJsk')
        new_bowser_reds_ss_wr = ('41.72', 'https://youtu.be/uhk_vPPXhLM')
        new_bowser_throw_wr = ('24.83', 'https://www.youtube.com/watch?v=84r1NnU5WRc')
        new_text, edit_summary = \
            replace_record_bowser(page_text, new_rta_course_record=new_bowser_course_rta_wr,
                                new_rta_reds_record=new_bowser_reds_rta_wr, new_ss_course_record= \
                                new_bowser_course_ss_wr, new_ss_reds_record=new_bowser_reds_ss_wr,
                                new_throw_record=new_bowser_throw_wr)
    elif page_text_cpy == 'reg':
        new_rta_wr = ('17.40', 'https://www.youtube.com/watch?v=W72cyc5sESo')
        # new_rta_wr = None
        new_ss_wr = ('8.20', 'https://www.youtube.com/watch?v=84r1NnU5WRc')
        new_text, edit_summary = replace_record(page_text, new_rta_record=new_rta_wr, new_ss_record=new_ss_wr)
    # new_text, edit_summary = replace_record_bowser(page_text, new_throw_record=new_bowser_throw_wr)

    # new_rta_100c_wr = ('1:29.53', 'https://youtu.be/9YBxtwAJKaU')
    # new_text, edit_summary = replace_record_multi_100c(page_text, new_rta_100c_record_1=new_rta_100c_wr)
    ind = new_text.index('}')
    new_text = new_text[:ind]
    print(new_text)
    print(edit_summary)