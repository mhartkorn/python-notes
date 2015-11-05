from uuid import uuid4
from flask import session, g
import sqlite3 as sql


def is_admin():
    return 'loggedin' in session


def check_csrf_token(request_token):
    token = session.pop('_csrf_token', None)
    return token is not None and token == request_token


def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid4()).split("-")[-1]
    return session['_csrf_token']


def get_db(database):
    # SQL connection
    if not hasattr(g, 'db_connection'):
        g.db_connection = connect_db(database, ["PRAGMA foreign_keys = ON"])
        g.db_cursor = g.db_connection.cursor()

    return g.db_cursor


def query_db(query, args=(), one=False):
    cursor = get_db(g.database)
    cursor.execute(query, args)
    rv = [dict((cursor.description[idx][0], value)
        for idx, value in enumerate(row)) for row in cursor.fetchall()]
    return (rv[0] if len(rv) > 0 else []) if one else rv


#def connect_db(database, init_arguments=None):
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
