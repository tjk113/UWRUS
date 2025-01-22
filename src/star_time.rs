use std::cmp;

/// Format `time` into the format used on Ukikipedia,
/// i.e. "x:xx.xx"
/// Note: this function should only need to be used on
/// times from the single star records table.
pub fn format(time: &str) -> String {
    time.replace("\"", ".").replace("'", ":")
}

/// Compare the time `a` to `b`, where they
/// are of the format "x:xx.xx".
pub fn compare(a: &str, b: &str) -> Option<cmp::Ordering> {
    let to_seconds = |time: &str| -> f32 {
        let minutes: Vec<_> = time.split(":").collect();
        if minutes.len() == 2 {
            return (str::parse::<f32>(minutes[0]).unwrap() * 60.0)
                    + str::parse::<f32>(minutes[1]).unwrap();
        }
        else {
            return str::parse(time).unwrap();
        };
    };
    to_seconds(a).partial_cmp(&to_seconds(b))
}