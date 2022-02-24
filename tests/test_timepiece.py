import unittest
from unittest.mock import patch
from unittest.mock import Mock

from backpack.timepiece import Ticker

# Mock time to control its behavior
time = Mock()

@patch('backpack.timepiece.time')
class TestTicker(unittest.TestCase):
    
    MAX_INTERVALS_CNT = 10
    TEST_INTERVALS_CNT = 20
    
    def setUp(self):
        self.current_time = 0
        
    def _setup_backpack_mock_time(self, backpack_mock_time):
        backpack_mock_time.perf_counter.side_effect = self._mock_time_perf_counter
        time.sleep.side_effect = self._mock_time_sleep

    def _mock_time_sleep(self, secs):
        self.current_time += secs
    
    def _mock_time_perf_counter(self):
        return self.current_time
    
    def _expected_intervals(self, max_intervals_cnt=None, test_intervals_cnt=None):
        max_intervals_cnt = max_intervals_cnt or TestTicker.MAX_INTERVALS_CNT
        test_intervals_cnt = test_intervals_cnt or TestTicker.TEST_INTERVALS_CNT
        return self.test_intervals[-min(max_intervals_cnt, test_intervals_cnt):]
    
    def _do_test(self, max_intervals_cnt=None, test_intervals_cnt=None):
        max_intervals_cnt = max_intervals_cnt or TestTicker.MAX_INTERVALS_CNT
        test_intervals_cnt = test_intervals_cnt or TestTicker.TEST_INTERVALS_CNT
        self.ticker = Ticker(max_intervals=max_intervals_cnt)
        self.test_intervals = [i + 1 for i in range(test_intervals_cnt)]

        for interval in self.test_intervals:
            self.ticker.tick()
            time.sleep(interval)
        self.ticker.tick()

    def test_perf_counter_called(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test()
        self.assertEqual(backpack_mock_time.perf_counter.call_count, len(self.test_intervals) + 1, 
                         'time.perf_counter called incorrect number of times')

    def _do_test_intervals_length(self, max_intervals_cnt, test_intervals_cnt):
        self._do_test(max_intervals_cnt, test_intervals_cnt)
        expected_intervals = self._expected_intervals(max_intervals_cnt, test_intervals_cnt)
        self.assertEqual(len(self.ticker.intervals), len(expected_intervals),
                        'incorrect number of intervals saved')
    
    def test_short_intervals_length(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test_intervals_length(20, 10)

    def test_long_intervals_length(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test_intervals_length(10, 20)
    
    def test_last_intervals_kept(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test()
        res = all(a == b for a, b in zip(self.ticker.intervals, self._expected_intervals()))
        self.assertTrue(res, 'the last intervals are not kept')
        
    def test_min(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test()
        self.assertEqual(self.ticker.min(), min(self._expected_intervals()),
                        'ticker.min() returned incorrect value')

    def test_max(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test()
        self.assertEqual(self.ticker.max(), max(self._expected_intervals()),
                        'ticker.max() returned incorrect value')

    def test_mean_freq(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test()
        expected_intervals = self._expected_intervals()
        expected_mean = sum(expected_intervals) / len(expected_intervals)
        expected_freq = 1 / expected_mean
        self.assertEqual(self.ticker.mean(), expected_mean,
                        'ticker.mean() returned incorrect value')
        self.assertEqual(self.ticker.freq(), expected_freq,
                        'ticker.mean() returned incorrect value')

    def test_no_tick_no_crash(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self.ticker = Ticker(max_intervals=TestTicker.MAX_INTERVALS_CNT)
        self.ticker.min()
        self.ticker.max()
        self.ticker.mean()
        self.ticker.freq()

    def test_repr(self, backpack_mock_time):
        self._setup_backpack_mock_time(backpack_mock_time)
        self._do_test()
        expected_repr = (
            '<Ticker intervals=[11.0000, 12.0000, 13.0000, 14.0000, 15.0000, ...] '
            'min=11.0000 mean=15.5000 max=20.0000>'
        )
        self.assertEqual(repr(self.ticker), expected_repr, 'repr(ticker) returned incorrect value')
