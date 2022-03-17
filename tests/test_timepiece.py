import unittest
from unittest.mock import patch, Mock, PropertyMock
import datetime

from backpack.timepiece import (
    local_now, local_dt, panorama_timestamp_to_datetime,
    Ticker, StopWatch, Callback,
    AtSchedule, IntervalSchedule, OrdinalSchedule, AlarmClock,
    Tachometer
)

# Mock time to control its behavior
time = Mock()

MAX_INTERVALS_CNT = 10
TEST_INTERVALS_CNT = 20


class TestGlobal(unittest.TestCase):
    
    def test_local_now(self):
        now = local_now()
        self.assertTrue(now.tzinfo)
        self.assertEqual(now.tzinfo.__class__.__name__, 'tzlocal')
        
    def test_local_dt(self):
        local = local_dt(datetime.datetime.now())
        self.assertTrue(local.tzinfo)
        self.assertEqual(local.tzinfo.__class__.__name__, 'tzlocal')

    def test_panorama_timestamp_to_datetime(self):
        ts = (1645735796, 142984)
        dt = panorama_timestamp_to_datetime(ts)
        expected_dt = datetime.datetime(2022, 2, 24, 20, 49, 56, 142984)
        self.assertEqual(dt, expected_dt)

@patch('backpack.timepiece.time')
class TestTicker(unittest.TestCase):
    
    def setUp(self):
        self.current_time = 0
        self.ticker = None
        self.test_intervals = None
        
    def _setup_mocks(self, backpack_mock_time):
        def _mock_time_sleep(secs):
            self.current_time += secs
        def _mock_time_perf_counter():
            return self.current_time
        backpack_mock_time.perf_counter.side_effect = _mock_time_perf_counter
        time.sleep.side_effect = _mock_time_sleep
    
    def _expected_intervals(self, max_intervals_cnt=None, test_intervals_cnt=None):
        max_intervals_cnt = max_intervals_cnt or MAX_INTERVALS_CNT
        test_intervals_cnt = test_intervals_cnt or TEST_INTERVALS_CNT
        return self.test_intervals[-min(max_intervals_cnt, test_intervals_cnt):]
    
    def _do_test(self, max_intervals_cnt=None, test_intervals_cnt=None):
        max_intervals_cnt = max_intervals_cnt or MAX_INTERVALS_CNT
        test_intervals_cnt = test_intervals_cnt or TEST_INTERVALS_CNT
        self.ticker = Ticker(max_intervals=max_intervals_cnt)
        self.test_intervals = [i + 1 for i in range(test_intervals_cnt)]

        for interval in self.test_intervals:
            self.ticker.tick()
            time.sleep(interval)
        self.ticker.tick()

    def test_perf_counter_called(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        self.assertEqual(backpack_mock_time.perf_counter.call_count, len(self.test_intervals) + 1, 
                         'time.perf_counter called incorrect number of times')

    def _do_test_intervals_length(self, max_intervals_cnt, test_intervals_cnt):
        self._do_test(max_intervals_cnt, test_intervals_cnt)
        expected_intervals = self._expected_intervals(max_intervals_cnt, test_intervals_cnt)
        self.assertEqual(len(self.ticker.intervals), len(expected_intervals),
                        'incorrect number of intervals saved')
    
    def test_short_intervals_length(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test_intervals_length(20, 10)

    def test_long_intervals_length(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test_intervals_length(10, 20)
    
    def test_last_intervals_kept(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        res = all(a == b for a, b in zip(self.ticker.intervals, self._expected_intervals()))
        self.assertTrue(res, 'the last intervals are not kept')
        
    def test_min(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        self.assertEqual(self.ticker.min(), min(self._expected_intervals()),
                        'ticker.min() returned incorrect value')

    def test_max(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        self.assertEqual(self.ticker.max(), max(self._expected_intervals()),
                        'ticker.max() returned incorrect value')

    def test_sum(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        self.assertEqual(self.ticker.sum(), sum(self._expected_intervals()),
                        'ticker.sum() returned incorrect value')

    def test_len(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        self.assertEqual(self.ticker.len(), len(self._expected_intervals()),
                        'ticker.len() returned incorrect value')
        
    def test_mean_freq(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        expected_intervals = self._expected_intervals()
        expected_mean = sum(expected_intervals) / len(expected_intervals)
        expected_freq = 1 / expected_mean
        self.assertEqual(self.ticker.mean(), expected_mean,
                        'ticker.mean() returned incorrect value')
        self.assertEqual(self.ticker.freq(), expected_freq,
                        'ticker.mean() returned incorrect value')

    def test_no_tick_no_crash(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self.ticker = Ticker(max_intervals=MAX_INTERVALS_CNT)
        self.ticker.min()
        self.ticker.max()
        self.ticker.mean()
        self.ticker.freq()

    def test_reset(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        self.assertEqual(
            len(self.ticker.intervals), min(len(self.test_intervals), MAX_INTERVALS_CNT)
        )
        self.ticker.reset()
        self.assertEqual(len(self.ticker.intervals), 0)

    def test_repr(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self._do_test()
        expected_repr = (
            '<Ticker intervals=[11.0000, 12.0000, 13.0000, 14.0000, 15.0000, ...] '
            'min=11.0000 mean=15.5000 max=20.0000>'
        )
        self.assertEqual(repr(self.ticker), expected_repr, 'repr(ticker) returned incorrect value')


class TestStopWatchBase(unittest.TestCase):
    
    def setUp(self):
        self.current_time = 0
        self.stopwatch = StopWatch(name='testwatch', max_intervals=MAX_INTERVALS_CNT)
        self.childwatch = self.stopwatch.child('childwatch')
        self.assertIsInstance(self.childwatch, StopWatch)

    def _setup_mocks(self, backpack_mock_time):
        backpack_mock_time.perf_counter.side_effect = self._mock_time_perf_counter
        time.sleep.side_effect = self._mock_time_sleep
    
    def test_new_child_no_interval(self):
        self.assertEqual(self.childwatch.intervals.maxlen, self.stopwatch.intervals.maxlen)

    def test_new_child_new_interval(self):
        childwatch2 = self.stopwatch.child('childwatch2', max_intervals=13)
        self.assertIsInstance(childwatch2, StopWatch)
        self.assertEqual(childwatch2.intervals.maxlen, 13)

    def test_existing_child(self):
        childwatch2 = self.stopwatch.child('childwatch')
        self.assertIs(self.childwatch, childwatch2)

    def test_parent(self):
        self.assertTrue(self.stopwatch in self.childwatch.parents())

    def test_level(self):
        self.assertEqual(self.stopwatch.level, 0)
        self.assertEqual(self.childwatch.level, 1)

    def test_root_no_parents(self):
        self.assertEqual(list(self.stopwatch.parents()), [])

    def test_fullname(self):
        self.assertEqual(self.childwatch.full_name(), 'testwatch.childwatch')


@patch('backpack.timepiece.time')
class TestStopWatchContext(unittest.TestCase):

    def setUp(self):
        self.current_time = 0

    def _setup_mocks(self, backpack_mock_time):
        def _mock_time_sleep( secs):
            self.current_time += secs
        def _mock_time_perf_counter():
            return self.current_time
        backpack_mock_time.perf_counter.side_effect = _mock_time_perf_counter
        time.sleep.side_effect = _mock_time_sleep

    def test_context(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        with StopWatch('root') as root:
            time.sleep(3)
        self.assertEqual(root.intervals[0], 3)

    def _do_complex(self):
        with StopWatch('root') as root:
            with root.child('task1', max_intervals=5) as task1:
                time.sleep(1)
                with task1.child('subtask1_1') as subtask1_1:
                    time.sleep(3)
                with task1.child('subtask1_2'):
                    time.sleep(7)
                with task1.child('subtask1_3'):
                    time.sleep(9)
                with subtask1_1:
                    time.sleep(5)
            for i in range(5):
                with root.child('task2') as task2:
                    time.sleep(i + 1)
        return root

    def test_complex(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        root = self._do_complex()
        self.assertEqual(root.intervals[0], 1+3+7+9+5+1+2+3+4+5)
        self.assertEqual(len(root.child('task1').children), 3)
        self.assertEqual(len(root.child('task2').intervals), 5)
        self.assertEqual(root.child('task2').min(), 1)
        self.assertEqual(root.child('task2').max(), 5)
        self.assertEqual(root.child('task2').mean(), 3)
        
    def test_repr(self, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        root = self._do_complex()
        expected_repr = '''\
<StopWatch name=root intervals=[40.0000] min=40.0000 mean=40.0000 max=40.0000 children=[
    <StopWatch name=task1 intervals=[25.0000] min=25.0000 mean=25.0000 max=25.0000 children=[
        <StopWatch name=subtask1_1 intervals=[3.0000, 5.0000] min=3.0000 mean=4.0000 max=5.0000>, 
        <StopWatch name=subtask1_2 intervals=[7.0000] min=7.0000 mean=7.0000 max=7.0000>, 
        <StopWatch name=subtask1_3 intervals=[9.0000] min=9.0000 mean=9.0000 max=9.0000>
    ]>, 
    <StopWatch name=task2 intervals=[1.0000, 2.0000, 3.0000, 4.0000, 5.0000] min=1.0000 mean=3.0000 max=5.0000>
]>'''
        self.assertEqual(repr(root), expected_repr)


@patch('backpack.timepiece.local_now')
class TestAtSchedule(unittest.TestCase):
    
    def setUp(self):
        self.fire = datetime.datetime(2022, 2, 22, 22, 22, 22)
        self.before_fire = self.fire - datetime.timedelta(seconds=1)
        self.after_fire = self.fire + datetime.timedelta(seconds=1)
        self.callback = Mock()
        self.cbargs = (1, 2, 3)
        self.cbkwargs = {'foo': 'bar'}
        self.at_schedule = AtSchedule(
            at=self.fire, 
            callback=Callback(cb=self.callback, cbargs=self.cbargs, cbkwargs=self.cbkwargs)
        )
    
    def test_no_fire_before(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.before_fire
        fired, _ = self.at_schedule.tick()
        self.assertIs(fired, False, 'reported fire when it should not')
        self.callback.assert_not_called()

    def test_fire_after(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.after_fire
        fired, _ = self.at_schedule.tick()
        self.assertIs(fired, True, 'reported no fire when it should')
        self.callback.assert_called()

    def test_no_double_fire(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.after_fire
        res = self.at_schedule.tick()
        backpack_mock_local_now.return_value = self.after_fire + datetime.timedelta(seconds=1)
        fired, _ = self.at_schedule.tick()
        self.assertIs(fired, False, 'reported fire second time')
        self.callback.assert_called_once()

    def test_callback_args(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.after_fire
        self.at_schedule.tick()
        self.callback.assert_called_once_with(*self.cbargs, **self.cbkwargs)

    def test_with_executor(self, backpack_mock_local_now):
        executor = Mock()
        cb = Callback(cb=self.callback, cbargs=self.cbargs, cbkwargs=self.cbkwargs,executor=executor)
        at_schedule = AtSchedule(at=self.fire, callback=cb)
        backpack_mock_local_now.return_value = self.after_fire
        fired, _ = at_schedule.tick()
        self.assertIs(fired, True, 'reported no fire when it should')
        executor.submit.assert_called_once_with(unittest.mock.ANY, *self.cbargs, **self.cbkwargs)


@patch('backpack.timepiece.local_now')
class TestIntervalSchedule(unittest.TestCase):

    def setUp(self):
        self.start = datetime.datetime(2022, 2, 22, 22, 22, 0)
        self.interval = datetime.timedelta(seconds=5)
        self.callback = Mock()
        self.cbargs = (1, 2, 3)
        self.cbkwargs = {'foo': 'bar'}
        self.interval_schedule = IntervalSchedule(
            interval=self.interval,
            callback=Callback(cb=self.callback, cbargs=self.cbargs, cbkwargs=self.cbkwargs)
        )

    def test_first_fire(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.start
        fired, _ = self.interval_schedule.tick()
        self.assertIs(fired, True, 'reported no fire when it should')
        self.callback.assert_called()

    def test_no_double_fire(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.start
        self.interval_schedule.tick()
        fired, _ = self.interval_schedule.tick()
        self.assertIs(fired, False, 'reported fire second time')
        self.assertEqual(self.callback.call_count, 1, 'did not fire once')

    def test_no_early_call(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.start
        self.interval_schedule.tick()
        backpack_mock_local_now.return_value = self.start + datetime.timedelta(seconds=3)
        fired, _ = self.interval_schedule.tick()
        self.assertIs(fired, False, 'reported fire early')
        self.assertEqual(self.callback.call_count, 1, 'did not fire once')

    def test_interval_call(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.start
        self.interval_schedule.tick()
        backpack_mock_local_now.return_value = self.start + self.interval
        fired, _ = self.interval_schedule.tick()
        self.assertIs(fired, True, 'did not fire second time')
        self.assertEqual(self.callback.call_count, 2, 'did not fire two times')

    def test_second_call_schedule(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.start
        self.interval_schedule.tick()
        backpack_mock_local_now.return_value = self.start + datetime.timedelta(seconds=8)
        fired, _ = self.interval_schedule.tick()
        self.assertIs(fired, True, 'did not fire second time')
        # even if last tick was at 8s, next call should be scheduled at 10s (not 13s)
        backpack_mock_local_now.return_value = self.start + datetime.timedelta(seconds=11)
        fired, _ = self.interval_schedule.tick()
        self.assertIs(fired, True, 'did not fire third time')
        self.assertEqual(self.callback.call_count, 3, 'did not fire three times')

    def test_callback_args(self, backpack_mock_local_now):
        backpack_mock_local_now.return_value = self.start
        self.interval_schedule.tick()
        self.callback.assert_called_once_with(*self.cbargs, **self.cbkwargs)


class TestOrdinalSchedule(unittest.TestCase):

    def setUp(self):
        self.ordinal = 3
        self.callback = Mock()
        self.cbargs = (1, 2, 3)
        self.cbkwargs = {'foo': 'bar'}
        self.ordinal_schedule = OrdinalSchedule(
            ordinal=self.ordinal,
            callback=Callback(cb=self.callback, cbargs=self.cbargs, cbkwargs=self.cbkwargs)
        )

    def test_no_first_call(self):
        fired, _ = self.ordinal_schedule.tick()
        self.assertFalse(fired, 'reported fire when it should not')
        self.callback.assert_not_called()

    def test_called_in_order(self):
        self.ordinal_schedule.tick()
        fired, _ = self.ordinal_schedule.tick()
        self.assertIs(fired, False, 'reported fire when it should not')
        self.callback.assert_not_called()
        fired, _ = self.ordinal_schedule.tick()
        self.assertIs(fired, True, 'did not report fire when it should')
        self.callback.assert_called()

    def test_zero_ordinal(self):
        zero_ordinal_schedule = OrdinalSchedule(
            ordinal=0, 
            callback=Callback(cb=self.callback, cbargs=self.cbargs, cbkwargs=self.cbkwargs)
        )
        zero_ordinal_schedule.tick()
        zero_ordinal_schedule.tick()
        fired, _ = zero_ordinal_schedule.tick()
        self.assertIs(fired, False, 'reported fire when it should not')
        self.callback.assert_not_called()

    def test_negative_ordinal(self):
        with self.assertRaises(ValueError):
            zero_ordinal_schedule = OrdinalSchedule(
                ordinal=-1, 
                callback=Callback(cb=self.callback, cbargs=self.cbargs, cbkwargs=self.cbkwargs)
            )


class TestAlarmClock(unittest.TestCase):

    def setUp(self):
        self.schedule1 = Mock()
        self.schedule1.tick.return_value = (True, None)
        type(self.schedule1).repeating = PropertyMock(return_value=True)
        self.schedule2 = Mock()
        self.schedule2.tick.return_value = (True, None)
        type(self.schedule2).repeating = PropertyMock(return_value=False)
        self.alarm_clock = AlarmClock([self.schedule1, self.schedule2])

    def test_call_every_schedule(self):
        self.alarm_clock.tick()
        self.schedule1.tick.assert_called()
        self.schedule2.tick.assert_called()

    def test_non_repeating_removed(self):
        self.alarm_clock.tick()
        self.alarm_clock.tick()
        self.assertEqual(self.schedule1.tick.call_count, 2)
        self.assertEqual(self.schedule2.tick.call_count, 1)
        self.assertFalse(self.schedule2 in self.alarm_clock.schedules)


@patch('backpack.timepiece.time')
@patch('backpack.timepiece.local_now')
class TestTachometer(unittest.TestCase):
    
    def setUp(self):
        self.stats_callback = Mock(side_effect=self._stats_callback)
        self.stats_interval = datetime.timedelta(seconds=60)
        self.tachometer = Tachometer(
            stats_callback=self.stats_callback,
            stats_interval=self.stats_interval
        )
        self.start = datetime.datetime(2022, 2, 22, 22, 22, 0)
        self.current_perf_time = 0
        
    def _stats_callback(self, timestamp, ticker):
        self.stats_callback_timestamp = timestamp
        self.stats_callback_ticker = ticker
        self.stats_callback_ticker_intervals = ticker.intervals.copy()

    def _setup_mocks(self, backpack_mock_time):
        def _mock_time_sleep( secs):
            self.current_perf_time += secs
        def _mock_time_perf_counter():
            return self.current_perf_time
        backpack_mock_time.perf_counter.side_effect = _mock_time_perf_counter
        time.sleep.side_effect = _mock_time_sleep
    
    def test_init(self, backpack_mock_local_now, backpack_mock_time):
        self.assertIsInstance(self.tachometer.ticker, Ticker)
        min_interval_len = Tachometer.EXPECTED_MAX_FPS * self.stats_interval.total_seconds()
        self.assertTrue(self.tachometer.ticker.intervals.maxlen >= min_interval_len)

    def test_first_tick_no_stats(self, backpack_mock_local_now, backpack_mock_time):
        backpack_mock_local_now.return_value = self.start
        fired, (cb_fired, res) = self.tachometer.tick()
        self.assertIs(cb_fired, False, 'Stats callback was reported to be called')
        self.stats_callback.assert_not_called()

    def test_stats_called(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        for i in range(60 + 1):
            backpack_mock_local_now.return_value = self.start + datetime.timedelta(seconds=i)
            tick_res = self.tachometer.tick()
            time.sleep(1)
        fired, cb_fired = tick_res
        self.assertIs(cb_fired[0], True, 'Stats callback was not reported to be called')
        self.stats_callback.assert_called()
        args, _ = self.stats_callback.call_args
        self.assertEqual(args[0], self.start + datetime.timedelta(seconds=60), 
                         'Stats callback was called with incorrect timestamp')
        self.assertIsInstance(args[1], Ticker, 'Stats callback was not called Ticker instance')
        self.assertEqual(len(self.stats_callback_ticker_intervals), 60, 
                         'Stast callback Ticker has incorrect number of intervals')
