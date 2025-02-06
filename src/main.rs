#![feature(core_intrinsics)]

/// Data structures and functions for storing and modifying records.
mod record;
/// Functions for fetching records from remote sources.
mod fetch;
/// Functions for interacting with the records database.
mod database;
/// Functions for operating on times, as formatted by the single star and RTA record pages.
mod times;
/// Functions for editing page text to be uploaded to the wiki.
mod text;
/// Functions for interacting with Ukikipedia pages using the MediaWiki API.
mod wiki;

use std::{fs, io::{BufWriter, Write}, ops::Index, str};

use record::{Record, RecordData};

use rusqlite::{Connection, Result};
use text::InfoboxFormat;

fn is_multi_100c_stage(stage: u8) -> bool {
    match stage {
        4 | 11 | 13 | 15 => true,
        _ => false
    }
}

fn main() -> Result<()> {
    let mut session = wiki::Session::new().unwrap();
    let mut con = Connection::open(database::PATH)?;
    
    // // Why doesn't the google_sheetsv4 crate offer a synchronous API...
    let runtime = tokio::runtime::Runtime::new().unwrap();
    let rta_records = match runtime.block_on(fetch::rta_records()) {
        Ok(records) => records,
        Err(_) => {
            Vec::default()
            // eprintln!("{:?}", e);
            // return Err();
        }
    };
    let new_rta_records = database::get_new_records(&mut con, &rta_records, database::RecordsTable::RTA).unwrap();
    
    let ss_records = fetch::single_star_records().unwrap();
    let new_ss_records = database::get_new_records(&mut con, &ss_records, database::RecordsTable::SingleStar).unwrap();

    let _ = database::update_records(&mut con, &rta_records, database::RecordsTable::RTA)?;
    let _ = database::update_records(&mut con, &new_ss_records, database::RecordsTable::SingleStar)?;

    // Fake records for testing purposes:
    // let record = record::Record {
    //     course: 2,
    //     star: 6,
    //     with_100_coins: false,
    //     page_name: String::from("Blast Away the Wall"),
    //     time: String::from("6.00"),
    //     is_rta: false,
    //     video_link: String::from("test.com"),
    //     video_time: None
    // };
    // let record2 = record::Record {
    //     course: 2,
    //     star: 6,
    //     with_100_coins: false,
    //     page_name: String::from("Blast Away the Wall"),
    //     time: String::from("5.97"),
    //     is_rta: true,
    //     video_link: String::from("test.com"),
    //     video_time: None
    // };

    // let mut a1 = Vec::new();
    // a1.push(record);
    // let mut a2 = Vec::new();
    // a2.push(record2);
    let records_data = RecordData::from_to_vec(
        &mut session,
        new_rta_records,
        new_ss_records
    );
    println!("{:#?}", records_data);

    for record_data in records_data {
        let course = record_data.records[0].course;
        let with_100_coins = record_data.records[0].with_100_coins;
        let is_multi_100c = match course {
            // CCM, WDW, THI, RR
            4 | 11 | 13 | 15 => with_100_coins,
            _ => false
        };
        let format = match course {
            0..=15 => {
                if is_multi_100c {
                    InfoboxFormat::Multiple100Coins
                }
                else {
                    InfoboxFormat::Standard
                }
            },
            _ => InfoboxFormat::BowserStage
        };

        let _ = format.update(&record_data.page_text, &record_data.records);
    }
    
    // TODO: fetch record pages...
    // let page_text = fs::read_to_string("dev_resources/blastAwayTheWall.txt").unwrap();

    // let record_ind = new_ss_records.iter().position(|record| {
    //     record.course == 18 && record.star == 1
    // }).unwrap();
    // let record = new_ss_records[record_ind].clone();

    // println!("{:?}", text::InfoboxFormat::Standard.update(&page_text, &[record, record2]));


    // for record in rta_records {
    //     println!("{:#?}", record);
    // }

    Ok(())
}