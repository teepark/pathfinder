#!/usr/bin/env python
# vim: fileencoding=utf8:et:sta:ai:sw=4:ts=4:sts=4

import os
import sys

import gevent.http
import gevent.wsgi
import pathfinder


#
# Simple handlers
#
def hello_world(request):
    return pathfinder.Response("Hello, World!")

def hello_name(request, name):
    # just returning a string works, pathfinder wraps it in a Response
    return "hello, %s!" % name

def goodbye_name(request, name):
    return "goodbye, %s!" % name


#
# Delegating to sub url-schemes
#
def pass_it_down(request):
    # just by returning (finder_instance, request_instance),
    # the next finder will be used to continue matching against the path

    # this also allows for modifying the request instance on the way down
    return sub_finder, request


urls = [
    # regex-based url routing,
    # with groups and named groups mapping to *args and **kwargs respectively
    (r"^/helloworld/$", hello_world, ["GET"]),
    (r"^/hello/(\w+)/$", hello_name, ["GET"]),
    (r"^/goodbye/(?P<name>\w+)/$", goodbye_name, ["GET"]),

    # delegating to sub-finders - note the lack of $ in the regex
    (r"^/sub/", pass_it_down, ["GET"]),
]

sub_urls = [
    # regexes here will be compared against the *rest* of the url,
    # everything but the portion that matched in the parent finder
    (r"hello/$", hello_world, ["GET"]),
]

sub_finder = pathfinder.Finder(sub_urls)

finder = pathfinder.Finder(urls)


#
# SERVER INTERFACE
#
# finder.gevent_http_handle works as the 'handle' argument to the
# gevent.http server
#
# maybe at some point in the future, finder.wsgi could be a valid wsgi app
#

def main(environ, argv):
    if '--wsgi' in argv:
        server = gevent.wsgi.WSGIServer(('127.0.0.1', 8070), finder.wsgi)
    else:
        server = gevent.http.HTTPServer(('127.0.0.1', 8070),
                finder.gevent_http_handle)
    server.serve_forever()


if __name__ == '__main__':
    exit(main(os.environ, sys.argv))
