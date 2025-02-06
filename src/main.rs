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

use record::Record;

use rusqlite::{Connection, Result};

fn construct_the_data_structure<'a>(session: &mut wiki::Session,
                                    new_rta_records: Vec<Record>,
                                    new_ss_records: Vec<Record>)
                                    -> Vec<(Vec<Record>, String)> {
    let new_records = [new_rta_records, new_ss_records].concat();
    let mut unique_stars = new_records.clone();
    // TODO: Does this actually deduplicate properly?
    unique_stars.dedup_by_key(|record| record.page_name.clone());
    println!("{:?}", new_records);

    let mut the_data_structure = Vec::new();

    let page_texts = session.get_page_texts(
        &unique_stars
            .iter()
            .map(|record| record.page_name.clone())
            .collect::<Vec<_>>()
    );

    for star in unique_stars {
        let records = new_records
            .iter()
            .filter(|record| record.page_name == star.page_name)
            .cloned()
            .collect::<Vec<_>>();
        the_data_structure.push(
            (records, page_texts[&star.page_name].to_owned())
        );
    }

    the_data_structure
}

fn main() -> Result<()> {
    let mut session = wiki::Session::new().unwrap();
    // let mut con = Connection::open(database::PATH)?;
    
    // // Why doesn't the google_sheetsv4 crate offer a synchronous API...
    // let runtime = tokio::runtime::Runtime::new().unwrap();
    // let rta_records = match runtime.block_on(fetch::rta_records()) {
    //     Ok(records) => records,
    //     Err(_) => {
    //         Vec::default()
    //         // eprintln!("{:?}", e);
    //         // return Err();
    //     }
    // };
    // let new_rta_records = database::get_new_records(&mut con, &rta_records, database::RecordsTable::RTA).unwrap();
    
    // let ss_records = fetch::single_star_records().unwrap();
    // let new_ss_records = database::get_new_records(&mut con, &ss_records, database::RecordsTable::SingleStar).unwrap();

    // database::update_records(&mut con, &rta_records, database::RecordsTable::RTA)?;
    // database::update_records(&mut con, &new_ss_records, database::RecordsTable::SingleStar)?;

    // Fake records for testing purposes:
    let record = record::Record {
        course: 2,
        star: 6,
        with_100_coins: false,
        page_name: String::from("Blast Away the Wall"),
        time: String::from("6.00"),
        is_rta: false,
        video_link: String::from("test.com"),
        video_time: None
    };
    let record2 = record::Record {
        course: 2,
        star: 6,
        with_100_coins: false,
        page_name: String::from("Blast Away the Wall"),
        time: String::from("5.97"),
        is_rta: true,
        video_link: String::from("test.com"),
        video_time: None
    };

    let mut a1 = Vec::new();
    a1.push(record);
    let mut a2 = Vec::new();
    a2.push(record2);
    let the_data_structure = construct_the_data_structure(&mut session, a1, a2);
    println!("{:#?}", the_data_structure);

    // for records_info in records_infos {
        
    // }
    
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