# Notes

Tiny blogging software in Python based on Flask. Very basic and fast, ideal to quickly type out toughts. Supports full HTML in all posts.

Initially written to write down snippets about commandline arguments.

### Requirements

- Python 3.3 or later
- SQLite 3.7.11 or later

### How to install

- Install dependencies with `pip install flask` (use `pip -r requirements.txt` for using the unit tests)
- Create SQLite database with `sqlite3 database.sqlite < schema.sql`
- Change the value of `app.config['SECRET_KEY']` in `notes.py`
- Run `python3 notes.py`

This starts a HTTP server on `http://localhost:5000`. To login, navigate to `http://localhost:5000/admin` and enter the predefined credentials (name: `admin`, password `admin`).

Feel free to tunnel it through nginx or stunnel to create a secure connection.