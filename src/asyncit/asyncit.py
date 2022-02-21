import time
import asyncio
import logging
import threading
from random import randint
from datetime import timedelta
from functools import partial

from .dicts import DotDict
from .queue_ex import QueueEx

logger = logging.getLogger(__name__)


class Asyncit:  # pylint: disable=too-many-instance-attributes
    def __init__(self, pool_size=0, rate_limit=None, max_retry=None, save_output=False):
        """
        :param pool_size:
        :param rate_limit: list of dicts with: max_calls, period_sec
        :param save_output:
        """
        rate_limit = rate_limit or []
        self.futures = []

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as error:
            logger.warning(f"{error}. Creating new event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        self.loop = loop

        self.save_output = save_output
        self.output_queue = QueueEx() if self.save_output else None
        self.sem = threading.Semaphore(pool_size) if pool_size else None
        self.clock_time = time.perf_counter
        self.raise_on_limit = True
        self.rate_limit = []
        self.max_retry = max_retry or 1
        for limit in rate_limit:
            limit = DotDict(limit)
            self.rate_limit.append(
                DotDict(
                    dict(
                        max_calls=limit.max_calls,
                        period_sec=limit.period_sec,
                        last_reset=self.clock_time(),
                        num_calls=0,
                        total_calls=0,
                    )
                )
            )
        self.lock = threading.RLock()
        self.total_counter = 0
        self.total_run_start = self.clock_time()

    def __period_remaining(self, last_reset, period_sec):
        """
        Return the period remaining for the current rate limit window.
        :return: The remaing period.
        :rtype: float
        """
        elapsed = self.clock_time() - last_reset
        return period_sec - elapsed

    def reset_start_time(self):
        self.total_run_start = self.clock_time()

    def total_run_time(self):
        elapsed_time = self.clock_time() - self.total_run_start
        return str(timedelta(seconds=elapsed_time)).split(".", maxsplit=1)[0]

    def func_wrapper(self, func, *args, **kwargs):
        if self.sem:
            self.sem.acquire()

        if self.rate_limit:
            with self.lock:
                for limit in self.rate_limit:
                    period_remaining = self.__period_remaining(limit.last_reset, limit.period_sec)

                    # If the time window has elapsed then reset.
                    if period_remaining <= 0:
                        limit.num_calls = 0
                        limit.last_reset = self.clock_time()

                    limit.num_calls += 1
                    limit.total_calls += 1
                    if limit.num_calls > limit.max_calls:
                        logger.info(f"going to sleep for {period_remaining} {limit}")
                        time.sleep(period_remaining)

        value = None
        retry_counter = 0
        exception = None

        while retry_counter < self.max_retry:
            retry_counter += 1
            try:
                value = func(*args, **kwargs)
                save_value = bool(value is not None and self.save_output and self.output_queue is not None)
                if save_value:
                    self.output_queue.put(value)
                break
            except asyncio.CancelledError:
                logger.info("worker cancelled")
                break
            except Exception as ex:
                exception = ex
                if retry_counter < self.max_retry:
                    sleep_time = randint(1, 6)
                    logger.error(f"ex: {type(ex)}")
                    logger.info(f"sleep before retry: {sleep_time} sec ({self.rate_limit})")
                    time.sleep(sleep_time)
        else:
            logger.error(
                f"!!! Error: function {func.__name__} failed with args: {args} and kwargs: {kwargs}. "
                f"Exception caught: {exception}"
            )
        if self.sem:
            self.sem.release()
        return value

    def run(self, func, *args, **kwargs):
        func = partial(self.func_wrapper, func, *args, **kwargs)

        # Run tasks in the default loop's executor
        self.futures.append(self.loop.run_in_executor(None, func))

    def wait(self):
        self.loop.run_until_complete(self._gather_with_concurrency())
        self.futures = []

    def get_output(self):
        return self.output_queue.to_list() if self.output_queue else None

    async def _gather_with_concurrency(self):
        await asyncio.gather(*self.futures, return_exceptions=True)
