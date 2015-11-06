CREATE TABLE notes (
  noteid INTEGER PRIMARY KEY,
  date DATE NOT NULL,
  text TEXT NOT NULL
);

INSERT INTO notes (date, text) VALUES (DATE('now'), 'This is the first entry.');

CREATE TABLE tags (
  tagid INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

INSERT INTO tags (name) VALUES ('First Post');

CREATE TABLE notetags (
  noteid INTEGER REFERENCES notes (noteid) NOT NULL,
  tagid INTEGER REFERENCES tags (tagid) NOT NULL,
  CONSTRAINT pk_nt PRIMARY KEY (noteid, tagid)
);

INSERT INTO notetags (noteid, tagid) VALUES (1, 1);

CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT INTO settings (key, value) VALUES ('admin_username', 'admin');
INSERT INTO settings (key, value) VALUES ('admin_password', 'admin');
-- INSERT INTO settings (key, value) VALUES ('last_day', DATE('now'));
