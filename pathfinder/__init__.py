"""pathfinder -- simple modular HTTP request routing

Copyright 2012-2013 Jawbone Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
# vim: fileencoding=utf8:et:sta:ai:sw=4:ts=4:sts=4

from __future__ import absolute_import

import BaseHTTPServer
import collections
import Cookie
import logging
import os
import re
import sys
import traceback
import urlparse
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from . import multipart, util

try:
    import gevent.core
except ImportError:
    gevent = None


__all__ = ["ALL_METHODS", "Finder", "Request", "Response"]

log = logging.getLogger("pathfinder")

HTTP_CODE_DATA = BaseHTTPServer.BaseHTTPRequestHandler.responses

ALL_METHODS = ["OPTIONS", "GET", "HEAD", "POST",
               "PUT", "DELETE", "TRACE", "CONNECT"]


class Finder(object):
    """The router of HTTP requests

    Create it with a list of three-tuples for route matching. the first item
    should be a regular expression string, the second a handler (more on this
    in a bit), and the third a list of strings of HTTP methods (the special
    value pathfinder.ALL_METHODS is a list of all the methods in rfc 2616).

    Each request will have the path checked against all regular expressions
    with the correct HTTP method associated, and the handler of the first
    match will be used to handle the request.

    Handlers can be other instances of Finder, in which case the request will
    be handed off to it (the portion of the path that matched the regular
    expression will be stripped before checks against the sub-finder's regexes
    commence).

    Handlers can also be functions in which case they will be called with the
    request as the first argument, and any un-named and named capture groups
    from the regex as further positional and keyword arguments, respectively.
    """
    def __init__(self, urlmap):
        self._map = {}

        for regex, mapping in urlmap:
            regex = re.compile(regex)
            if isinstance(mapping, Finder) or hasattr(mapping, '__call__'):
                for verb in ALL_METHODS:
                    self._map.setdefault(verb.lower(), []).append(
                            (regex, mapping))
            else:
                for verb, handler in mapping.iteritems():
                    self._map.setdefault(verb.lower(), []).append(
                            (regex, handler))

    def _resolve(self, method, path):
        for regex, handler in self._map.get(method.lower(), ()):
            match = regex.match(path)
            if match:
                if isinstance(handler, Finder):
                    remaining = path[:match.start()] + path[match.end():]
                    return handler, (), {}, remaining
                kwargs = match.groupdict()
                args = () if kwargs else match.groups()
                return handler, args, kwargs, ""
        return None, (), {}, ""

    def _handle(self, path, request):
        method = request.method

        handler, args, kwargs, remaining = self._resolve(method, path)
        if not handler:
            # no routes matched, bail with 404
            return self._on_404(request)

        if isinstance(handler, Finder):
            return handler._handle(remaining, request)

        try:
            response = handler(request, *args, **kwargs)
        except Exception:
            triple = sys.exc_info()
            log.error("handler raised:\n%s" %
                    ''.join(traceback.format_exception(*triple)))
            return self._on_500(request, triple)

        # enable string return values
        if isinstance(response, str):
            return Response(response,
                    headers=[("Content-Length", str(len(response)))])

        # allow unicode responses in the same way, encoding to UTF-8
        if isinstance(response, unicode):
            try:
                response = response.encode('utf8')
            except UnicodeEncodeError:
                log.error(
                    "unicode returned from handler can not be encoded UTF-8")
                return self._on_500(request, sys.exc_info())
            return Response(response, headers=[
                    ('Content-Length', str(len(response))),
                    ('Content-Encoding', 'UTF-8')])

        # bail out on any other return type
        if not isinstance(response, Response):
            log.error("handler didn't return a Response but %r" % response)
            # this is dumb, but how *should* one get an exception triple?
            try:
                raise TypeError("expected a Response, got %r" % response)
            except TypeError:
                return self._on_500(request, sys.exc_info())

        return response

    if gevent:
        def gevent_http_handle(self, grequest):
            """Use this method as the handler for a gevent.http.HTTPServer

            gevent.http (which disappears in gevent 1.0) has a special API, and
            this function translates that to pathfinder.
            """
            path = urlparse.urlsplit(grequest.uri).path
            request = Request(grequest.typestr, grequest.uri,
                    grequest.get_input_headers(), grequest.input_buffer)
            request._request = grequest

            response = self._handle(request.path, request)
            if response is NoResponse:
                return

            try:
                response.finalize(request)
            except Exception:
                response = self._on_500(request, sys.exc_info())

            status_text = HTTP_CODE_DATA[response.code][0]
            try:
                for name, value in response.headers.iteritems():
                    grequest.add_output_header(name, value)
                grequest.send_reply(
                        response.code, status_text, response.content)
            except gevent.core.HttpRequestDeleted:
                pass

    def wsgi(self, environ, start_response):
        """Use this as a WSGI application/callable

        This method is a valid WSGI application which translates the WSGI
        interface to pathfinder.
        """
        headers = []
        for key, value in environ.iteritems():
            if not key.startswith("HTTP_"):
                continue
            key = key[5:].replace('_', '-').lower()
            for val in value.split(","):
                headers.append((key, val))

        request = Request(environ['REQUEST_METHOD'],
                environ['PATH_INFO'], headers, environ['wsgi.input'])
        request._request = environ

        response = self._handle(request.path, request)
        if response is NoResponse:
            # this WSGI handler doesn't support NoResponse
            response = Response("Server Error", code=500)

        try:
            response.finalize(request)
        except Exception:
            response = self._on_500(request, sys.exc_info())

        status_text = HTTP_CODE_DATA[response.code][0]
        start_response("%d %s" % (response.code, status_text),
                response.headers.items())

        if not hasattr(response.content, "__iter__"):
            return [response.content]
        return response.content

    def _on_404(self, request):
        log.info("404 looking for %s" % request.path)
        try:
            response = self.on_404(request)
        except Exception:
            triple = sys.exc_info()
            log.error("on_404 handler exception:\n%s" %
                    ''.join(traceback.format_exception(*triple)))
            return self._on_500(request, triple)

        if isinstance(response, Response) or response is NoResponse:
            return response

        return Response("Not Found", code=404, headers=[
                ('Content-Length', '9')
                ('Content-Type', 'text/plain')])

    def _on_500(self, request, triple):
        try:
            response = self.on_500(request, triple)
        except Exception:
            triple = sys.exc_info()
            log.critical("on_500 handler exception:\n%s" %
                    ''.join(traceback.format_exception(*triple)))
            return Finder.on_500(request, triple)

        if isinstance(response, Response) or response is NoResponse:
            return response

        log.critical(
            "on_500 handler didn't return a Response, instead: %r" % response)

        return Response("Server Error", code=500, headers=[
                ('Content-Length', '12'),
                ('Content-Type', 'text/plain')])

    #
    # Subclass and override these methods to gain control of response
    # generation in those cases where regular handlers can't do it
    # (either because one couldn't be found, or because one raised)
    #
    def on_404(self, request):
        """Overridable stub for what to do on 404

        This method **must** return an instance of :class:`Response`
        (``NoResponse`` is also an option on gevent.http). It is called to
        generate the response when no matching handler could be found.
        """
        return Response("", code=404, headers=[("Content-Length", "0")])

    def on_500(self, request, exc_triple):
        """Overridable stub for what to do on 404

        This method **must** return an instance of :class:`Response`
        (``NoResponse`` is also an option on gevent.http). It is called to
        generate the response in error conditions such as a handler raising.
        """
        log.error("error from handler on %s:\n%s" % (
            request.path,
            ''.join(traceback.format_exception(*exc_triple))))
        return Response("", code=500, headers=[("Content-Length", "0")])


class Request(object):
    """A data object with the HTTP request information

    An instance of this is created by pathfinder and passed as the first
    argument to handler functions.
    """
    CHUNKSIZE = 8192

    def __init__(self, method, path, headers, bodyfile):
        self._bodyfile = bodyfile
        self._bodystring = None
        self._post = None
        self._started_reading = False
        self._rbuf = StringIO()

        parsed = urlparse.urlsplit(path)

        self.method = method.upper()
        "The HTTP method of the request"

        self.path = parsed.path
        "The full URL path"

        self.query_string = parsed.query
        "the raw query string"

        self.query_params = util.OrderedMultiDict(urlparse.parse_qsl(parsed.query))
        "decoded parameters from the querystring"

        headers, ctopts, cdopts = _parse_headers(headers)
        self._ctopts = ctopts
        self._cdopts = cdopts

        self.headers = headers
        "Request headers"

        self.cookies = _parse_cookies(self.headers.getall('cookie'))
        "Cookies in the request"

        self.parts = self._parse_parts()
        "Sections of a multipart request body"

    def _parse_parts(self):
        if self.headers.get('content-type', '') == 'multipart/form-data':
            boundary = self.content_type_opts.get('boundary', '')
            clength = int(self.headers.get('content-length', -1))
            charset = self.content_type_opts.get('charset', 'utf8')
            parser = multipart.MultipartParser(self, boundary, clength,
                    disk_limit=2**32, mem_limit=2**28, memfile_limit=2**28,
                    charset=charset)
            for part in parser:
                headers, ctopts, cdopts = _parse_headers(part.headerlist)
                yield multipartpart(
                        headers, part.size, part.name, part.filename,
                        part.charset, ctopts, cdopts, part.value)

    @property
    def body_params(self):
        "url-encoded parameters from a POST or PUT request body"
        if self._post is None:
            if self._started_reading:
                raise Exception("already consuming request body")

            self._post = util.OrderedMultiDict()

            ctype = self.headers.get('content-type', None)
            if ctype and self.method in ('POST', 'PUT'):
                ctype, opts = multipart.parse_options_header(ctype)
                if ctype in ('application/x-www-form-urlencoded',
                        'application/x-form-url-encoded'):
                    self._post.update(urlparse.parse_qsl(self.read()))

        return self._post

    @property
    def content_type_opts(self):
        "options from the Content-Type header"
        return self._ctopts

    @property
    def content_disposition_opts(self):
        "options from the Content-Disposition header"
        return self._cdopts

    @property
    def params(self):
        "parameters from the querystring and request body combined"
        params = self.query_params.copy()
        params.update(self.body_params)
        return params

    def read(self, size=None):
        "Read some or all of the request body directly"
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
    "The content-type that will be assigned if none is provided"

    def __init__(self, content, code=200, headers=None):
        self.content = content
        "the response string, or iterable of strings"

        self.code = code
        "integer HTTP status code (defaults to 200)"

        self.headers = util.CaseInsensitiveOrderedMultiDict(headers or {})
        "dictionary of headers for the response"

        self.cookies = Cookie.SimpleCookie()
        "Cookies to send in the response"

    def finalize(self, request):
        """finalizer for responses

        override this in a subclass to add behavior for after the handler is
        finished (and remember to call the super)
        """
        # place output headers into the set-cookie header(s)
        self.headers.update(('Set-Cookie', m.output(header='')[1:])
                for m in self.cookies.values())

        # add a content-type
        if self.default_content_type and 'content-type' not in self.headers:
            self.headers['Content-Type'] = self.default_content_type


def _parse_headers(keyvals):
    headers = util.CaseInsensitiveOrderedMultiDict()
    ctopts, cdopts = {}, {}
    for key, val in keyvals:
        lkey = key.lower()
        if lkey == 'content-type':
            val, ctopts = multipart.parse_options_header(val)
        elif lkey == 'content-disposition':
            val, cdopts = multipart.parse_options_header(val)
        headers[key] = val
    return headers, ctopts, cdopts


def _parse_cookies(cookie_headers):
    cookies = Cookie.SimpleCookie()
    for value in cookie_headers:
        cookies.load(value)
    return cookies


multipartpart = collections.namedtuple('multipartpart',
        ('headers', 'size', 'name', 'filename', 'charset',
            'content_type_opts', 'content_disposition_opts', 'body'))


NoResponse = object()
