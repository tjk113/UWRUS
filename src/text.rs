use std::{any::Any, convert::{TryFrom, TryInto}, intrinsics::type_id};

use regex;

use crate::record::Record;
use crate::star_time;

#[derive(Debug)]
pub enum UpdateError {
    TextAlreadyUpdated,
    TextInvalid
}

/// Each format's value corresponds to the
/// amount of captures expected for that
/// infobox type.
#[derive(Debug)]
pub enum InfoboxFormat {
    Standard = 2,
    Multiple100Coins = 3,
    BowserStage = 5
}

impl TryFrom<usize> for InfoboxFormat {
    type Error = UpdateError;

    fn try_from(v: usize) -> Result<Self, Self::Error> {
        match v {
            x if x == Self::Standard as usize => Ok(Self::Standard),
            x if x == Self::Multiple100Coins as usize => Ok(Self::Multiple100Coins),
            x if x == Self::BowserStage as usize => Ok(InfoboxFormat::BowserStage),
            _ => Err(UpdateError::TextInvalid)
        }
    }
}

fn wiki_link_to_parts(link: &str) -> (&str, &str) {
    let split: Vec<_> = link.splitn(3, ' ').collect();
    (split[0].trim_start_matches('['), split[1].trim_end_matches(']'))
}

impl InfoboxFormat {
    // TODO: Is dynamically determining this
    // position at runtime a horrendous idea?
    // NOTE: All of the indices returned are
    // 1-based because `cur_captures` always
    // includes the full match as its first
    // element.
    fn get_captures_index(&self, cur_captures: &regex::Captures<'_>, new_record: &Record) -> usize {
        match self {
            // Infobox Format:
            // ```
            // rta_record=...
            // ss_record=...
            // ```
            Self::Standard => {
                match new_record.is_rta {
                    true => 1,
                    false => 2
                }
            },
            // Infobox Format:
            // ```
            // rta_record=... / ...
            // ss_record=...
            // ```
            Self::Multiple100Coins => {
                if !new_record.is_rta {
                    3
                }
                else {
                    // The faster of the two 100c records goes first.
                    let first_capture = cur_captures.get(1).unwrap().as_str();
                    let (_, first_time) = wiki_link_to_parts(first_capture);
                    let second_capture = cur_captures.get(2).unwrap().as_str();
                    let (_, second_time) = wiki_link_to_parts(second_capture);

                    // Check that the new record is less than or equal to the
                    // current first record, and less than teh current second
                    // record.
                    let first_comparison = star_time::compare(&new_record.time, first_time).unwrap();
                    let second_comparison = star_time::compare(&new_record.time, second_time).unwrap();
                    if first_comparison.is_le() && second_comparison.is_lt() {
                        1
                    }
                    else {
                        2
                    }
                }
            },
            // Infobox Format:
            // ```
            // rta_record=... / ...
            // ss_record=... / ...
            // throw(s)_record=...
            // ```
            Self::BowserStage => {
                match new_record.star {
                    // Course
                    0 => if new_record.is_rta { 1 } else { 3 },
                    // Red Coins Star
                    1 => if new_record.is_rta { 2 } else { 4 },
                    // Throw(s)
                    2 => 5,
                    // This should never happen!
                    _ => panic!("Invalid star number for a Bowser course")
                }
            }
        }
    }

    fn add_to_summary(summary: &str, old_time: &str, new_time: &str) -> String {
        let mut owned = summary.to_owned();
        // If one or more star_time are present in the
        // summary, then append a comma.
        // TODO: Figure out a way to un-jankify this.
        if owned.len() > "Updated WRs: ".len() + 2 {
            owned.push_str(", ");
        }
        owned.push_str(format!("{old_time} to {new_time}").as_str());
        return owned;
    }

    pub fn update(&self, page_text: &str, new_records: &[Record]) -> Result<Update, UpdateError> {
        let records_pattern = self.get_regex();
        let captures = records_pattern.captures(page_text);
        if captures.is_none() {
            return Err(UpdateError::TextInvalid);
        }
        let cur_records = captures.unwrap();

        // Check to make sure that the actual format
        // is the same as the expected format.
        let num_captures = cur_records.len() - 1;
        let actual_format: InfoboxFormat = num_captures.try_into()?;
        if actual_format.type_id() != self.type_id().to_owned()
           || (actual_format as usize) != num_captures {
            return Err(UpdateError::TextInvalid);
        }

        let mut new_page_text = String::from(page_text);
        let mut summary = format!("Updated WR{}: ",
            if new_records.len() == 1 { "" } else { "s" });

        for new_record in new_records {
            let captures_index = self.get_captures_index(&cur_records, new_record);
            let cur_record = cur_records.get(captures_index).unwrap().as_str();
            let (cur_link, cur_time) = wiki_link_to_parts(cur_record);
            // This comparison is `.is_le()` so that links can
            // be updated even when a time hasn't been improved.
            if star_time::compare(new_record.time.as_str(), cur_time).unwrap().is_le() {
                new_page_text = new_page_text.replacen(cur_time, &new_record.time, 1);
                new_page_text = new_page_text.replacen(cur_link, &new_record.video_link, 1);
                summary = InfoboxFormat::add_to_summary(&mut summary, cur_time, &new_record.time);
            }
        }
        Ok(Update::new(new_page_text, summary))
    }

    // TODO: This probably sucks to dynamically
    // reconstruct the regex every single time
    // we need to use it, but this can be
    // rethought later!
    // NOTE: These regex patterns will capture the [brackets]
    // around each record link. This is because somestar_time the
    // record text will not start with a link (namely, stars
    // for which no RTA strategy exists, such as Find the 8
    // Red Coins in Bob-omb Battlefield).
    fn get_regex(&self) -> regex::Regex {
        regex::RegexBuilder::new(match self {
            Self::Standard => {
                r#"rta_record=(?P<rta_record>.+[\]\)])\\n\|ss_record=(?P<ss_record>.+[\]\)])\\n}}"#
            },
            Self::Multiple100Coins => {
                r#"rta_record=(?P<rta_100c_record_1>.+\]) / (?P<rta_100c_record_2>.+\])\\n\|ss_record=(?P<ss_record>.+\])\\n}}"#
            },
            Self::BowserStage => {
                r#"rta_record=(?P<rta_course_record>.+[\]\)]) / (?P<rta_reds_record>.+[\]\)])\\n\|ss_record=(?P<ss_course_record>.+[\]\)]) / (?P<ss_reds_record>.+[\]\)])\\n\|throws?_record=(?P<throw_record>.+[\]\)])\\n}}"#
            }
        }).build().unwrap()
    }
}

#[derive(Debug)]
pub struct Update {
    pub text: String,
    pub summary: String
}

impl Update {
    pub fn new(text: String, summary: String) -> Self {
        Self {text, summary}
    }
}