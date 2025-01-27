#[derive(Debug, Clone, Default)]
pub struct Record {
    pub course: u8,
    pub star: u8,
    pub with_100_coins: bool,
    pub page_name: String,
    pub time: String,
    pub is_rta: bool,
    pub video_link: String,
    pub video_time: Option<String>
}

impl Record {
    pub fn to_wiki_link(&self) -> String {
        format!("[{} {} {}]", self.video_link, self.time,
                if self.with_100_coins {
                    format!("(with {})", self.page_name)
                }
                else { String::from("") }
        )
    }
}

#[derive(Debug)]
pub enum RecordParseError {
    NotEnoughParameters,
    UntrackedRecord
}

impl TryFrom<&Vec<String>> for Record {
    type Error = RecordParseError;

    fn try_from(v: &Vec<String>) -> Result<Self, Self::Error> {
        // Indices into the Value array `v`.
        let time_index = 0;
        let course_index = 3;
        let star_index = 6;
        let is_full_star_index = 8;

        if v.len() < 10 {
            return Err(RecordParseError::NotEnoughParameters);
        }

        let mut record = Record::default();
        record.is_rta = true;

        let course = str::parse::<i8>(&v[course_index]).unwrap();
        if course == -1 || v[is_full_star_index] != "1" || !(1..=24).contains(&course) {
            return Err(RecordParseError::UntrackedRecord);
        }
        record.course = course as u8;

        let star_comma_index = v[star_index].find(',');
        if star_comma_index.is_some() {
            let cloned = v[star_index].clone();
            let star = cloned.split_at(star_comma_index.unwrap()).0;
            println!("{star}");
            record.star = str::parse::<u8>(&star).unwrap();
            record.with_100_coins = true;
        }
        else {
            let star = str::parse::<i8>(&v[star_index]).unwrap();
            if star == -1 {
                return Err(RecordParseError::UntrackedRecord);
            }
            record.star = star as u8;
        }

        let split: Vec<_> = v[time_index].split(',').collect();
        (record.video_link, record.time) =
            (split[0].trim_start_matches("=HYPERLINK(").to_string(),
             split[1].trim_end_matches(')').to_string());

        Ok(record)
    }
}