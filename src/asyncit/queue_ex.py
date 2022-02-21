import timeit
import logging
import multiprocessing
from functools import partial
from multiprocessing.queues import Empty, Queue

logger = logging.getLogger(__name__)


class SharedCounter:
    def __init__(self, count=0):
        self.count = multiprocessing.Value("i", count)

    def increment(self, num=1):
        """Increment the counter by n (default = 1)"""
        with self.count.get_lock():
            if self.count.value + num >= 0:
                self.count.value += num

    def decrement(self, num=1):
        """Decrement the counter by n (default = 1)"""
        self.increment(num * -1)

    @property
    def value(self):
        """Return the value of the counter"""
        return self.count.value


class QueueEx(Queue):

    _sentinel = object()

    def __init__(self, default_timeout=None):
        super().__init__(ctx=multiprocessing.get_context())
        self.size_counter = SharedCounter(0)
        self.default_timeout = default_timeout
        self.idle_timer_start = None
        self.non_block_get = partial(self.get, block=False)
        self.append = self.add = self.put
        self.size = self.qsize

    def __iter__(self):
        """returns the iterator object"""
        return iter(self.non_block_get, self._sentinel)

    def __next__(self, timeout=None):
        """return the next item in the sequence"""
        if self.empty():
            raise StopIteration
        return self.get(timeout=timeout)

    def __len__(self):
        return self.qsize()

    def close(self):
        while not self.empty():
            self.get()
        self.cancel_join_thread()

    def reset_idle_timer(self):
        self.idle_timer_start = timeit.default_timer()

    def clear_idle_timer(self):
        self.idle_timer_start = None

    def idle_time(self):
        if not self.idle_timer_start:
            return 0
        return timeit.default_timer() - self.idle_timer_start

    def put(self, *args, **kwargs):
        self.reset_idle_timer()
        self.size_counter.increment(1)
        try:
            super().put(*args, **kwargs)
        except Exception as ex:
            logger.error(f"failed to add item: {args}, ex: {ex}")

    def get(self, *args, **kwargs):
        self.size_counter.decrement(1)
        if self.empty():
            self.clear_idle_timer()
        if self.default_timeout and "timeout" not in kwargs and len(args) < 2:
            kwargs["timeout"] = self.default_timeout
        try:
            return super().get(*args, **kwargs)
        except Empty:
            # in case block parameter is False - return the sentinel instead of raising Exception (handle loop iter)
            return self._sentinel

    def to_list(self, max_size=None):
        items = []
        while not self.empty():
            items.append(self.get())
            if max_size and len(items) == max_size:
                break
        return items

    def qsize(self):
        """Reliable implementation of multiprocessing.Queue.qsize()"""
        return self.size_counter.value

    def empty(self):
        """Reliable implementation of multiprocessing.Queue.empty()"""
        return not self.qsize()
