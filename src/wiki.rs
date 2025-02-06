use std::{collections::HashMap, fs, io::{self, Read}};

use serde_json::{self, from_str};

use mediawiki;

pub const UKIKIPEDIA_API_URL: &str = "https://ukikipedia.net/mediawiki/api.php";

#[derive(Debug)]
pub struct Session {
    api: mediawiki::api_sync::ApiSync,
    pages_queried: usize,
    pages_updated: usize
}

#[derive(Debug)]
pub enum WikiError {
    Login(io::Error),
    LoginParse(String),
    MediaWiki(mediawiki::MediaWikiError)
}

impl From<io::Error> for WikiError {
    fn from(e: io::Error) -> Self {
        WikiError::Login(e)
    }
}

impl From<String> for WikiError {
    fn from(e: String) -> Self {
        WikiError::LoginParse(e)
    }
}

impl From<mediawiki::MediaWikiError> for WikiError {
    fn from(e: mediawiki::MediaWikiError) -> Self {
        WikiError::MediaWiki(e)
    }
}

pub type Result<T> = std::result::Result<T, WikiError>;

impl Session {
    pub fn new() -> Result<Self> {
        let mut api = mediawiki::api_sync::ApiSync::new(UKIKIPEDIA_API_URL)?;
    
        // let mut file = fs::File::open("auth/ukiki")?;
        // let mut content = String::new();
        // let _ = file.read_to_string(&mut content)?;
        // if let Some((user, pass)) = content.split_once(' ') {
        //     api.login(user, pass)?;
        // }
        // else {
        //     return Err(WikiError::LoginParse(String::from("invalid credentials format for auth/ukiki")));
        // }

        Ok(Session {api, pages_queried: 0, pages_updated: 0})
    }

    pub fn get_page_texts(&mut self, star_names: &[String]) -> HashMap<String, String> {
        let mut set = HashMap::new();
        let page_titles = star_names
            .into_iter()
            .map(|page_title| format!("RTA Guide/{page_title}"))
            .collect::<Vec<_>>()
            .join("|");
        println!("{page_titles}");
        let params = self.api.params_into(&[
            ("action"       , "query"),
            ("meta"         , "tokens"),
            ("titles"       , &page_titles),
            ("prop"         , "revisions"),
            ("rvslots"      , "main"),
            ("rvprop"       , "content|timestamp"),
            ("formatversion", "2"),
            ("curtimestamp" , "true"),
            ("format"       , "json")
        ]);
        // let mut file = std::fs::File::open("dev_resource/bits_ccm_response.json").unwrap();
        // let mut bytes = Vec::<u8>::new();
        // let _ = file.read_to_end(&mut bytes);
        // let json = String::from_utf8(bytes).unwrap();
        // let res: serde_json::Value = serde_json::from_str(&json).unwrap();
    
        let res = self.api.get_query_api_json(&params).unwrap();
        for page in res["query"]["pages"].as_array().unwrap() {
            let content = page["revisions"][0]["slots"]["main"]["content"]
                .as_str()
                .unwrap()
                .to_string();
            let page_title = page["title"]
                .as_str()
                .unwrap()
                .split('/')
                .nth(1)
                .unwrap()
                .to_string();
            set.insert(page_title, content);
            self.pages_queried += 1;
        }
    
        set
    }

    pub fn update_page(&mut self, star_name: String, new_text: String) -> Result<()> {
        
        
        Ok(())
    }
}