import os
import unittest

from flask.ext.testing import TestCase

import notes


class NotesFlaskTest(TestCase):
    render_templates = True

    def create_app(self):
        notes.app.config['DATABASE'] = ':memory:'
        notes.app.config['TESTING'] = True

        return notes.app

    def setUp(self):
        # Import database schema and test data into SQLite
        with open('./schema.sql', 'r') as fp:
            sql = fp.read()
            notes.get_db().executescript(sql)

    def tearDown(self):
        if os.path.isfile(notes.app.config['DATABASE']):
            os.remove(notes.app.config['DATABASE'])

    def test_index(self):
        rv = self.client.get('/')
        self.assert200(rv)

    def test_note(self):
        rv = self.client.get('/note')
        self.assert404(rv)
        rv = self.client.get('/note/1')
        self.assert200(rv)

    def test_tag(self):
        rv = self.client.get('/tag')
        self.assert404(rv)
        rv = self.client.get('/tag/test')
        self.assert404(rv)

    def test_archive(self):
        rv = self.client.get('/archive')
        self.assert404(rv)
        rv = self.client.get('/archive/1984/05')
        self.assert404(rv)
        import datetime
        now = datetime.datetime.now()
        rv = self.client.get('/archive/%04d/%02d' % (now.year, now.month))
        self.assert200(rv)

    def test_login_failed(self):
        rv = self.client.get('/login')
        self.assert200(rv)
        rv = self.client.get('/admin')
        self.assertRedirects(rv, '/login')
        rv = self.client.post('/login/submit', data=dict(username="wrong", passwd="wrong"))
        self.assertRedirects(rv, '/login/failed')
        rv = self.client.get('/login/failed')
        self.assert401(rv)

    def test_login_success_logout(self):
        rv = self.client.get('/login')
        self.assert200(rv)
        rv = self.client.get('/admin')
        self.assertRedirects(rv, '/login')
        rv = self.client.post('/login/submit', data=dict(username="admin", passwd="admin"))
        self.assertRedirects(rv, '/admin')
        rv = self.client.get('/login')
        self.assertRedirects(rv, '/admin')
        rv = self.client.get('/admin')
        self.assert200(rv)
        # Check if login information and CSRF token were set
        with self.client.session_transaction() as session:
            assert session.get('_csrf_token', None) is not None
            assert session.get('loggedin', None) is not None

        # Eventually log out
        rv = self.client.get('/logout')
        self.assertRedirects(rv, '/')

    def test_delete_note_success(self):
        rv = self.client.get('/note/1')
        self.assert200(rv)
        self.client.post('/login/submit', data=dict(username="admin", passwd="admin"))
        rv = self.client.get('/note/1/delete')
        self.assert200(rv)
        with self.client.session_transaction() as session:
            rv = self.client.get('/note/1/delete/confirm/%s' % session.get('_csrf_token'))
            self.assertRedirects(rv, '/')
        rv = self.client.get('/note/1')
        self.assert404(rv)

    def test_delete_note_fail(self):
        rv = self.client.get('/note/1/delete')
        self.assert401(rv)

    def test_csrf_attack(self):
        self.client.post('/login/submit', data=dict(username="admin", passwd="admin"))
        rv = self.client.get('/note/1/delete/confirm/%s' % 'INVALID')
        self.assert401(rv)

    # Temporarily disabled because of Travis-CI
    def test_admin_post_success(self):
        self.client.post('/login/submit', data=dict(username="admin", passwd="admin"), follow_redirects=True)
        with self.client.session_transaction() as session:
            rv = self.client.post('/admin/post', data=dict(text="Test note", tags="Test, T3st",
                                                           csrf_token=session.get('_csrf_token', None)))
            self.assertRedirects(rv, '/')
        rv = self.client.get('/')
        self.assert200(rv)
        rv = self.client.get('/note/2')
        self.assert200(rv)
        assert b"Test note" in rv.data
        rv = self.client.get('/tag/test')
        self.assert200(rv)
        rv = self.client.get('/tag/t3st')
        self.assert200(rv)

    def test_admin_invalid_action(self):
        self.client.post('/login/submit', data=dict(username="admin", passwd="admin"), follow_redirects=True)
        with self.client.session_transaction() as session:
            rv = self.client.post('/admin/invalid', data=dict(text="Test note", tags="Test, T3st",
                                                              csrf_token=session.get('_csrf_token', None)))
            self.assert400(rv)

    def test_admin_post_fail(self):
        rv = self.client.post('/admin/post', data=dict(text="Test note", tags="Test, T3st", csrf_token='INVALID'))
        self.assert401(rv)
        rv = self.client.get('/note/2')
        self.assert404(rv)

    def test_note_edit(self):
        rv = self.client.get('/note/1/edit')
        self.assert401(rv)
        self.client.post('/login/submit', data=dict(username="admin", passwd="admin"), follow_redirects=True)
        rv = self.client.get('/note/10/edit')
        self.assert404(rv)
        rv = self.client.get('/note/10/invalid')
        self.assert400(rv)
        self.assert_template_used('error.html')
        rv = self.client.get('/note/1/edit')
        self.assert200(rv)
        with self.client.session_transaction() as session:
            rv = self.client.post('/admin/edit', data=dict(text="Edited test note", tags="Edit, Test, T3st",
                                                           csrf_token=session.get('_csrf_token', None)))
            self.assert400(rv)
            rv = self.client.post('/admin/edit', data=dict(text="Edited test note", tags="Edit, Test, T3st",
                                                           csrf_token='INVALID'))
            self.assert401(rv)
            rv = self.client.get('/note/1/edit/confirm/%s' % session.get('_csrf_token'))
            self.assert400(rv)
            rv = self.client.post('/admin/edit', data=dict(text="Edited test note", tags="Edit, Test, T3st",
                                                           csrf_token=session.get('_csrf_token', None)))
            self.assert400(rv)
            rv = self.client.post('/admin/edit', data=dict(text="Edited test note", tags="Edit, Test, T3st",
                                                           csrf_token=session.get('_csrf_token', None), noteid=1))
            self.assertRedirects(rv, '/')
        rv = self.client.get('/note/1')
        self.assert200(rv)
        assert b"Edited test note" in rv.data

    def test_statis_pages(self):
        rv = self.client.get('/imprint')
        self.assert200(rv)
        rv = self.client.get('/about')
        self.assert200(rv)


class UtilTests(unittest.TestCase):
    def test_subtract_lists(self):
        r = notes.subtract_lists([1, 9, 2, 3, 4], [7, 2, 3, 1, 3])
        assert r[0] == 9 and r[1] == 4


if __name__ == '__main__':
    unittest.main()
