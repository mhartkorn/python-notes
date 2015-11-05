import notes
import unittest


class FlaskrTestCase(unittest.TestCase):
    def setUp(self):
        notes.app.config['DATABASE'] = './database.sqlite'
        notes.app.config['TESTING'] = True
        self.app = notes.app.test_client()

    def tearDown(self):
        pass

    def test_tag(self):
        rv = self.app.get('/tag')
        assert rv.status_code == 404
        rv = self.app.get('/tag/test')
        assert rv.status_code == 200

    def test_login(self):
        rv = self.app.get('/login')
        assert rv.status_code == 200
        rv = self.app.post('/login/submit', data=dict(username="wrong", passwd="wrong"), follow_redirects=True)
        assert rv.status_code == 401
        rv = self.app.post('/login/submit', data=dict(username="admin", passwd="admin"), follow_redirects=True)
        assert rv.status_code == 200
        rv = self.app.get('/logout', follow_redirects=True)
        assert rv.status_code == 200


if __name__ == '__main__':
    unittest.main()
