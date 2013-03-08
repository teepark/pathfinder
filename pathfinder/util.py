"""pathfinder.util -- data structures to support HTTP messages

Copyright 2011 Jawbone Inc.

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

import collections


__all__ = ["OrderedMultiDict", "CaseInsensitiveOrderedMultiDict"]

_notset = object()


class OrderedMultiDict(collections.MutableMapping):
    '''A dictionary which maintains some necessary extra metadata about entries

    - allows multiple values for a given key
    - maintains a total ordering for all values
    '''

    # reasonable performance on the wide variety of dictionary operations are
    # supported by the datastructure underlying this object: a doubly linked
    # list of nodes with (key, value) pairs, and a dict mapping keys straight
    # to nodes

    def __init__(self, *args, **kwargs):
        self._dict = collections.defaultdict(list)
        self._head = None # need this for pop()ing latest item
        self._tail = None # need this for iteration starting point
        self._len = 0     # need this for a constant-time __len__

        self.update(*args, **kwargs)

    def __len__(self):
        return self._len

    def __iter__(self):
        "iteration is done in order"
        for node in self._iternodes():
            yield node.key

    def __contains__(self, key):
        return key in self._dict

    has_key = __contains__

    def __getitem__(self, key):
        "returns only the last value for the provided key"
        if key not in self._dict:
            raise KeyError(key)
        return self._dict[key][-1].value

    def __setitem__(self, key, value):
        "effectively appends to the list of values for a key"
        node = _OMDNode()
        node.key = key
        node.value = value
        if not self._head:
            self._head = node
            node.prev = None
        else:
            node.prev = self._tail
            self._tail.next = node
        node.next = None
        self._tail = node
        self._dict[key].append(node)
        self._len += 1

    def __delitem__(self, key):
        "only removes the last value for a given key"
        if key not in self._dict:
            raise KeyError(key)
        self._remove_last_item(key)

    def __repr__(self):
        return "{%s}" % (
                ', '.join('%r: %r' % (k, v) for k, v in self.iteritems()))

    __str__ = __repr__

    def clear(self):
        self._dict.clear()
        self._head = None
        self._tail = None
        self._len = 0

    def copy(self):
        return type(self)(self)

    def get(self, key, default=None):
        "only gets a the last value for the given key"
        if key not in self._dict:
            return default
        return self._dict[key][-1].value

    def pop(self, key, default=_notset):
        "only pops a single value for the key, others may remain"
        if key not in self._dict:
            if default is _notset:
                raise KeyError(key)
            return default
        return self._remove_last_item(key)

    def popitem(self):
        "pops a single key/value pair, other values for the key may remain"
        # only pops a single (key, value) pair,
        # other values for the key may remain
        if not self._tail:
            raise KeyError("OrderedMultiDict is empty")
        key = self._tail.key
        return key, self._remove_last_item(key)

    def setdefault(self, key, value=None):
        if key in self._dict:
            return self._dict[key][-1].value
        self[key] = value
        return value

    def update(self, *args, **kwargs):
        "preserves order if the argument is a list of two-tuples"
        if args:
            arg = args[0]
            if isinstance(arg, collections.MutableMapping):
                arg = arg.iteritems()
            for key, value in arg:
                self[key] = value
        for key, value in kwargs.iteritems():
            self[key] = value

    def iterkeys(self):
        "iterator over the keys in order, but skipping duplicates"
        shown = set()
        for node in self._iternodes():
            if node.key not in shown:
                yield node.key
                shown.add(node.key)

    def itervalues(self):
        "iterator over all values in order"
        for node in self._iternodes():
            yield node.value

    def iteritems(self):
        "iterator over all key/value pairs in order"
        for node in self._iternodes():
            yield node.key, node.value

    def keys(self):
        "produces all keys in order, skipping duplicates"
        return list(self.iterkeys())

    def values(self):
        "produces all values in order"
        return list(self.itervalues())

    def items(self):
        "produces all key/value pairs in order"
        return list(self.iteritems())

    #
    # these are not re-implemented dictionary methods but extensions for OMD
    #
    def itergetall(self, key):
        "iterator over all the values for a given key in order"
        for node in self._dict.get(key, ()):
            yield node.value

    def getall(self, key):
        "produces all the values for a given key in order"
        return list(self.itergetall(key))

    def iterlastitems(self):
        "iterator producing key/value pairs in order with no duplicate keys"
        shown = set()
        for node in self._iternodes():
            if node.key not in shown:
                yield node.key, self._dict[node.key][-1].value
                shown.add(node.key)

    def lastitems(self):
        "produces a list of key/value pairs in order with no duplicate keys"
        return list(self.iterlastitems())

    def popall(self, key):
        "remove all values present for a particular key"
        # there is no iter-version because this implementation
        # wouldn't play nice with mutation between iterations
        result = []
        for node in self._dict.pop(key, ()):
            self._remove_node(node)
            result.append(node.value)
        return result

    def popitemall(self):
        "remove all values for whichever key comes last in order"
        if not self._tail:
            raise KeyError("OrderedMultiDict is empty")
        key = self._tail.key
        return key, self.popall(self._tail.key)

    def replace(self, key, value):
        "set a value for a key, removing all existing values"
        for node in self._dict.pop(key, ()):
            self._remove_node(node)
        self[key] = value

    def _remove_node(self, node):
        self._len -= 1
        if node.prev:
            node.prev.next = node.next
        else:
            self._head = node.next
        if node.next:
            node.next.prev = node.prev
        else:
            self._tail = node.prev

    def _remove_last_item(self, key):
        node = self._dict[key].pop()
        if not self._dict[key]:
            del self._dict[key]
        self._remove_node(node)
        return node.value

    def _iternodes(self):
        node = self._head
        while node:
            yield node
            node = node.next


class CaseInsensitiveOrderedMultiDict(OrderedMultiDict):
    '''Adds case-insensitive retrievals to OrderedMultiDict's behavior

    this class does **store** keys case-sensitively, so keys(), items(), etc
    will return the keys exactly as they were set
    '''
    def __init__(self, *args, **kwargs):
        self._casemap = collections.defaultdict(lambda: ([], set()))
        super(CaseInsensitiveOrderedMultiDict, self).__init__(*args, **kwargs)

    def __contains__(self, key):
        "checks case-insensitively for presence of the key"
        return key.lower() in self._casemap

    def __getitem__(self, key):
        "retrieves the last value for any key that matches case-insensitively"
        key = key.lower()
        if key not in self._casemap:
            raise KeyError(key)
        key = self._casemap[key][0][-1]
        return super(CaseInsensitiveOrderedMultiDict, self).__getitem__(key)

    def __setitem__(self, key, value):
        super(CaseInsensitiveOrderedMultiDict, self).__setitem__(key, value)
        lst, st = self._casemap[key.lower()]
        if key not in st:
            st.add(key)
            lst.append(key)

    def __delitem__(self, key):
        "deletes the last value for any key that matches case-insensitively"
        lower = key.lower()
        if lower in self._casemap:
            key = self._casemap[lower][0][-1]
        super(CaseInsensitiveOrderedMultiDict, self).__delitem__(key)

    def clear(self):
        super(CaseInsensitiveOrderedMultiDict, self).clear()
        self._casemap.clear()

    def get(self, key, default=None):
        "retrieves the last value for any key that matches case-insensitively"
        key = key.lower()
        if key not in self._casemap:
            return default
        key = self._casemap[key][0][-1]
        return super(CaseInsensitiveOrderedMultiDict, self).__getitem__(key)

    def pop(self, key, default=_notset):
        "pops the last value for any key that matches case-insensitively"
        lower = key.lower()
        if lower not in self._casemap:
            if default is _notset:
                raise KeyError(key)
            return default
        key = self._casemap[lower][0][-1]
        return super(CaseInsensitiveOrderedMultiDict, self).pop(key)

    def setdefault(self, key, value=None):
        "the check for presence of the key is case-insensitive"
        lower = key.lower()
        if lower in self._casemap:
            key = self._casemap[lower][0][-1]
        return super(CaseInsensitiveOrderedMultiDict,
                self).setdefault(key, value)

    def itergetall(self, key):
        "gets all values for all keys which case-insensitively match"
        lower = key.lower()
        for key in self._casemap.get(lower, [()])[0]:
            for value in super(CaseInsensitiveOrderedMultiDict,
                    self).itergetall(key):
                yield value

    def popall(self, key):
        "pops all values for all keys which case-insensitively match"
        lower = key.lower()
        lst, st = self._casemap.pop(lower)
        results = []
        for key in lst:
            results.extend(super(
                CaseInsensitiveOrderedMultiDict, self).popall(key))
        return results

    def replace(self, key, value):
        "replace all case-insensitively matching key/value pairs"
        lower = key.lower()
        if lower in self._casemap:
            for key_option in self._casemap[lower][0]:
                super(CaseInsensitiveOrderedMultiDict,
                        self).popall(key_option)
        self._casemap[lower] = ([key], set([key]))
        super(CaseInsensitiveOrderedMultiDict, self).__setitem__(key, value)

    def _remove_last_item(self, key):
        lower = key.lower()
        lst, st = self._casemap[lower]
        key = lst[-1]
        value = super(CaseInsensitiveOrderedMultiDict,
                self)._remove_last_item(key)
        if key not in self._dict:
            lst.pop()
            st.remove(key)
            if not lst:
                del self._casemap[lower]
        return value

class _OMDNode(object):
    __slots__ = ["prev", "next", "key", "value"]

    def _reprshort(self):
        return '(%r: %r)' % (self.key, self.value)

    def __repr__(self):
        return '_OMDNode(prev=%s, next=%s, keyval=%s)' % (
                self.prev._reprshort() if self.prev else 'None',
                self.next._reprshort() if self.next else 'None',
                self._reprshort())
