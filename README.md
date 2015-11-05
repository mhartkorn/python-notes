# Notes

Tiny blogging software in Python based on Flask. Very basic and fast, ideal to quickly type out toughts. Supports full HTML in all posts.

Initially written to write down snippets about commandline arguments.

How to install:

- Install dependencies with `pip install flask`
- Create SQLite database with `sqlite3 database.sqlite < schema.sql`
- Run `python3 notes.py`

This starts a HTTP server on `http://localhost:5000`. To login, navigate to `http://localhost:5000/admin` and enter the predefined credentials (name: `admin`, password `admin`).

Feel free to tunnel it through nginx or stunnel to create a secure connection.