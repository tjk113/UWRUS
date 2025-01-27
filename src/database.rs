use std::cmp;

use rusqlite::{Connection, Statement, Result, params};

use crate::record::Record;
use crate::times;

pub const PATH: &str = "records.db";

#[derive(Debug, PartialEq)]
pub enum RecordsTable {
    SingleStar,
    RTA
}

impl RecordsTable {
    pub fn to_table_name(&self) -> String {
        String::from(match self {
            Self::SingleStar => "ss_records",
            Self::RTA => "rta_records",
        })
    }
}

pub fn update_records(con: &mut Connection, new_records: &Vec<Record>, table: RecordsTable) -> Result<()> {
    let transaction = con.transaction()?;

    let query = format!(
        "UPDATE {}
        SET Time = ?3,
            VideoLink = ?4
        WHERE
            Course = ?1 AND Star = ?2;",
        table.to_table_name()
    );

    let mut statement = transaction.prepare(&query)?;

    for record in new_records {
        let params = match table {
            RecordsTable::SingleStar => params![
                record.course, record.star,
                record.time, record.video_link
            ],
            RecordsTable::RTA => params![
                record.course, record.star,
                record.time, record.video_link,
                record.with_100_coins
            ]
        };
        let _ = statement.execute(params)?;
    }

    // `statement` is manually dropped here so that
    // we can reclaim ownership of `transaction`, in
    // order to commit the changes.
    drop(statement);
    transaction.commit()?;

    Ok(())
}

pub fn get_new_records(con: &mut Connection, fetched_records: &Vec<Record>, table: RecordsTable) -> Result<Vec<Record>> {
    let transaction = con.transaction()?;

    let mut statement = transaction.prepare(
        format!("SELECT * FROM {};", table.to_table_name()).as_str()
    )?;

    let mut new_records = Vec::<Record>::new();

    let mut res = statement.query([])?;
    while let Some(row) = res.next()? {
        let course = row.get_ref_unwrap(0).as_i64()?;
        let star = row.get_ref_unwrap(1).as_i64()?;
        let time = row.get_ref_unwrap(2).as_str()?;
        let video_link = row.get_ref_unwrap(3).as_str()?;

        let fetched_record = fetched_records[fetched_records.iter().position(
            |x| (x.course as i64) == course
                && (x.star as i64) == star
                && match table {
                       // For RTA records, we also need to match the record
                       // to its route with the 100 coins star if it has one.
                       RecordsTable::RTA => {
                           let with_100_coins = row.get_ref_unwrap(4).as_i64().unwrap();
                           (x.with_100_coins as i64) == with_100_coins
                       },
                       _ => true
                }
        ).unwrap()].clone();

        let should_update = match times::compare(fetched_record.time.as_str(), time).unwrap() {
            cmp::Ordering::Less => true,
            _ => false
        } || fetched_record.video_link != video_link;

        if should_update {
            new_records.push(fetched_record);
        }
    }
    Ok(new_records)
}