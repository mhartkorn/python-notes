#!/usr/bin/env python

import sqlite3 as sql
import time
import urllib
from uuid import uuid4

from flask import Flask, g, render_template, request, redirect, url_for, session, abort

app = Flask('notes')
app.config['SECRET_KEY'] = 'ReallyReallyLongUniqueSecretKey'
app.config['DATABASE'] = './database.sqlite'


@app.route('/')
def index_page():
    query = query_db(
        "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name) AS tags FROM notes "
        "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
        # "WHERE notes.date >= DATE((SELECT value FROM settings WHERE key='lastday')) GROUP BY notes.noteid "
        "GROUP BY notes.noteid "
        "ORDER BY notes.date DESC, notes.noteid DESC")

    return display(query)


@app.route('/tag/<path:tag>')
def tag_page(tag):
    query = query_db(
        "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name) AS tags FROM notes "
        "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
        # "WHERE notes.date >= DATE((SELECT value FROM settings WHERE key='lastday')) AND "
        "WHERE notes.noteid IN (SELECT notetags.noteid FROM notetags "
        "WHERE notetags.tagid=(SELECT tagid FROM tags WHERE LOWER(name)=?)) "
        "GROUP BY notes.noteid ORDER BY notes.date DESC, notes.noteid DESC", [urllib.parse.unquote_plus(tag).lower()])

    return display(query)


@app.route('/note/<int:noteid>')
def single_note_page(noteid):
    query = query_db(
        "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name) AS tags FROM notes "
        "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
        "WHERE notes.noteid=? GROUP BY notes.noteid", (noteid,))

    return display(query)


@app.route('/archive/<int:year>/<int:month>')
def archive_page(year, month):
    import calendar

    date_begin = '%04d-%02d-01' % (year, month,)
    date_end = '%04d-%02d-%02d' % (year, month, calendar.monthrange(year, month)[1],)
    query = query_db(
        "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name) AS tags FROM notes "
        "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
        "WHERE notes.date BETWEEN ? AND ? GROUP BY notes.noteid", [date_begin, date_end])

    return display(query)


def display(query):
    if len(query) > 0:
        notes = []
        previous_date = query[0]['date']
    else:
        notes = None
        previous_date = None

    for note in query:
        if note['tags'] is not None:
            note['tags'] = note['tags'].split(",")

        note['date'] = time.strftime("%d.%m.%Y", time.strptime(note['date'], "%Y-%m-%d"))
        if len(notes) == 0 or previous_date != note['date']:
            notes.append([note])
            previous_date = note['date']
        else:
            notes[-1].append(note)

    if len(query) > 0:
        return render_template('index.html', notes=notes)
    else:
        return render_template('index.html', notes=notes), 404


@app.route('/note/<int:noteid>/<action>', defaults={'csrf_token': None})
@app.route('/note/<int:noteid>/<action>/confirm/<csrf_token>')
def delete_note_page(noteid, action, csrf_token):
    allowed_actions = ('edit', 'delete',)

    if csrf_token is None:
        if is_admin() and action in allowed_actions:
            # CSRF protection
            csrf_token = get_csrf_token()

            if action == 'delete':
                return render_template('manage-notes.html', action=action, noteid=noteid, csrf_token=csrf_token)
            elif action == 'edit':
                query = query_db(
                    "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name, ',') AS tags FROM notes "
                    "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) "
                    "LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
                    "WHERE notes.noteid=? GROUP BY notes.noteid", [noteid], one=True)

                if query is None:
                    return render_template('error.html', type='note-not-found')

                query['tags'] = ', '.join(query['tags'].split(','))

                return render_template('admin.html', note=query, csrf_token=csrf_token)
        else:
            return abort(401)
    else:
        if is_admin() and action in allowed_actions and check_csrf_token(csrf_token):
            if action == 'delete':
                query_db("DELETE FROM notetags WHERE noteid=?", [noteid])
                query_db("DELETE FROM notes WHERE noteid=?", [noteid])
                g.db_connection.commit()

                return redirect(url_for('index_page'))
            elif action == 'edit':
                return 'To be implemented...'
        else:
            return abort(401)


@app.route('/login', defaults={'status': None})
@app.route('/login/<status>', methods=['GET', 'POST'])
def login_page(status):
    if is_admin():
        return redirect(url_for('admin_page'))

    if status == 'submit':
        admin_credentials_result = query_db(
            "SELECT key, value FROM settings WHERE key=? OR key=?", ('admin_password', 'admin_username',))
        admin_username = None
        admin_password = None

        for ac in admin_credentials_result:
            if ac['key'] == 'admin_password':
                admin_password = ac['value']
            else:
                admin_username = ac['value']

        # check_password_hash(admin_password, request.form['passwd']): # secure version
        if request.form['username'] == admin_username and admin_password == request.form['passwd']:
            session['loggedin'] = request.form['username']
            return redirect(url_for('admin_page'))
        else:
            return redirect(url_for('login_page', status='failed'))
    elif status == 'failed':
        return render_template('login.html', status='failed'), 401
    else:
        return render_template('login.html', status='login')


@app.route('/logout')
def logout_page():
    session.clear()

    return redirect(url_for('index_page'))


@app.route('/admin')
def admin_page():
    if is_admin():
        csrf_token = get_csrf_token()
        return render_template('admin.html', note=None, csrf_token=csrf_token)
    else:
        return redirect(url_for('login_page'))


@app.route('/admin/<action>', methods=['POST'])
def admin_action_page(action):
    if is_admin() and check_csrf_token(request.form['csrf_token']) and \
                    request.form['content'] is not None and request.form['tags'] is not None:
        if action == 'edit':
            if request.form['noteid'] is not None:
                query_db("UPDATE notes SET text=? WHERE noteid=?", [request.form['content'], request.form['noteid']])
                note_id = int(request.form['noteid'])
            else:
                return abort(400)
        elif action == 'post':
            query_db("INSERT INTO notes (date, text) VALUES (?, ?)",
                     [time.strftime("%Y-%m-%d"), request.form['content']])

            note_id = g.db_cursor.lastrowid
        else:
            return abort(400)

        tags = set([tag.strip() for tag in request.form['tags'].split(',')])

        if len(tags) > 0:
            query = query_db("SELECT tagid, name FROM tags WHERE LOWER(name) IN (%s)" % (",".join("?" for i in tags)),
                             [tag.lower() for tag in tags])

            # IDs of known tags
            tag_ids = [row['tagid'] for row in query]

            # Find new tags
            tags_to_add = []
            found = False
            for tag in tags:
                for row in query:
                    if row['name'].lower() == tag.lower():
                        found = True
                        break
                if not found:
                    tags_to_add.append(tag)
                else:
                    found = False

            if len(tags_to_add) > 0:
                query_db("INSERT INTO tags (name) VALUES (%s)" % ('),('.join('?' for i in tags_to_add)),
                         tags_to_add)

                # Get key IDs
                last_id = g.db_cursor.lastrowid
                row_count = g.db_cursor.rowcount
                tag_ids.extend(range(last_id - row_count + 1, last_id + 1))

            # When we are editing we need to make sure we do not insert redundant data
            if action == 'edit':
                query = query_db("SELECT tagid FROM notetags WHERE noteid=?", [note_id])
                existing_tags = [tag['tagid'] for tag in query]
                tags_to_delete = subtract_lists(existing_tags, tag_ids)
                tag_ids = subtract_lists(tag_ids, existing_tags)

                # Delete the old tags
                sql_arguments = [note_id]
                sql_arguments.extend(tags_to_delete)

                query_db("DELETE FROM notetags WHERE noteid=? AND tagid IN (%s)" % (
                    ','.join('?' for i in tags_to_delete)), sql_arguments)

            if len(tag_ids) > 0:
                query_db("INSERT INTO notetags (tagid, noteid) VALUES %s" % (','.join('(?,?)' for i in tag_ids)),
                         [(tag_ids[int(i / 2)] if i % 2 == 0 else note_id) for i in range(0, len(tag_ids) * 2)])

        g.db_connection.commit()

        return redirect(url_for('index_page'))
    else:
        return render_template('login.html', status='failed'), 401


# Static pages
@app.route('/imprint')
def imprint_page():
    return render_template('imprint.html')


@app.route('/about')
def about_page():
    return render_template('about.html')


def is_admin():
    return 'loggedin' in session


def check_csrf_token(request_token):
    token = session.get('_csrf_token', None)
    return token is not None and token == request_token


def get_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid4()).split("-")[-1]
    return session['_csrf_token']


def get_db():
    # SQL connection
    if not hasattr(g, 'db_connection'):
        g.db_connection = connect_db(app.config['DATABASE'], ["PRAGMA foreign_keys = ON"])
        g.db_cursor = g.db_connection.cursor()

    return g.db_cursor


def query_db(query, args=(), one=False):
    cursor = get_db()
    cursor.execute(query, args)
    rv = [dict((cursor.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cursor.fetchall()]
    return (rv[0] if len(rv) > 0 else []) if one else rv


# def connect_db(database, init_arguments=None):
#    sql_connection = sql.connect(database='notes',
#                                 user='notes',
#                                 password='notes',
#                                 host='/var/run/postgresql')
#    if init_arguments is not None:
#        for arg in init_arguments:
#            sql_connection.execute(arg)
#    return sql_connection

def connect_db(database, init_arguments=None):
    sql_connection = sql.connect(database)
    if init_arguments is not None:
        for arg in init_arguments:
            sql_connection.execute(arg)
    return sql_connection


def subtract_lists(left, right):
    s = set(right)
    return [x for x in left if x not in s]


@app.teardown_appcontext
def teardown_appcontext(exception):
    if hasattr(g, 'db_connection'):
        g.db_connection.close()


@app.before_request
def before_request():
    # Time object for template
    app.jinja_env.globals['current_time'] = time


# Run it as standalone server
if __name__ == '__main__':
    app.run(debug=False)
