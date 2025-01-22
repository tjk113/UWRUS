/// Data structures and functions for storing and modifying records.
mod record;
/// Functions for fetching records from remote sources.
mod fetch;
/// Functions for interacting with the records database.
mod database;
/// Functions for operating on times, as formatted by the single star and RTA record pages.
mod star_time;

// use mediawiki;
// use reqwest;
use rusqlite::{Connection, Result};

fn main() -> Result<()> {
    // let con = Connection::open_with_flags("records.db",
    //     OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE)?;

    // let url = "https://ukikipedia.net/mediawiki/api.php";
    // let mut api = mediawiki::api_sync::ApiSync::new(url).unwrap();
    // api.login("MY BOT USER NAME", "MY BOT PASSWORD").unwrap();
    // // let star_name = "Blast Away the Wall";
    // let params = api.params_into(&[
    //     ("action"       , "query"),
    //     ("meta"         , "tokens"),
    //     ("titles"       , "RTA Guide/Blast Away the Wall"),
    //     ("prop"         , "revisions"),
    //     ("rvslots"      , "main"),
    //     ("rvprop"       , "content|timestamp"),
    //     ("formatversion", "2"),
    //     ("curtimestamp" , "true"),
    //     ("format"       , "json")
    // ]);
    // let res = api.get_query_api_json(&params);

    // TODO: merge rusqlite::Result and reqwest::Result
    // into a type that main can return
    let mut con = Connection::open(database::PATH)?;
    let ss_records = fetch::single_star_records().unwrap();
    let new_ss_records = database::get_new_records(&mut con, &ss_records, database::RecordsTable::SingleStar).unwrap();

    database::update_records(&mut con, &new_ss_records, database::RecordsTable::SingleStar)?;

    Ok(())
}