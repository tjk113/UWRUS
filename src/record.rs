#[derive(Debug, Clone)]
pub struct Record {
    pub course: u8,
    pub star: u8,
    pub with_100_coins: bool,
    pub page_name: String,
    pub time: String,
    pub video_link: String,
    pub video_time: Option<String>
}

impl Record {
    pub fn default() -> Self {
        Self {course: 0, star: 0, with_100_coins: false,
              page_name: String::default(), time: String::default(),
              video_link: String::default(), video_time: None}
    }
}