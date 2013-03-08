#!/usr/bin/env python
# vim: fileencoding=utf8:et:sta:ai:sw=4:ts=4:sts=4


import unittest

import pathfinder.util


class OMDDictCompat(object):
    #
    # set of tests ensuring dict-like behavior
    #
    def test_len(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(len(d), 3)

    def test_iter(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(sorted(list(d)), ['a', 'b', 'c'])

    def test_contains(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertIn('a', d)
        self.assertNotIn('d', d)

    def test_has_key(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertTrue(d.has_key('b'))
        self.assertTrue(not d.has_key('d'))

    def test_getitem(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertTrue(d['a'], 1)
        self.assertTrue(d['b'], 2)
        self.assertRaises(KeyError, lambda: d['d'])

    def test_setitem(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d['d'] = 4
        self.assertEqual(d['d'], 4)
        self.assertIn('d', d)

        d['a'] = 11
        self.assertEqual(d['a'], 11)

    def test_delitem(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        del d['b']
        self.assertNotIn('b', d)

        def del_d():
            del d['d']
        self.assertRaises(KeyError, del_d)

    def test_clear(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d.clear()
        self.assertFalse(d)
        self.assertEqual(len(d), 0)
        self.assertNotIn('a', d)

    def test_copy(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d2 = d.copy()
        self.assertEqual(d.items(), d2.items())

    def test_independence_of_copies(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d2 = d.copy()
        del d['b']
        self.assertNotIn('b', d)
        self.assertIn('b', d2)

    def test_get(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(d.get('a'), 1)
        self.assertEqual(d.get('d'), None)
        self.assertEqual(d.get('d', 5), 5)

    def test_pop(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(d.pop('c'), 3)
        self.assertNotIn('c', d)
        self.assertEqual(d.pop('d', 5), 5)
        self.assertRaises(KeyError, d.pop, 'd')

    def test_popitem(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3)])
        self.assertEqual(d.popitem(), ('c', 3))
        self.assertNotIn('c', d)

        d.popitem()
        d.popitem()
        self.assertFalse(d)
        self.assertRaises(KeyError, d.popitem)

    def test_setdefault(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3)])

        self.assertEqual(d.setdefault('a', 4), 1)

        self.assertEqual(d.setdefault('d', 7), 7)
        self.assertIn('d', d)
        self.assertEqual(d['d'], 7)

        self.assertIsNone(d.setdefault('f'))
        self.assertIn('f', d)
        self.assertEqual(d['f'], None)

    def test_update(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d.update({'a': 11, 'd': 4, 'e': 5})
        self.assertIn('d', d)
        self.assertIn('e', d)
        self.assertEqual(d['a'], 11)
        self.assertEqual(d['d'], 4)
        self.assertEqual(d['e'], 5)

    def test_iterkeys(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(sorted(d.iterkeys()), ['a', 'b', 'c'])

    def test_itervalues(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(sorted(d.itervalues()), [1, 2, 3])

    def test_iteritems(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(sorted(d.iteritems()),
                [('a', 1), ('b', 2), ('c', 3)])

    def test_keys(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(sorted(d.keys()), ['a', 'b', 'c'])

    def test_values(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(sorted(d.values()), [1, 2, 3])

    def test_items(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(sorted(d.items()),
                [('a', 1), ('b', 2), ('c', 3)])

class OMDDictCompatTests(OMDDictCompat, unittest.TestCase):
    #
    # ensure OrderedMultiDict behaves sufficiently like builtin dicts
    #
    def omd(self, *args, **kwargs):
        return pathfinder.util.OrderedMultiDict(*args, **kwargs)

class CIOMDDictCompatTests(OMDDictCompat, unittest.TestCase):
    #
    # ensure CaseInsensitiveOrderedMultiDict behaves like builtin dicts
    #
    def omd(self, *args, **kwargs):
        return pathfinder.util.CaseInsensitiveOrderedMultiDict(*args, **kwargs)


class OMDSpecialBehavior(object):
    #
    # testing the additional functionality
    # (order-preservation and multiple values per key)
    #
    def test_iter_goes_in_order(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3)])
        self.assertEqual(list(d), ['a', 'b', 'c'])

        del d['a']
        d['a'] = 1
        self.assertEqual(list(d), ['b', 'c', 'a'])

    def test_iter_duplicates_duplicated_keys(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)])
        self.assertEqual(list(d), ['a', 'b', 'c', 'a'])

    def test_delitem_leaves_older_values(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)])
        self.assertEqual(d['a'], 4)
        del d['a']
        self.assertIn('a', d)
        self.assertEqual(d['a'], 1)

    def test_copy_gets_all_copies(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)])
        d2 = d.copy()
        del d2['a']
        self.assertIn('a', d2)
        self.assertEqual(d2['a'], 1)

    def test_pop_leaves_older_values(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)])
        self.assertEqual(d.pop('a'), 4)
        self.assertIn('a', d)
        self.assertEqual(d['a'], 1)

    def test_popitem_leaves_older_values(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)])
        self.assertEqual(d.popitem(), ('a', 4))
        self.assertIn('a', d)
        self.assertEqual(d['a'], 1)

    def test_update_allows_duplicates(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3)])
        d.update([('a', 4), ('b', 5)])
        del d['a']
        del d['b']
        self.assertIn('a', d)
        self.assertEqual(d['a'], 1)
        self.assertIn('b', d)
        self.assertEqual(d['b'], 2)

    def test_iterkeys_skips_duplicates(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        counts = {}
        for key in d.iterkeys():
            counts.setdefault(key, 0)
            counts[key] += 1
        self.assertEqual(counts.values(), [1, 1, 1])

    def test_iterkeys_preserves_order_by_first_instance(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(list(d.iterkeys()), ['a', 'b', 'c'])

    def test_keys_skips_duplicates(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        counts = {}
        for key in d.keys():
            counts.setdefault(key, 0)
            counts[key] += 1
        self.assertEqual(counts.values(), [1, 1, 1])

    def test_keys_preserves_order_by_first_instance(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(d.keys(), ['a', 'b', 'c'])

    def test_itervalues_traverses_duplicate_keys(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(set(d.itervalues()), set([1,2,3,4,5]))

    def test_itervalues_preserves_order(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(list(d.itervalues()), [1,2,3,4,5])

    def test_values_traverses_duplicate_keys(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(set(d.values()), set([1,2,3,4,5]))

    def test_values_preserves_order(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(d.values(), [1,2,3,4,5])

    def test_iteritems_includes_duplicate_keys(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(set(d.iteritems()),
                set([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)]))

    def test_iteritems_preserves_order(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(list(d.iteritems()),
                [('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])

    def test_items_includes_duplicate_keys(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(set(d.items()),
                set([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)]))

    def test_items_preserves_order(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(d.items(),
                [('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])

    def test_itergetall(self):
        d = self.omd([('a', 1), ('a', 2), ('a', 3)])
        self.assertEqual(list(d.itergetall('a')), [1,2,3])
        self.assertEqual(list(d.itergetall('b')), [])

    def test_getall(self):
        d = self.omd([('a', 1), ('a', 2), ('a', 3)])
        self.assertEqual(d.getall('a'), [1,2,3])
        self.assertEqual(d.getall('b'), [])

    def test_iterlastitems(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(list(d.iterlastitems()),
                [('a', 4), ('b', 5), ('c', 3)])

    def test_lastitems(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(d.lastitems(), [('a', 4), ('b', 5), ('c', 3)])

    def test_popall(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(d.popall('a'), [1, 4])
        self.assertNotIn('a', d)
        self.assertRaises(KeyError, lambda: d['a'])

    def test_popitemall(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        self.assertEqual(d.popitemall(), ('b', [2, 5]))
        self.assertNotIn('b', d)
        self.assertRaises(KeyError, lambda: d['b'])

    def test_replace(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        d.replace('a', 10)
        self.assertEqual(d['a'], 10)
        self.assertEqual(d.items(), [('b', 2), ('c', 3), ('b', 5), ('a', 10)])


class OMDSpecialBehaviorTests(OMDSpecialBehavior, unittest.TestCase):
    #
    # run the special behavior tests on OrderedMultiDict
    #
    def omd(self, *args, **kwargs):
        return pathfinder.util.OrderedMultiDict(*args, **kwargs)


class CIOMDSpecialBehavior(OMDSpecialBehavior, unittest.TestCase):
    #
    # run the special behavior tests on CaseInsensitiveOrderedMultiDict
    #
    def omd(self, *args, **kwargs):
        return pathfinder.util.CaseInsensitiveOrderedMultiDict(*args, **kwargs)

    #
    # throw in tests specifically for the case-insensitive behavior of CIOMD
    #
    def test_contains_insensitive(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertIn('a', d)
        self.assertIn('A', d)
        self.assertIn('b', d)
        self.assertIn('B', d)
        self.assertIn('c', d)
        self.assertIn('C', d)
        self.assertNotIn('d', d)
        self.assertNotIn('D', d)

    def test_getitem_insensitive(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(d['A'], 1)
        self.assertEqual(d['B'], 2)

    def test_setitem_sensitive(self):
        d = self.omd({'a': 1, 'B': 2, 'c': 3})
        keys = d.keys()
        self.assertIn('a', keys)
        self.assertNotIn('A', keys)
        self.assertNotIn('b', keys)
        self.assertIn('B', keys)
        self.assertIn('c', keys)
        self.assertNotIn('C', keys)

    def test_delitem_insensitive(self):
        d = self.omd({'a': 1, 'B': 2, 'c': 3})
        del d['A']
        self.assertNotIn('a', d)

        d = self.omd([('a', 1), ('b', 2), ('A', 3)])
        del d['a']
        self.assertEqual(d.items(), [('a', 1), ('b', 2)])

    def test_get_insensitive(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(d.get('A'), 1)
        self.assertEqual(d.get('B'), 2)

    def test_pop_insensitive(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3)])
        self.assertEqual(d.pop('A', None), 1)
        self.assertNotIn('a', d)

        d = self.omd([('a', 1), ('b', 2), ('A', 3), ('c', 4)])
        self.assertEqual(d.pop('a', None), 3)
        self.assertEqual(d.items(), [('a', 1), ('b', 2), ('c', 4)])

    def test_setdefault_insensitive(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(d.setdefault('A', 10), 1)
        self.assertEqual(len(d), 3)

    def test_itergetall_insensitive(self):
        d = self.omd([('a', 1), ('b', 2), ('A', 3), ('c', 4)])
        self.assertEqual(list(d.itergetall('a')), [1, 3])

    def test_getall_insensitive(self):
        d = self.omd([('a', 1), ('b', 2), ('A', 3), ('c', 4)])
        self.assertEqual(d.getall('a'), [1, 3])

    def test_popall_insensitive(self):
        d = self.omd([('a', 1), ('a', 1.5), ('b', 2), ('A', 3), ('c', 4)])
        self.assertEqual(d.popall('a'), [1, 1.5, 3])
        self.assertEqual(d.items(), [('b', 2), ('c', 4)])

    def test_replace_insensitive_match_but_sensitive_set(self):
        d = self.omd([('a', 1), ('a', 1.5), ('b', 2), ('A', 3), ('c', 4)])
        d.replace('A', 10)
        self.assertEqual(d.items(), [('b', 2), ('c', 4), ('A', 10)])


class OMDInternals(object):
    #
    # use an assertion that the whole internal data structure is sound
    #
    def assertHealthy(self, d):
        nodes = []
        node = d._head
        prevnode = None
        while node:
            nodes.append(node)
            nextnode = node.next
            if nextnode:
                self.assertIs(nextnode.prev, node)
            prevnode, node = node, nextnode
        self.assertIs(d._tail, prevnode)
        self.assertEqual(d._len, len(nodes))
        x = {}
        for n in nodes:
            x.setdefault(n.key, []).append(n)
        self.assertEqual(d._dict, x)
        return nodes

    #
    # tests that ensure the internal state of an OMD remains good
    #
    def test_begins_life_healthy(self):
        self.assertHealthy(self.omd())
        self.assertHealthy(self.omd({'a': 1, 'b': 2, 'c': 3}))
        self.assertHealthy(self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)]))

    def test_setitem(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d['d'] = 4
        d['A'] = 10
        self.assertHealthy(d)

    def test_delitem(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        del d['b']
        self.assertHealthy(d)

        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)])
        del d['a']
        self.assertHealthy(d)

    def test_clear(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d.clear()
        self.assertHealthy(d)

    def test_copy(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        self.assertHealthy(d.copy())
        self.assertHealthy(d)

    def test_pop(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d.pop('b')
        self.assertHealthy(d)

    def test_popitem(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d.popitem()
        self.assertHealthy(d)

    def test_setdefault(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d.setdefault('a', 10)
        self.assertHealthy(d)
        d.setdefault('d', 4)
        self.assertHealthy(d)

    def test_update(self):
        d = self.omd({'a': 1, 'b': 2, 'c': 3})
        d.update({'a': 5, 'B': 6})
        self.assertHealthy(d)

    def test_popall(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4)])
        d.popall('a')
        self.assertHealthy(d)

    def test_popitemall(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        d.popitemall()
        self.assertHealthy(d)

    def test_replace(self):
        d = self.omd([('a', 1), ('b', 2), ('c', 3), ('a', 4), ('b', 5)])
        d.replace('d', 14)
        self.assertHealthy(d)
        d.replace('a', 12)
        self.assertHealthy(d)


class OMDInternalDataStructuresTests(OMDInternals, unittest.TestCase):
    #
    # run the internals tests on OrderedMultiDict
    #
    def omd(self, *args, **kwargs):
        return pathfinder.util.OrderedMultiDict(*args, **kwargs)


class CIOMDInternalDataStructuresTests(OMDInternals, unittest.TestCase):
    #
    # run the internals tests on CaseInsensitiveOrderedMultiDict,
    # adding in checks against the case-insensitive data structure
    #
    def assertHealthy(self, d):
        nodes = super(CIOMDInternalDataStructuresTests, self).assertHealthy(d)
        x = {}
        for n in nodes:
            lst, st = x.setdefault(n.key.lower(), ([], set()))
            if n.key not in st:
                lst.append(n.key)
                st.add(n.key)
        self.assertEqual(dict(d._casemap), x)

    def omd(self, *args, **kwargs):
        return pathfinder.util.CaseInsensitiveOrderedMultiDict(*args, **kwargs)


if __name__ == '__main__':
    unittest.main()
