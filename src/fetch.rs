use std::fs;

use google_sheets4 as sheets4;
use sheets4::{Sheets, hyper_rustls, hyper_util, yup_oauth2};
use hyper_util::client::legacy::connect::HttpConnector;
use hyper_rustls::HttpsConnector;
use regex::Regex;
use serde_json;
use reqwest;

use crate::record::Record;
use crate::times;

const SINGLE_STAR_RECORDS_URL: &str = "https://singlestar.sm64rta.info/singlestar/";

const RTA_RECORDS_SPREADSHEET_ID: &str = "1J20aivGnvLlAuyRIMMclIFUmrkHXUzgcDmYa31gdtCI";
const RTA_RECORDS_SPREADSHEET_RANGE: &str = "'Best Time(Raw)'!B4:K";

#[derive(Debug)]
pub enum FetchError {
    Sheets(sheets4::Error),
    Reqwest(reqwest::Error),
    IO(std::io::Error)
}

impl From<sheets4::Error> for FetchError {
    fn from(e: sheets4::Error) -> Self {
        FetchError::Sheets(e)
    }
}

impl From<reqwest::Error> for FetchError {
    fn from(e: reqwest::Error) -> Self {
        FetchError::Reqwest(e)
    }
}

impl From<std::io::Error> for FetchError {
    fn from(e: std::io::Error) -> Self {
        FetchError::IO(e)
    }
}

pub type Result<T> = std::result::Result<T, FetchError>;

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

pub fn single_star_records() -> Result<Vec<Record>> {
    // For testing purposes:
    let html = fs::read_to_string("dev_resources/new_ss.html")?;
    // let html = reqwest::blocking::get(SINGLE_STAR_RECORDS_URL)?.text()?;

    let cell_pattern = Regex::new(r#"<td( class="small")?>((<a href="(?<link>.+)">)|(<i class=.+"><span .+oon">)|(<img src="/img/flag/(?<region>us|jp|eu)\.png".+t">))?(?<text>[^<]*)"#).unwrap();

    let lines = html.lines();
    let mut records = Vec::<Record>::new();
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
                    cur_record.time = times::format(
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

async fn get_sheets_hub() -> Result<Sheets<HttpsConnector<HttpConnector>>> {
    let creds_json = fs::read_to_string("auth/credentials.json")?;
    let secret: yup_oauth2::ApplicationSecret =
        match serde_json::from_str::<yup_oauth2::ConsoleApplicationSecret>(&creds_json) {
            Ok(s) => s.installed.unwrap(),
            Err(err) => panic!("Encountered error parsing ApplicationSecret: {}", err)
        };

    let auth = yup_oauth2::InstalledFlowAuthenticator::builder(
        secret,
        yup_oauth2::InstalledFlowReturnMethod::HTTPRedirect,
    ).persist_tokens_to_disk("auth/token.json").build().await?;

    let client = hyper_util::client::legacy::Client::builder(
        hyper_util::rt::TokioExecutor::new()
    )
    .build(
        hyper_rustls::HttpsConnectorBuilder::new()
            .with_native_roots()
            .unwrap()
            .https_or_http()
            .enable_http1()
            .build()
    );

    Ok(Sheets::new(client, auth))
}

// This predicate for pushing records means that we
// will only take the fastest time for each star
// across all strategies.
fn should_push(fastest: &Option<Record>, cur: &Record) -> bool {
    if let Some(fastest) = fastest {
        times::compare(&cur.time, &fastest.time)
            .unwrap().is_lt()
    }
    else {
        true
    }
}

fn is_same_star(a: &Record, b: &Record) -> bool {
    a.star == b.star
    && a.course == b.course
    && a.with_100_coins == b.with_100_coins
}

pub async fn rta_records() -> Result<Vec<Record>> {
    let hub = get_sheets_hub().await?;
    let values = hub
        .spreadsheets()
        .values_get(RTA_RECORDS_SPREADSHEET_ID, RTA_RECORDS_SPREADSHEET_RANGE)
        .add_scope(sheets4::api::Scope::SpreadsheetReadonly)
        .value_render_option("FORMULA")
        .doit()
        .await?;

    let mut records = Vec::<Record>::new();
    // The fastest time for the current star.
    let mut fastest_record: Option<Record> = None;
    for row in &values.1.values.unwrap() {
        let b: Vec<_> = row
            .iter()
            .map(|val| val
                .to_string()
                .replace('"', "")
                .replace("\\", ""))
            .collect();

        let record = (&b).try_into();
        match record {
            Ok(record) => {
                if let Some(fastest) = &fastest_record {
                    if !is_same_star(&fastest, &record) {
                        fastest_record = None;
                    }
                }
                if should_push(&fastest_record, &record) {
                    if let Some(_) = &fastest_record {
                        let _ = records.pop().unwrap();
                    }
                    fastest_record = Some(record.clone());
                    records.push(record);
                }
            },
            _ => {}
        }
    }

    Ok(records)
}