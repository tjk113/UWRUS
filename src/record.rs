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