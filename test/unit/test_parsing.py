#!/usr/bin/env python
# vim: fileencoding=utf8:et:sta:ai:sw=4:ts=4:sts=4

import unittest

import pathfinder.multipart


class HeaderParsingTests(unittest.TestCase):
    def test_option_header_urlencoded_ctype_no_charset(self):
        self.assertEqual(
                pathfinder.multipart.parse_options_header(
                    "application/x-www-form-urlencoded"),
                ('application/x-www-form-urlencoded', {}))
        self.assertEqual(
                pathfinder.multipart.parse_options_header(
                    "application/x-form-url-encoded"),
                ('application/x-form-url-encoded', {}))

    def test_option_header_urlencoded_ctype_with_charset(self):
        self.assertEqual(
                pathfinder.multipart.parse_options_header(
                    "application/x-www-form-urlencoded; charset=UTF8"),
                ('application/x-www-form-urlencoded', {'charset': 'UTF8'}))
        self.assertEqual(
                pathfinder.multipart.parse_options_header(
                    "application/x-form-url-encoded; charset=UTF8"),
                ('application/x-form-url-encoded', {'charset': 'UTF8'}))


if __name__ == '__main__':
    unittest.main()
