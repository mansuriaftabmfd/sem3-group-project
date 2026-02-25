"""
Custom Data Structures for SkillVerse Application
Built ENTIRELY from scratch — no external libraries used for core logic.

This module contains hand-built implementations of:
1. HashMap  — Hash table with separate chaining for O(1) average lookups
2. MaxHeap  — Binary max-heap for efficient top-N element selection
3. Queue    — Linked-list-based FIFO queue for order processing
4. Trie     — Prefix tree for fast autocomplete suggestions

Author: SkillVerse Team
Purpose: Demonstrate understanding of fundamental data structures
"""


# ============================================================================
# 1. HASHMAP — Hash Table with Separate Chaining
# ============================================================================

class _HashNode:
    """
    Internal linked-list node for HashMap's separate chaining.
    Each node stores a key-value pair and a pointer to the next node.
    """
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.next = None  # Pointer to next node in chain


class HashMap:
    """
    Hash Table implementation using separate chaining for collision resolution.
    Built from scratch as a drop-in replacement for Python's built-in dict.

    How it works:
    - An internal array of 'buckets' stores key-value pairs
    - A hash function maps each key to a bucket index
    - Collisions are resolved via chaining (linked list per bucket)
    - The table resizes (doubles) when load factor exceeds 0.75

    Time Complexity:
    - Average case: O(1) for get, put, delete, contains
    - Worst case:   O(n) when all keys hash to the same bucket

    Space Complexity: O(n)
    """

    INITIAL_CAPACITY = 16
    LOAD_FACTOR_THRESHOLD = 0.75

    def __init__(self):
        """Initialize an empty HashMap with default capacity."""
        self._capacity = self.INITIAL_CAPACITY
        self._size = 0
        self._buckets = [None] * self._capacity

    def _hash(self, key):
        """Compute bucket index for a given key using modulo hashing."""
        return hash(key) % self._capacity

    def _resize(self):
        """Double capacity and rehash all existing entries."""
        old_buckets = self._buckets
        self._capacity *= 2
        self._buckets = [None] * self._capacity
        self._size = 0
        for head in old_buckets:
            node = head
            while node is not None:
                self[node.key] = node.value
                node = node.next

    def __setitem__(self, key, value):
        """Insert or update a key-value pair: hashmap[key] = value"""
        index = self._hash(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next
        new_node = _HashNode(key, value)
        new_node.next = self._buckets[index]
        self._buckets[index] = new_node
        self._size += 1
        if self._size / self._capacity > self.LOAD_FACTOR_THRESHOLD:
            self._resize()

    def __getitem__(self, key):
        """Retrieve value by key. Raises KeyError if not found."""
        index = self._hash(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        raise KeyError(key)

    def __contains__(self, key):
        """Check if key exists: key in hashmap"""
        index = self._hash(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                return True
            node = node.next
        return False

    def __delitem__(self, key):
        """Remove a key-value pair: del hashmap[key]"""
        index = self._hash(key)
        node = self._buckets[index]
        prev = None
        while node is not None:
            if node.key == key:
                if prev is None:
                    self._buckets[index] = node.next
                else:
                    prev.next = node.next
                self._size -= 1
                return
            prev = node
            node = node.next
        raise KeyError(key)

    def get(self, key, default=None):
        """Retrieve value by key, returning default if not found."""
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        """Remove all key-value pairs and reset to initial state."""
        self._capacity = self.INITIAL_CAPACITY
        self._size = 0
        self._buckets = [None] * self._capacity

    def keys(self):
        """Return a list of all keys."""
        result = []
        for head in self._buckets:
            node = head
            while node is not None:
                result.append(node.key)
                node = node.next
        return result

    def values(self):
        """Return a list of all values."""
        result = []
        for head in self._buckets:
            node = head
            while node is not None:
                result.append(node.value)
                node = node.next
        return result

    def items(self):
        """Return a list of (key, value) tuples."""
        result = []
        for head in self._buckets:
            node = head
            while node is not None:
                result.append((node.key, node.value))
                node = node.next
        return result

    def __len__(self):
        return self._size

    def __repr__(self):
        pairs = [f'{k!r}: {v!r}' for k, v in self.items()]
        return 'HashMap({' + ', '.join(pairs) + '})'


# ============================================================================
# 2. MAX HEAP — Binary Max-Heap (Array-based)
# ============================================================================

class MaxHeap:
    """
    Binary Max-Heap built from scratch using a flat array.

    How it works:
    - Stored as a flat array where for element at index i:
      - Parent is at (i-1) // 2
      - Left child is at 2i + 1
      - Right child is at 2i + 2
    - Max-heap property: parent priority >= both children
    - Supports efficient extraction of the N largest elements

    Time Complexity:
    - insert:      O(log n)
    - extract_max: O(log n)
    - nlargest(k): O(n log n + k log n)
    """

    def __init__(self):
        """Initialize an empty MaxHeap."""
        self._heap = []   # Stores (priority, order, item) tuples
        self._counter = 0  # Insertion order for tie-breaking

    def _swap(self, i, j):
        """Swap two elements in the heap array."""
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _heapify_up(self, index):
        """Bubble element UP to restore heap property after insertion."""
        while index > 0:
            parent = (index - 1) // 2
            if self._heap[index][0] > self._heap[parent][0]:
                self._swap(index, parent)
                index = parent
            else:
                break

    def _heapify_down(self, index):
        """Bubble element DOWN to restore heap property after extraction."""
        size = len(self._heap)
        while True:
            largest = index
            left = 2 * index + 1
            right = 2 * index + 2
            if left < size and self._heap[left][0] > self._heap[largest][0]:
                largest = left
            if right < size and self._heap[right][0] > self._heap[largest][0]:
                largest = right
            if largest == index:
                break
            self._swap(index, largest)
            index = largest

    def insert(self, item, priority=None):
        """Insert an item with a given priority into the heap."""
        if priority is None:
            priority = item
        self._heap.append((priority, self._counter, item))
        self._counter += 1
        self._heapify_up(len(self._heap) - 1)

    def extract_max(self):
        """Remove and return the item with the highest priority."""
        if not self._heap:
            raise IndexError("extract_max from an empty heap")
        self._swap(0, len(self._heap) - 1)
        _, _, item = self._heap.pop()
        if self._heap:
            self._heapify_down(0)
        return item

    def peek(self):
        """Return the maximum item without removing it."""
        if not self._heap:
            raise IndexError("peek from an empty heap")
        return self._heap[0][2]

    def size(self):
        """Return the number of elements."""
        return len(self._heap)

    def is_empty(self):
        """Check if the heap is empty."""
        return len(self._heap) == 0

    @staticmethod
    def nlargest(n, iterable, key=None):
        """
        Return the n largest elements from iterable using a MaxHeap.
        Drop-in replacement for heapq.nlargest().

        Algorithm:
        1. Insert all items into a MaxHeap with key values as priority
        2. Extract the maximum element n times
        """
        if key is None:
            key = lambda x: x
        heap = MaxHeap()
        for item in iterable:
            heap.insert(item, key(item))
        result = []
        for _ in range(min(n, heap.size())):
            result.append(heap.extract_max())
        return result

    def __len__(self):
        return len(self._heap)

    def __repr__(self):
        return f'MaxHeap(size={len(self._heap)})'


# ============================================================================
# 3. QUEUE — Linked-List-based FIFO Queue
# ============================================================================

class _QueueNode:
    """Internal node for the linked-list-based Queue."""
    def __init__(self, value):
        self.value = value
        self.next = None


class Queue:
    """
    FIFO Queue built from scratch using a singly linked list.

    How it works:
    - 'front' pointer for dequeue, 'rear' pointer for enqueue
    - Enqueue appends to rear:  O(1)
    - Dequeue removes from front: O(1)
    - No fixed capacity — grows dynamically

    Time Complexity: O(1) for enqueue, dequeue, peek
    Space Complexity: O(n)
    """

    def __init__(self):
        """Initialize an empty Queue."""
        self._front = None
        self._rear = None
        self._size = 0

    def enqueue(self, value):
        """Add an element to the rear of the queue."""
        new_node = _QueueNode(value)
        if self._rear is None:
            self._front = new_node
            self._rear = new_node
        else:
            self._rear.next = new_node
            self._rear = new_node
        self._size += 1

    def dequeue(self):
        """Remove and return the element at the front."""
        if self._front is None:
            raise IndexError("dequeue from an empty queue")
        value = self._front.value
        self._front = self._front.next
        if self._front is None:
            self._rear = None
        self._size -= 1
        return value

    def peek(self):
        """Return the front element without removing it."""
        if self._front is None:
            raise IndexError("peek from an empty queue")
        return self._front.value

    def is_empty(self):
        """Check if the queue is empty."""
        return self._front is None

    def append(self, value):
        """Alias for enqueue — compatibility with deque API."""
        self.enqueue(value)

    def to_list(self):
        """Convert queue contents to a Python list (front to rear)."""
        result = []
        node = self._front
        while node is not None:
            result.append(node.value)
            node = node.next
        return result

    def __len__(self):
        return self._size

    def __repr__(self):
        return f'Queue({self.to_list()})'


# ============================================================================
# 4. TRIE — Prefix Tree for Autocomplete
# ============================================================================

class _TrieNode:
    """
    Internal node for the Trie (Prefix Tree).
    Each node represents a character and contains:
    - children: HashMap of child nodes (char -> _TrieNode)
    - is_end: whether this node marks the end of a complete word
    - original_word: the original-case version of the word
    - frequency: how many times this word was inserted
    """
    def __init__(self):
        self.children = {}        # char -> _TrieNode
        self.is_end = False
        self.original_word = None  # Preserves original casing
        self.frequency = 0


class Trie:
    """
    Trie (Prefix Tree) built from scratch for autocomplete functionality.

    How it works:
    - Each node represents a single character
    - Words are stored character-by-character along paths from root
    - Prefix search traverses to the prefix end, then collects all words below
    - All lookups are case-insensitive (stored lowercase, original case preserved)

    Time Complexity:
    - insert:          O(L) where L is word length
    - search:          O(L)
    - get_suggestions: O(L + K) where K is number of matching words

    Space Complexity: O(ALPHABET_SIZE * L * N) where N is number of words
    """

    def __init__(self):
        """Initialize an empty Trie with a root node."""
        self.root = _TrieNode()
        self._word_count = 0

    def insert(self, word):
        """
        Insert a word into the Trie.
        Stores lowercase for matching, preserves original case for display.
        """
        if not word or not word.strip():
            return
        node = self.root
        for char in word.lower():
            if char not in node.children:
                node.children[char] = _TrieNode()
            node = node.children[char]

        if not node.is_end:
            self._word_count += 1
        node.is_end = True
        node.original_word = word  # Preserve original casing
        node.frequency += 1

    def search(self, word):
        """Check if an exact word exists in the Trie. Returns True/False."""
        if not word:
            return False
        node = self.root
        for char in word.lower():
            if char not in node.children:
                return False
            node = node.children[char]
        return node.is_end

    def starts_with(self, prefix):
        """Check if any word in the Trie starts with the given prefix."""
        if not prefix:
            return False
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return False
            node = node.children[char]
        return True

    def _collect_words(self, node, results, limit):
        """DFS to collect all complete words below a given node."""
        if len(results) >= limit:
            return
        if node.is_end:
            results.append((node.original_word, node.frequency))
        for char in sorted(node.children.keys()):
            if len(results) >= limit:
                return
            self._collect_words(node.children[char], results, limit)

    def get_suggestions(self, prefix, limit=10):
        """
        Get autocomplete suggestions for a given prefix.

        Algorithm:
        1. Navigate to the node representing the last char of prefix
        2. DFS from that node to collect all complete words
        3. Sort by frequency (most popular first), then by length
        4. Return top 'limit' results with original casing

        Returns:
            list: Suggestion strings matching the prefix
        """
        if not prefix:
            return []
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]

        results = []
        self._collect_words(node, results, limit * 3)

        # Sort by frequency (descending), then by word length (shorter first)
        results.sort(key=lambda x: (-x[1], len(x[0])))

        return [word for word, freq in results[:limit]]

    def __len__(self):
        return self._word_count

    def __repr__(self):
        return f'Trie(words={self._word_count})'
