# vim: fileencoding=utf8:et:sta:ai:sw=4:ts=4:sts=4
from __future__ import absolute_import

import Cookie
import BaseHTTPServer
import os
import re
import sys
import urlparse
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from . import util

try:
    import gevent.core
except ImportError:
    gevent = None


HTTP_CODE_DATA = BaseHTTPServer.BaseHTTPRequestHandler.responses


class Finder(object):
    def __init__(self, urlmap):
        self._map = {}

        for regex, handler, verbs in urlmap:
            regex = re.compile(regex)
            for verb in verbs:
                self._map.setdefault(verb.lower(), []).append((regex, handler))

    def _resolve(self, method, path):
        for regex, handler in self._map.get(method.lower(), ()):
            match = regex.match(path)
            if match:
                remaining = path[:match.start()] + path[match.end():]
                kwargs = match.groupdict()
                args = not kwargs and match.groups() or ()
                return handler, args, kwargs, remaining
        return None, (), {}, path

    def _handle(self, path, request):
        method = request.method
        fullpath = request.path

        handler, args, kwargs, remaining = self._resolve(method, path)
        if not handler:
            # no routes matched, bail with 404
            return self._on_404(method, fullpath, request)

        try:
            response = handler(request, *args, **kwargs)
        except Exception:
            triple = sys.exc_info()
            return self._on_500(method, fullpath, request, triple)

        # recurse into a sub-finder if it was provided
        if isinstance(response, tuple) and len(response) == 2:
            finder, request = response
            return finder._handle(remaining, request)

        # enable string return values
        if isinstance(response, str):
            return Response(response,
                    headers=[("Content-Length", str(len(response)))])

        # allow unicode responses in the same way, encoding to UTF-8
        if isinstance(response, unicode):
            try:
                response = response.encode('utf8')
            except UnicodeEncodeError:
                return self._on_500(method, fullpath, request, sys.exc_info())
            return Response(response, headers=[
                    ('Content-Length', str(len(response))),
                    ('Content-Encoding', 'UTF-8')])

        # bail out on any other return type
        if not isinstance(response, Response):
            # this is dumb, but how *should* one get an exception triple?
            try:
                raise TypeError("expected a pathfinder.Response")
            except TypeError:
                triple = sys.exc_info()
                return self._on_500(method, fullpath, request, triple)

        return response

    if gevent:
        #
        # Use this method as the handler argument to gevent.http.HTTPServer
        #
        # don't call it, just pass the function object itself
        #
        def gevent_http_handle(self, grequest):
            # anything that isn't specific to gevent.http.HTTPServer should go
            # in _handle above so it can easily be shared with other (WSGI for
            # example) future ports
            path = urlparse.urlsplit(grequest.uri).path
            request = Request(grequest.typestr, path,
                    grequest.get_input_headers(), grequest.input_buffer)

            response = self._handle(path, request)
            response._finalize()

            status_text = HTTP_CODE_DATA[response.code][0]
            try:
                for name, value in response.headers.iteritems():
                    grequest.add_output_header(name, value)
                grequest.send_reply(
                        response.code, status_text, response.content)
            except gevent.core.HttpRequestDeleted:
                pass

    def wsgi(self, environ, start_response):
        headers = [(k[5:].replace('_', '-').lower(), v)
                for k, v in environ.iteritems() if k.startswith("HTTP_")]

        request = Request(environ['REQUEST_METHOD'],
                environ['PATH_INFO'], headers, environ['wsgi.input'])

        response = self._handle(request.path, request)
        response._finalize()

        status_text = HTTP_CODE_DATA[response.code][0]
        start_response("%d %s" % (response.code, status_text),
                response.headers.items())
        return [response.content]

    def _on_404(self, method, path, request):
        response = self.on_404(method, path, request)
        if isinstance(response, Response):
            return response
        return Response("Not Found", code=404, headers=[
                ('Content-Length', '9')
                ('Content-Type', 'text/plain')])

    def _on_500(self, method, path, request, triple):
        response = self.on_500(method, path, request, triple)
        if isinstance(response, Response):
            return response
        return Response("Server Error", code=404, headers=[
                ('Content-Length', '12'),
                ('Content-Type', 'text/plain')])

    #
    # Subclass and override these methods to gain control of response
    # generation in those cases where regular handlers can't do it
    # (either because one couldn't be found, or because one raised)
    #
    def on_404(self, method, path, request):
        return Response("", code=404, headers=[("Content-Length", "0")])

    def on_500(self, method, path, request, exc_triple):
        return Response("", code=500, headers=[("Content-Length", "0")])


class Request(object):
    CHUNKSIZE = 8192

    def __init__(self, method, fullpath, headers, bodyfile):
        self._bodyfile = bodyfile
        self._bodystring = None
        self._post = None
        self._started_reading = False
        self._rbuf = StringIO()

        parsed = urlparse.urlsplit(fullpath)

        self.method = method.upper()
        self.path = parsed.path
        self.query_params = util.OrderedMultiDict(urlparse.parse_qsl(parsed.query))
        self.headers = util.CaseInsensitiveOrderedMultiDict(headers)

        self.cookies = Cookie.SimpleCookie()
        for value in self.headers.getall('cookie'):
            self.cookies.load(value)

    @property
    def body_params(self):
        if self._post is None:
            if self._started_reading:
                raise Exception("already consuming request body")

            self._post = util.OrderedMultiDict()
            if (self.method in ('POST', 'PUT') and
                    self.headers.get('content-type', None) in (
                        'application/x-www-form-urlencoded',
                        'application/x-form-url-encoded')):
                self._post.update(urlparse.parse_qsl(self.read()))

        return self._post

    @property
    def params(self):
        params = self.query_params.copy()
        params.update(self.body_params)
        return params

    def read(self, size=None):
        self._started_reading = True
        csize = self.CHUNKSIZE if size is None else min(self.CHUNKSIZE, size)

        buf = self._rbuf
        buf.seek(0, os.SEEK_END)
        collected = buf.tell()

        while 1:
            if size is not None and collected >= size: # we have enough
                break

            chunk = self._bodyfile.read(csize)
            if not chunk: # EOF
                break

            collected += len(chunk)
            buf.write(chunk)

        # get rid of the old buffer
        everything = buf.getvalue()
        buf.seek(0)
        buf.truncate()

        if size is not None:
            # leave overflow in the buffer
            buf.write(everything[size:])
            return everything[:size]

        return everything


class Response(object):
    default_content_type = "text/html"

    def __init__(self, content, code=200, headers=None):
        self.content = content
        self.code = code
        self.headers = util.CaseInsensitiveOrderedMultiDict(headers or {})

        self.cookies = Cookie.SimpleCookie()

        if 'content-type' not in self.headers:
            self.headers['Content-Type'] = self.default_content_type

    def _finalize(self):
        # place output headers into the set-cookie header(s)
        self.headers.update(('Set-Cookie', m.output(header='')[1:])
                for m in self.cookies.values())


NoResponse = object()
