DROP TABLE IF EXISTS user;  
DROP TABLE IF EXISTS employee; 

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);
INSERT INTO user (username, password) VALUES ('admin', 'scrypt:32768:8:1$ecnkwtzPiGDn1pOG$5ff45cde0bc210e51aa0fd9f9feef57558c25e36fbef0c69e742f0a542deac323fe02c9016b94b2f2c44aaf776bdda84151f9a7d18251d52dda10237434798ae');
CREATE TABLE employee (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_code TEXT UNIQUE NOT NULL,
  card_no TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  email TEXT ,
  pdf_password TEXT
);

-- CREATE TABLE attendance (
--   id INTEGER PRIMARY KEY AUTOINCREMENT,
--   comapny TEXT NOT NULL,
--   location TEXT NOT NULL,
--   date_range TEXT NOT NULL,
--   employee_code TEXT NOT NULL,
--   date TEXT ,
--   in_time TEXT,
--   out_time TEXT,
-- );

-- CREATE TABLE post (
--   id INTEGER PRIMARY KEY AUTOINCREMENT,
--   author_id INTEGER NOT NULL,
--   created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
--   title TEXT NOT NULL,
--   body TEXT NOT NULL,
--   FOREIGN KEY (author_id) REFERENCES user (id)
-- );