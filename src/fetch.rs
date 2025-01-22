use regex::Regex;
use reqwest;

use std::fs;

use crate::record::Record;
use crate::star_time;

const SINGLE_STAR_RECORDS_URL: &str = "https://singlestar.sm64rta.info/singlestar/";

// The database stores secret stage course numbers as
// found on the Ultimate Star Spreadsheet v2's "Raw Times"
// sheet, so the natural indices need to be adjusted to match.
fn adjust_course_num_for_database(record: &mut Record) {
    match record.course {
        16 => {
            match record.star {
                1 => {
                    record.course = 21;
                    record.star = 1;
                },
                2 => {
                    record.course = 22;
                    record.star = 1;
                },
                3 => {
                    record.course = 20;
                    record.star = 1;
                },
                4 => {
                    record.course = 19;
                    record.star = 1;
                },
                5 => {
                    record.course = 19;
                    record.star = 2;
                },
                6 => {
                    record.course = 24;
                    record.star = 1;
                },
                7 => {
                    record.course = 23;
                    record.star = 1;
                },
                _ => {}
            }
        }
        17 => {
            match record.star {
                1 => {
                    record.course = 16;
                    record.star = 0;
                },
                2 => {
                    record.course = 16;
                    record.star = 1;
                },
                3 => {
                    record.course = 16;
                    record.star = 2;
                },
                4 => {
                    record.course = 17;
                    record.star = 0;
                },
                5 => {
                    record.course = 17;
                    record.star = 1;
                },
                6 => {
                    record.course = 17;
                    record.star = 2;
                },
                7 => {
                    record.course = 18;
                    record.star = 0;
                },
                8 => {
                    record.course = 18;
                    record.star = 1;
                },
                9 => {
                    record.course = 18;
                    record.star = 2;
                },
                _ => {}
            }
        }
        _ => {}
    }
}

pub fn single_star_records() -> reqwest::Result<Vec<Record>> {
    // For testing purposes:
    let html = fs::read_to_string("new.html").unwrap();
    // let html = reqwest::blocking::get(SINGLE_STAR_RECORDS_URL)?.text()?;

    let cell_pattern = Regex::new(r#"<td( class="small")?>((<a href="(?<link>.+)">)|(<i class=.+"><span .+oon">)|(<img src="/img/flag/(?<region>us|jp|eu)\.png".+t">))?(?<text>[^<]*)"#).unwrap();

    let lines = html.lines();
    let mut records: Vec<Record> = Vec::new();
    let mut cur_record: Record = Record::default();
    // Keep track of which field we're on
    // when populating a Record struct.
    let mut field_counter = 0;
    for line in lines {
        // Stop at the end of the table.
        if line.contains("Singlestar WR Counter") {
            break;
        }
        else if line.contains("./stage?name=") {
            cur_record.course += 1;
            cur_record.star = 0;
        }
        else if line.ends_with("r>") {
            if cur_record.page_name.len() > 0 {
                cur_record.star += 1;
                records.push(cur_record.clone());
                // Listen, I will make as many
                // allocations as I want...
                cur_record.page_name = String::new();
            }
            continue;
        }

        let fields = cell_pattern.captures(line);
        if let Some(fields) = fields {
            match field_counter {
                0 => {
                    cur_record.page_name = fields["text"].to_string();
                    // Only take the first row if there are ties for a record.
                    if cur_record.page_name.len() == 0 {
                        field_counter += 1;
                        continue;
                    }
                },
                2 => {
                    cur_record.time = star_time::format(
                        fields["text"].to_string().as_str()
                    );

                    let mut video_link = fields["link"].to_string();
                    video_link = video_link.split("\" ").next().unwrap().to_string();
                    cur_record.video_link = video_link;
                },
                6 => {
                    field_counter = 0;
                    continue;
                }
                _ => {}
            }
            field_counter += 1;
        }
    }

    for record in &mut records {
        adjust_course_num_for_database(record);
    }

    Ok(records)
}

pub fn rta_records() -> Vec<Record> {
    todo!("fetch::rta_records")
}