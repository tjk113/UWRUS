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

use std::{fs, str};

use rusqlite::{Connection, Result};
// use mediawiki;

const UKIKIPEDIA_API_URL: &str = "https://ukikipedia.net/mediawiki/api.php";

fn main() -> Result<()> {
    // let con = Connection::open_with_flags("records.db",
    //     OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE)?;
    // let api = mediawiki::api_sync::ApiSync::new(UKIKIPEDIA_API_URL).unwrap();
    // api.login("MY BOT USER NAME", "MY BOT PASSWORD").unwrap();

    // let mut file = fs::File::create("replies.json").unwrap();
    // let _ = file.write(res.to_string().as_bytes());

    // TODO: merge disparate Result types
    // into a type that main can return
    // let mut con = Connection::open(database::PATH)?;
    // let ss_records = fetch::single_star_records().unwrap();
    // let new_ss_records = database::get_new_records(&mut con, &ss_records, database::RecordsTable::SingleStar).unwrap();
    // database::update_records(&mut con, &new_ss_records, database::RecordsTable::SingleStar)?;

    // TODO: fetch record pages...
    let page_text = fs::read_to_string("dev_resources/blastAwayTheWall.txt").unwrap();

    // let record_ind = new_ss_records.iter().position(|record| {
    //     record.course == 18 && record.star == 1
    // }).unwrap();
    // let record = new_ss_records[record_ind].clone();

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

    println!("{:?}", text::InfoboxFormat::Standard.update(&page_text, &[record, record2]));

    // let page_titles: Vec<_> = vec!["Bowser in the Sky", "CCM 100 Coins"]
    //     .iter()
    //     .map(|page_title| format!("RTA Guide/{page_title}"))
    //     .collect();
    // let page_titles_str = page_titles.join("|");
    // let params = api.params_into(&[
    //     ("action"       , "query"),
    //     ("meta"         , "tokens"),
    //     ("titles"       , page_titles_str.as_str()),
    //     ("prop"         , "revisions"),
    //     ("rvslots"      , "main"),
    //     ("rvprop"       , "content|timestamp"),
    //     ("formatversion", "2"),
    //     ("curtimestamp" , "true"),
    //     ("format"       , "json")
    // ]);

    // let res = api.get_query_api_json(&params).unwrap();

    Ok(())
}