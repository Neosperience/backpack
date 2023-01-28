''' This module contains time-related utility methods for measuring code execution time
and scheduling tasks in an external event loop. '''

import time
import datetime
import threading
from collections import deque
from itertools import islice
from typing import List, Deque, Optional, Iterator, Dict, Any, Callable, Tuple
from abc import ABC, abstractmethod
import concurrent.futures
import functools

from dateutil.tz import tzlocal

def local_now() -> datetime.datetime:
    ''' Returns the current time in local time zone.

    Returns:
        A timezone aware datetime instance in the local time zone.
    '''
    return datetime.datetime.now(tz=tzlocal())

def local_dt(dt: datetime.datetime) -> datetime.datetime:
    ''' Converts the supplied naive datetime to be time zone aware in the local time zone.

    Args:
        dt: The naive datetime instance.

    Returns:
        A timezone aware datetime instance in the local time zone.
    '''
    return dt.astimezone(tz=tzlocal())

def panorama_timestamp_to_datetime(panorama_ts: Tuple[int, int]) -> datetime.datetime:
    ''' Converts panoramasdk.media.time_stamp (seconds, microseconds)
    tuple to python datetime.

    Args:
        panorama_ts: The Panorama timestamp

    Returns:
        A python datetime instance.
    '''
    sec, microsec = panorama_ts
    return datetime.datetime.fromtimestamp(sec + microsec / 1000000.0)


class BaseTimer(ABC):
    ''' Base class for code execution time measuring timers.

    Args:
        max_intervals: Maximum number of intervals to remember.
    '''

    # Print at most this many intervals in __repr__
    MAX_REPR_INTERVALS = 5

    def __init__(self, max_intervals:int=10):
        self.intervals: Deque[float] = deque(maxlen=max_intervals)

    def min(self) -> float:
        ''' Returns the shortest time interval between the events (in seconds). '''
        return min(self.intervals) if len(self.intervals) > 0 else 0.0

    def max(self) -> float:
        ''' Returns the longest time interval between the events (in seconds). '''
        return max(self.intervals) if len(self.intervals) > 0 else 0.0

    def mean(self) -> float:
        ''' Returns the mean time interval between the events (in seconds). '''
        return self.sum() / self.len() if self.len() > 0 else 0.0

    def sum(self) -> float:
        ''' Returns the sum of the time interval between recorded events (in seconds). '''
        return sum(self.intervals) if len(self.intervals) > 0 else 0.0

    def len(self) -> int:
        ''' Returns the number of recorded events. '''
        return len(self.intervals)

    def freq(self) -> float:
        ''' Returns the mean frequency of the events (in Hertz). '''
        mean = self.mean()
        return 1 / mean if mean > 0 else 0.0

    def reset(self) -> None:
        ''' Resets the timer. '''
        self.intervals.clear()

    def _repr_intervals(self, intervals):
        iv_list = [f'{iv:.4f}' for iv in islice(intervals, self.MAX_REPR_INTERVALS)]
        if len(intervals) > self.MAX_REPR_INTERVALS:
            iv_list.append('...')
        return f'[{", ".join(iv_list)}]'

    def _repr_props(self) -> Iterator[str]:
        if self.intervals:
            yield f'intervals={self._repr_intervals(self.intervals)}'
            yield f'min={self.min():.4f}'
            yield f'mean={self.mean():.4f}'
            yield f'max={self.max():.4f}'

    def __repr__(self) -> str:
        elements = [self.__class__.__name__] + list(self._repr_props())
        return '<' + ' '.join(elements) + '>'


class Ticker(BaseTimer):

    ''' A performance profiler that measures the time interval between repeatedly
    occurring events.

    Ticker can also calculate basic statistics of the time intervals.

    Example usage::

        ticker = Ticker(max_intervals=5)
        for i in range(10):
            ticker.tick()
            time.sleep(random.random() / 10)
        print(ticker)

    Results::

        <Ticker intervals=[0.0899, 0.0632, 0.0543, 0.0713, 0.0681] min=0.0543 mean=0.0694 max=0.0899>

    :ivar max_intervals: Maximum number of time intervals to be recorded.
        Only the last max_intervals number of intervals will be kept.
    :ivar intervals: The recorded intervals in seconds between the successive events.
    '''

    def __init__(self, max_intervals:int=10):
        super().__init__(max_intervals=max_intervals)
        self._last_tick: Optional[float] = None

    def tick(self) -> None:
        ''' Registers a tick in this Ticker. '''
        now = time.perf_counter()
        if self._last_tick is not None:
            self.intervals.append(now - self._last_tick)
        self._last_tick = now


class StopWatch(BaseTimer):

    ''' A simple performance profiler with context managers.

    There are two ways to use StopWatch: as a context manager, or with the `tick()`
    method. You can use the same StopWatch object in both ways at the same time.

    When used as a context manager, StopWatch can be used to measure the
    performance of python code using an elegant API based on context manager.
    You can measure nested and serial execution.

    The second way is to measure the average execution of repeating tasks with
    the `tick()` function call. After enough data samples were collected with
    `tick()`, you can calculate the average execution of the task calling
    `mean_tick()`.

    Example usage::

        import time
        with StopWatch('root') as root:
            with root.child('task1', max_ticks=5) as task:
                time.sleep(0.01)
                with task.child('subtask1.1'):
                    time.sleep(0.03)
                with task.child('subtask1.2'):
                    time.sleep(0.07)
                with task.child('subtask1.3'):
                    time.sleep(0.09)
            with root.child('task2') as task:
                time.sleep(0.17)
        print(root)


    Results::

        <StopWatch name=root total_elapsed=0.9222 children=[
            <StopWatch
                name=task1
                total_elapsed=0.7520
                ticks=[0.0501, 0.0601, 0.0701, 0.0802, 0.0902]
                mean_tick=0.0701
                children=[
                    <StopWatch name=subtask1.1 total_elapsed=0.0301>,
                    <StopWatch name=subtask1.2 total_elapsed=0.0701>,
                    <StopWatch name=subtask1.3 total_elapsed=0.0902>
                ]
            >,
            <StopWatch name=task2 total_elapsed=0.1702>
        ]>

    Args:
        name: The name of this StopWatch
        max_intervals: Maximum number of intervals to be recorded.

    Attributes:
        name (str): The name of this StopWatch
        parent (Optional['StopWatch']): The parent StopWatch
        children (Dict[str, 'StopWatch']): The name-indexed dictionary of the children StopWatches
    '''

    def __init__(self, name:str, max_intervals:int=10):
        super().__init__(max_intervals=max_intervals)
        self.name: str = name
        self.parent: Optional['StopWatch'] = None
        self.children: Dict[str, 'StopWatch'] = {}
        self._start: Optional[float] = None

    def child(self, name:str, max_intervals:Optional[int]=None) -> 'StopWatch':
        ''' Creates a new or returns an existing child of this StopWatch.

        Args:
            name: Name of the child StopWatch.
            max_intervals: Maximum number of intervals to be recorded in the
                child. If None, max_intervals of the parent (this object) will be used.
        '''
        if name in self.children:
            return self.children[name]
        if max_intervals is None:
            max_intervals = self.intervals.maxlen
        child = self.__class__(name, max_intervals=max_intervals)
        child.parent = self
        self.children[name] = child
        return child

    def parents(self) -> Iterator['StopWatch']:
        ''' Returns a generator of all parents of this StopWatch. '''
        current = self
        while True:
            current = current.parent
            if not current:
                break
            yield current

    def full_name(self) -> str:
        ''' Returns the fully qualified name of this StopWatch, including
        all parents' name. '''
        family = [self.name]
        family.extend(p.name for p in self.parents())
        return '.'.join(reversed(family))

    def __enter__(self) -> 'StopWatch':
        ''' Context manager entry point returning self.'''
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        ''' Context manager exit. '''
        self.intervals.append(time.perf_counter() - self._start)
        self._start = None

    def measure(self, fun):
        ''' Use stopwatch as decorator.

        Usage::

            import time
            from backpack.timepiece import StopWatch

            stopwatch = StopWatch('stopwatch')

            @stopwatch.measure
            def long_running_func():
                time.sleep(10)

        '''
        @functools.wraps(fun)
        def wrapper(*args, **kwds):
            self.__enter__()
            fun(*args, **kwds)
            self.__exit__()
        return wrapper

    @property
    def level(self) -> int:
        ''' Returns the number of parents. '''
        return len(list(self.parents()))

    def _repr_props(self) -> Iterator[str]:
        yield f'name={self.name}'
        yield from super()._repr_props()

    def __repr__(self) -> str:
        ''' Indented string representation of this StopWatch.'''
        lvl = self.level
        indent = "    " * lvl
        newline = '\n'
        props = list(self._repr_props())
        if self.children:
            children = (repr(c) for c in self.children.values())
            props.append(f'children=[{", ".join(children)}\n{indent}]')
        return f'{newline if lvl > 0 else ""}{indent}<{self.__class__.__name__} {" ".join(props)}>'


class Callback:
    ''' Encapsulates a callback function and its arguments.

    The callback can be optionally called asynchronously.

    Args:
        cb (Callable): The callback function to be called
        cbargs (Optional[List[Any]]): The callback function to be called
        cbkwargs (Optional[Dict[str, Any]]): Keyword arguments of the callback
        executor (Optional[concurrent.futures.Executor]): If specified, the callback function will
            be called asynchronously using this executor.
    '''

    # pylint: disable=invalid-name,too-few-public-methods
    # invalid-name disabled for the `cb` parameter. callable is also taken.
    # too-few-public-methods disabled because this is a wrapper class around a callback function.
    def __init__(
        self,
        cb: Callable,
        cbargs: Optional[List[Any]] = None,
        cbkwargs: Optional[Dict[str, Any]] = None,
        executor: Optional[concurrent.futures.Executor] = None
    ):
        self.cb = cb
        self.cbargs = cbargs or []
        self.cbkwargs = cbkwargs or {}
        self.executor = executor

    def __call__(self):
        if self.executor:
            self.executor.submit(self.cb, *self.cbargs, **self.cbkwargs)
            return None
        return self.cb(*self.cbargs, **self.cbkwargs)


class Schedule(ABC):
    ''' Schedules a task to be called later with the help of an external
    scheduler.

    The external scheduler is expected to call the `tick()` method periodically,
    most likely from an event-loop.

    Args:
        repeating (bool): If this schedule fires repeatedly
        callback (Callback): The callback to be called when the scheduler fires
    '''

    def __init__(
        self,
        repeating: bool,
        callback: Callback
    ):
        self.repeating = repeating
        self.callback = callback

    def fire(self) -> None:
        ''' Fires the schedule calling the callback.

        Returns:
            If not using an executor (the callback is called synchronously), `fire()`
            returns the return value of the callback. Otherwise it returns None.
        '''
        return self.callback()

    @abstractmethod
    def tick(self) -> Tuple[bool, Any]: # pylint: disable=no-self-use
        ''' The heartbeat of the schedule to be called periodically.

        Returns:
            A tuple of (True, callback_return_value) if the schedule was fired,
            otherwise (False, None)
        '''


class AtSchedule(Schedule):
    ''' Schedules a task to be executed only once at a specific time.

    The task will be executed at the next tick after the specified datetime.

    Args:
        at (datetime.datetime): When to execute the task
        callback (Callback): The callback to be called when the scheduler fires
    '''

    # pylint: disable=invalid-name
    # Disabled for the `at` parameter

    def __init__(self, at: datetime.datetime, callback: Callback):
        super().__init__(repeating=False, callback=callback)
        self.at_lock = threading.Lock()
        self.fire_lock = threading.Lock()
        self.at = at

    @property
    def at(self) -> datetime.datetime:
        ''' Property accessor for 'at'. '''
        return self._at

    @at.setter
    def at(self, val: datetime.datetime):
        ''' Property setter for 'at'. '''
        with self.at_lock:
            self._at = val
            self._fired = False

    def _do_tick(self):
        now = local_now()
        if not self._fired and self.at is not None and now > self.at:
            res = self.fire()
            self._fired = True
            return (True, res)
        return (False, None)

    def tick(self) -> Tuple[bool, Any]:
        if self.callback.executor:
            with self.fire_lock:
                return self._do_tick()
        return self._do_tick()


class IntervalSchedule(Schedule):
    ''' Schedules a task to be executed at regular time intervals.

    The task will be executed at the first tick and at each tick after
    the specified time interval has passed.

    Args:
        interval (datetime.timedelta): The time interval of the executions
        callback (Callback): The callback to be called when the scheduler fires
    '''

    def __init__(self, interval: datetime.timedelta, callback: Callback):
        super().__init__(repeating=True, callback=callback)
        self.interval = interval
        self._next_fire = None

    def _set_next_fire(self, now):
        while self._next_fire <= now:
            self._next_fire += self.interval

    def tick(self) -> Tuple[bool, Any]:
        now = local_now()
        if not self._next_fire:
            self._next_fire = now
        if now >= self._next_fire:
            res = (True, self.fire())
        else:
            res = (False, None)
        self._set_next_fire(now)
        return res


class OrdinalSchedule(Schedule):
    ''' Schedules a task to be executed at each nth tick.

    At the first tick the task will not be executed.

    Args:
        ordinal (int): Execute the task once in every ordinal number of ticks. An OrdinalSchedule
            with zero ordinal will never fire.
        callback (Callback): The callback to be called when the scheduler fires
    '''

    def __init__(self, ordinal: int, callback: Callback):
        super().__init__(repeating=True, callback=callback)
        if ordinal < 0:
            raise ValueError('ordinal must be greater or equal than zero')
        self.ordinal = ordinal
        self._counter = 0

    def tick(self) -> Tuple[bool, Any]:
        if self.ordinal == 0:
            return (False, None)
        self._counter += 1
        if self._counter == self.ordinal:
            res = (True, self.fire())
            self._counter = 0
            return res
        return (False, None)


class AlarmClock:
    ''' An alarm clock can be used to bundle different schedules and send them
    the tick event at once.

    Args:
        schedules (List[Schedule]): The list of the schedules.
    '''

    # pylint: disable=too-few-public-methods
    # It happens that an alarm clock should only tick:
    # real functionality is implemented by wrapped schedules

    def __init__(self, schedules: List[Schedule]=None):
        self.schedules = schedules or []

    def tick(self) -> None:
        ''' The heartbeat of the alarm clock to be called periodically.

        Will forward the tick to the registered schedules.
        '''
        removables = []
        for schedule in self.schedules:
            fired, _ = schedule.tick()
            if fired and not schedule.repeating:
                removables.append(schedule)
        for schedule in removables:
            self.schedules.remove(schedule)


class BaseTachometer(ABC):
    ''' Abstract base class for tachometers.

    A Tachometer can be used to measure the frequency of recurring events, and periodically report
    statistics about it by calling a callback function with the following signature::

        def stats_callback(timestamp: datetime.datetime, timer: BaseTimer):
            pass

    passing the timestamp of the last event, as well as the `BaseTimer` instance that
    collected the events. You can access the `min()`, `max()`, `sum()` (total processing time)
    and the `len()` (number of measurements) methods of the timer.

    This class is not intended to be instantiated. Use one of the subclasses instead.

    Args:
        timer (BaseTimer): Instance of the BaseTimer subclass that will be used to report events.
        stats_callback (Callable[[datetime.datetime, BaseTimer]):  A callable with the above
            signature that will be called when new statistics is available.
        stats_interval (datetime.timedelta): The interval of the statistics calculation. Defaults
            to one minute.
        executor (Optional[concurrent.futures.Executor]): If specified, callback will be called
            asynchronously using this executor
    '''

    # pylint: disable=too-few-public-methods
    # It happens that a Tachometer should only tick and sometimes call the callback.

    EXPECTED_MAX_FPS = 100

    def __init__(
        self,
        timer: BaseTimer,
        stats_callback: Callable[[datetime.datetime, BaseTimer], None],
        stats_interval: datetime.timedelta = datetime.timedelta(seconds=60),
        executor: Optional[concurrent.futures.Executor] = None
    ):
        self.stats_callback = stats_callback
        self.schedule = IntervalSchedule(
            interval=stats_interval,
            callback=Callback(cb=self._calculate_stats, executor=executor)
        )
        self.timer = timer

    def _calculate_stats(self):
        timestamp = local_now()
        if len(self.timer.intervals) == 0:
            return (False, None)
        res = self.stats_callback(timestamp, self.timer)
        self.timer.intervals.clear()
        return (True, res)


class TickerTachometer(BaseTachometer):
    ''' TickerTachometer is a combination of a Ticker and a Tachometer.

    It reports statistics about the call frequency of the `tick()` method.

    Call the `tick()` method of the tachometer each time an atomic event happens.
    For example, if you are interested in the spastics of the frame processing
    time of your application, call `tick` method each time you process a new
    frame.

    Args:
        stats_callback (Callable[[datetime.datetime, Ticker]):  A callable that will be called
            when new statistics is available.
        stats_interval (datetime.timedelta): The interval of the statistics calculation. Defaults
            to one minute.
        executor (Optional[concurrent.futures.Executor]): If specified, callback will be called
            asynchronously using this executor
    '''

    def __init__(self,
        stats_callback: Callable[[datetime.datetime, Ticker], None],
        stats_interval: datetime.timedelta = datetime.timedelta(seconds=60),
        executor: Optional[concurrent.futures.Executor] = None
    ):
        ticker_intervals = int(self.EXPECTED_MAX_FPS * stats_interval.total_seconds())
        self.ticker = Ticker(max_intervals=ticker_intervals)
        super().__init__(self.ticker, stats_callback, stats_interval, executor)

    def tick(self) -> Tuple[bool, Any]:
        ''' Call this method when a recurring event happens.

        Returns:
            Tuple[bool, Any]: A tuple with these elements:

                - bool: True, if stats_callback was called
                - the return value of stats_callback if it was called, else None
        '''
        self.ticker.tick()
        return self.schedule.tick()


class StopWatchTachometer(BaseTachometer):
    ''' `StopWatchTachometer` is a combination of a StopWatch and a Tachometer.

    It reports statistics about the elapsed time intervals.

    Much like StopWatch, you can use `StopWatchTachometer` as a context manager or as a function
    decorator.

    For example::

        swt = StopWatchTachometer(
            stats_callback=lambda dt, timer: print('Mean interval:', timer.mean()),
            stats_interval=datetime.timedelta(seconds=10)
        )

        for i in range(11):
            with swt:
                print('tick')
                time.sleep(2)

        @swt.measure
        def long_running_func():
            print('tack')
            time.sleep(1.5)

        for i in range(15):
            long_running_func()

    Args:
        stats_callback (Callable[[datetime.datetime, Ticker]):  A callable that will be called
            when new statistics is available.
        stats_interval (datetime.timedelta): The interval of the statistics calculation. Defaults
            to one minute.
        executor (Optional[concurrent.futures.Executor]): If specified, callback will be called
            asynchronously using this executor
    '''

    def __init__(self,
        stats_callback: Callable[[datetime.datetime, Ticker], None],
        stats_interval: datetime.timedelta = datetime.timedelta(seconds=60),
        executor: Optional[concurrent.futures.Executor] = None
    ):
        ticker_intervals = int(self.EXPECTED_MAX_FPS * stats_interval.total_seconds())
        self.stopwatch = StopWatch('tachometer', max_intervals=ticker_intervals)
        super().__init__(self.stopwatch, stats_callback, stats_interval, executor)

    def __enter__(self) -> 'StopWatchTachometer':
        ''' Context manager entry point returning self.'''
        self.stopwatch.__enter__()
        return self

    def __exit__(self, *_) -> None:
        ''' Context manager exit. '''
        self.stopwatch.__exit__()
        self.schedule.tick()

    def measure(self, fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwds):
            self.__enter__()
            fun(*args, **kwds)
            self.__exit__()
        return wrapper
