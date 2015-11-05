#!/usr/bin/env python

from flask import Flask, g, render_template, request, redirect, url_for, session, abort
from werkzeug.security import check_password_hash

from functions import query_db, is_admin, generate_csrf_token, check_csrf_token, subtract_lists

import time
import urllib

DATABASE = './database.sqlite'

app = Flask('notes')
app.secret_key = '6>PmD$~h|&/5f1\x04kH^eqn:YQG~c(EZiRP{=uKTFgDu9pz^>\x01D1'


@app.route('/')
def index_page():
    query = query_db(
        "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name) AS tags FROM notes "
        "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
        "WHERE notes.date >= DATE((SELECT value FROM settings WHERE key='lastday')) GROUP BY notes.noteid "
        "ORDER BY notes.date DESC, notes.noteid DESC")

    return display(query)


@app.route('/tag/<path:tag>')
def tag_page(tag):
    query = query_db(
        "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name) AS tags FROM notes "
        "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
        "WHERE notes.date >= DATE((SELECT value FROM settings WHERE key='lastday')) AND "
        "notes.noteid IN (SELECT notetags.noteid FROM notetags "
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

    return render_template('index.html', notes=notes)


@app.route('/note/<int:noteid>/<action>', defaults={'csrf_token': None})
@app.route('/note/<int:noteid>/<action>/confirm/<csrf_token>')
def delete_note(noteid, action, csrf_token):
    allowed_actions = ('edit', 'delete',)

    if csrf_token is None:
        if is_admin() and action in allowed_actions:
            # CSRF protection
            csrf_token = generate_csrf_token()

            if action == 'delete':
                return render_template('manage-notes.html', action=action, noteid=noteid, csrf_token=csrf_token)
            elif action == 'edit':
                query = query_db(
                    "SELECT notes.noteid, notes.date, notes.text, GROUP_CONCAT(tags.name, ',') AS tags FROM notes "
                    "LEFT JOIN notetags ON (notetags.noteid=notes.noteid) LEFT JOIN tags ON (tags.tagid=notetags.tagid) "
                    "WHERE notes.noteid=? GROUP BY notes.noteid", [noteid], one=True)

                if query is None:
                    return render_template('error.html', type='note-not-found')

                query['tags'] = ', '.join(query['tags'].split(','))

                return render_template('admin.html', note=query, csrf_token=csrf_token)
        else:
            return abort(400)
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
            return abort(400)


@app.route('/login', defaults={'status': None})
@app.route('/login/<status>', methods=['GET', 'POST'])
def login(status):
    if is_admin():
        return redirect(url_for('admin'))

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
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('login', status='failed'))
    elif status == 'failed':
        return render_template('login.html', status='failed'), 401
    else:
        return render_template('login.html', status='login')


@app.route('/logout')
def logout():
    session.clear()

    return redirect(url_for('index_page'))


@app.route('/admin')
def admin():
    if is_admin():
        csrf_token = generate_csrf_token()
        return render_template('admin.html', note=None, csrf_token=csrf_token)
    else:
        return redirect(url_for('login'))


@app.route('/admin/<action>', methods=['POST'])
def admin_action(action):
    if check_csrf_token(request.form['csrf_token']) and \
                    request.form['text'] is not None and request.form['tags'] is not None:
        if action == 'edit':
            if request.form['noteid'] is not None:
                query_db("UPDATE notes SET text=? WHERE noteid=?", [request.form['text'], request.form['noteid']])
                note_id = int(request.form['noteid'])
            else:
                return abort(400)
        elif action == 'post':
            query_db("INSERT INTO notes (date, text) VALUES (?, ?)", [time.strftime("%Y-%m-%d"), request.form['text']])

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


# Static pages
@app.route('/imprint')
def imprint_page():
    return render_template('imprint.html')


@app.route('/about')
def about_page():
    return render_template('about.html')


@app.teardown_appcontext
def teardown_appcontext(exception):
    if hasattr(g, 'db_connection'):
        g.db_connection.close()


@app.before_request
def before_request():
    g.database = DATABASE

    # Time object for template
    app.jinja_env.globals['current_time'] = time


# Run it as standalone server
if __name__ == '__main__':
    app.run(debug=True)
