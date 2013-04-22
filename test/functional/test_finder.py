#!/usr/bin/env python
# vim: fileencoding=utf8:et:sta:ai:sw=4:ts=4:sts=4

import Cookie
import sys
import unittest
import urllib
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import pathfinder


#
# mocking the web (http://is.gd/gv1kh6)
#
def fake_wsgi_request(finder, method, path, request_headers=None, body=""):
    environ = {
        "REQUEST_METHOD": method.upper(),
        "PATH_INFO": path,
        "wsgi.input": StringIO(body),
    }
    if isinstance(request_headers, dict):
        request_headers = request_headers.items()

    for key, value in (request_headers or []):
        key = "HTTP_%s" % (key.replace("-", "_").upper(),)
        if key in environ:
            environ[key] += ',' + value
        else:
            environ[key] = value

    response = {}
    def start_response(status, response_headers):
        code, status_text = status.split(" ", 1)
        response['code'] = int(code)
        response['status'] = status_text
        response['headers'] = response_headers
        # pathfinder doesn't use the write() callable, so we can skip
        # implementing that here

    result = finder.wsgi(environ, start_response)
    response['body'] = "".join(result)
    return response


def fake_gevent_http_request(finder, method, path,
        request_headers=None, body=""):
    request = FakeGeventHTTPRequest(method, path, request_headers or {}, body)
    finder.gevent_http_handle(request)
    return request._response


class FakeGeventHTTPRequest(object):
    def __init__(self, method, path, headers, body):
        # input/request-oriented
        self.typestr = method.upper()
        self.uri = "http://example.com" + path
        if isinstance(headers, dict): headers = headers.items()
        self._headers = headers
        self.input_buffer = StringIO(body)
        self.remote_host = "127.0.0.1"
        self.remote_port = 56789
        self.major = 1
        self.minor = 1
        self.version = (1, 1)

        # output/response-oriented
        self._output_headers = []
        self._response = None

    def get_input_headers(self):
        return self._headers[:]

    def add_output_header(self, name, value):
        self._output_headers.append((name, value))

    def send_reply(self, code, status_text, body):
        self._response = {
            'code': code,
            'status': status_text,
            'headers': self._output_headers,
            'body': body,
        }


class FinderTests(object):
    def assertResponseCode(self, code,
            finder, method, path, headers=None, body=""):
        response = self.fake_request(finder, method, path, headers, body)
        self.assertIsNotNone(response, "no response was generated at all!")
        self.assertEqual(response['code'], code)

    def handler_ok(self, request):
        return pathfinder.Response("OK!", headers={'content-length': 3})

    def test_good_request(self):
        finder = pathfinder.Finder([
            (r"^/foobar$", {"GET": self.handler_ok}),
        ])
        self.assertResponseCode(200, finder, "GET", "/foobar")

    def test_404_by_method(self):
        finder = pathfinder.Finder([
            (r"^/foobar$", {"GET": self.handler_ok}),
        ])
        self.assertResponseCode(404, finder, "POST", "/foobar")

    def test_404_by_path(self):
        finder = pathfinder.Finder([
            (r"^/foo$", {"GET": self.handler_ok}),
        ])
        self.assertResponseCode(404, finder, "GET", "/bar")

    def test_querystring_params(self):
        d = {}
        def handler(request):
            d.update(request.query_params)
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", {"GET": handler}),
        ])
        self.assertResponseCode(200, finder, "GET", "/foo?a=1&b=2")
        self.assertEqual(d, {'a': '1', 'b': '2'})

    def test_post_body_params(self):
        d = {}
        def handler(request):
            print "params:", request.body_params
            d.update(request.body_params)
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", {"POST": handler}),
        ])
        req_body = urllib.urlencode({'a': 1, 'b': 2})
        self.assertResponseCode(200, finder, "POST", "/foo",
                headers={'content-type': 'application/x-www-form-urlencoded'},
                body=req_body)
        self.assertEqual(d, {'a': '1', 'b': '2'})

    def test_no_body_params_on_GET(self):
        d = {}
        def handler(request):
            print "params:", request.body_params
            d.update(request.body_params)
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", {"GET": handler}),
        ])
        req_body = urllib.urlencode({'a': 1, 'b': 2})
        self.assertResponseCode(200, finder, "GET", "/foo",
                headers={'content-type': 'application/x-www-form-urlencoded'},
                body=req_body)
        self.assertEqual(d, {})

    def test_no_body_params_without_right_content_type(self):
        d = {}
        def handler(request):
            print "params:", request.body_params
            d.update(request.body_params)
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", {"POST": handler}),
        ])
        req_body = urllib.urlencode({'a': 1, 'b': 2})
        self.assertResponseCode(200, finder, "POST", "/foo", body=req_body)
        self.assertEqual(d, {})

    def test_raising_produces_500(self):
        def handler(request):
            raise RuntimeError("WAT")
        finder = pathfinder.Finder([
            (r"^/foo$", {"GET": handler}),
        ])
        self.assertResponseCode(500, finder, "GET", "/foo")

    def test_method_is_accurate(self):
        m = [None]
        def handler(request):
            m[0] = request.method
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", handler),
        ])
        self.assertResponseCode(200, finder, "GET", "/foo")
        self.assertEqual(m[0], "GET")
        self.assertResponseCode(200, finder, "POST", "/foo")
        self.assertEqual(m[0], "POST")
        self.assertResponseCode(200, finder, "PUT", "/foo")
        self.assertEqual(m[0], "PUT")

    def test_path_is_accurate(self):
        m = [None]
        def handler(request):
            m[0] = request.path
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/\w+$", {"GET": handler}),
        ])
        self.assertResponseCode(200, finder, "GET", "/foo")
        self.assertEqual(m[0], "/foo")
        self.assertResponseCode(200, finder, "GET", "/bar")
        self.assertEqual(m[0], "/bar")
        self.assertResponseCode(200, finder, "GET", "/baz")
        self.assertEqual(m[0], "/baz")

    def test_headers(self):
        h = {'one': '1', 'two': '2', 'three': '3'}
        m = [None]
        def handler(request):
            m[0] = dict(request.headers)
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", {"GET": handler}),
        ])
        self.assertResponseCode(200, finder, "GET", "/foo", headers=h)
        self.assertEqual(m[0], h)

    def test_cookies(self):
        c = {'x': '10', 'y': '20', 'z': '30'}
        sc = Cookie.SimpleCookie(c)
        ch = [('Cookie', m.output(header='')[1:]) for m in sc.values()]
        m = [None]
        def handler(request):
            m[0] = dict((k, v.value) for k, v in request.cookies.items())
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", {"GET": handler}),
        ])
        self.assertResponseCode(200, finder, "GET", "/foo", headers=ch)
        self.assertEqual(m[0], c)

    def test_body_read(self):
        body = "this is a test"
        m = []
        n = [False]
        def handler(request):
            m.append(request.read(4))
            m.append(request.read(3))
            m.append(request.read(2))
            m.append(request.read(5))
            if not request.read():
                n[0] = True
            return "OK!"
        finder = pathfinder.Finder([
            (r"^/foo$", {"GET": handler}),
        ])
        self.assertResponseCode(200, finder, "GET", "/foo", body=body)


class FinderOnGeventHTTPTests(FinderTests, unittest.TestCase):
    fake_request = staticmethod(fake_gevent_http_request)


class FinderOnWSGITests(FinderTests, unittest.TestCase):
    fake_request = staticmethod(fake_wsgi_request)


class SubFinderTests(object):
    def assertResponseCode(self, code,
            finder, method, path, headers=None, body=""):
        response = self.fake_request(finder, method, path, headers, body)
        self.assertIsNotNone(response, "no response was generated at all!")
        self.assertEqual(response['code'], code)

    def test_traverses_down(self):
        def handler(request):
            return "OK!"

        subf = pathfinder.Finder([
            (r"/bar$", {"GET": handler}),
        ])
        finder = pathfinder.Finder([
            (r"^/foo(?=/)", {"GET": subf}),
        ])

        self.assertResponseCode(200, finder, "GET", "/foo/bar")

    def test_404_on_subfinder_miss(self):
        subf = pathfinder.Finder([])
        finder = pathfinder.Finder([
            (r"^/foo(?=/)", {"GET": subf}),
        ])

        self.assertResponseCode(404, finder, "GET", "/foo/bar")

    def test_404_handler_on_inner_finder(self):
        l = []

        class FourOhFourFinder(pathfinder.Finder):
            def on_404(self, request):
                l.append(None)
                return pathfinder.Response("Four Oh Four", code=200)

        subf = FourOhFourFinder([])
        finder = pathfinder.Finder([
            (r"^/foo(?=/)", {"GET": subf}),
        ])

        self.assertResponseCode(200, finder, "GET", "/foo/bar")
        self.assertEqual(l, [None])

    def test_500_handler_on_inner_finder(self):
        l = []

        class FiveHundredFinder(pathfinder.Finder):
            def on_500(self, request, exc_triple):
                l.append(2)
                return pathfinder.Response("Five Hundred", code=200)

        def handler(request):
            l.append(1)
            raise RuntimeError("ZOMG")

        subf = FiveHundredFinder([
            (r"/bar$", {"GET": handler}),
        ])
        finder = pathfinder.Finder([
            (r"^/foo(?=/)", {"GET": subf}),
        ])

        self.assertResponseCode(200, finder, "GET", "/foo/bar")
        self.assertEqual(l, [1, 2])

    def test_no_multiple_branch_traversal(self):
        """could have gone either way, but this decision was made

        when a *sub*finder doesn't find a match, we 404 all the way out to the
        response rather than resuming the search in the parent finder
        """
        def handler(request):
            return "OK!"

        subf1 = pathfinder.Finder([])
        subf2 = pathfinder.Finder([
            (r"nicator$", {"GET": handler}),
        ])
        outer = pathfinder.Finder([
            (r"^/", {"GET": subf1}),
            (r"^/frob", {"GET": subf2}),
        ])

        self.assertResponseCode(404, outer, "GET", "/frobnicator")


class SubFinderOnGeventHTTPTests(SubFinderTests, unittest.TestCase):
    fake_request = staticmethod(fake_gevent_http_request)


class SubFinderOnWSGITests(SubFinderTests, unittest.TestCase):
    fake_request = staticmethod(fake_wsgi_request)


if __name__ == '__main__':
    unittest.main()
