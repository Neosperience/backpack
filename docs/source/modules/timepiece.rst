.. _timepiece-readme:

Timepiece
---------

Timepiece component includes classes that allow you to quickly time profile the video processing
pipeline. For detailed information, please check the API documentation.

Ticker
^^^^^^

:class:`~backpack.timepiece.Ticker` allows you to calculate statistics of the time intervals
between recurring events. You can use a ticker, for example, to get statistics about how much time
the application spends to process frames.

Example usage:

.. code-block:: python

    import time
    import random
    from backpack.timepiece import Ticker

    ticker = Ticker(max_intervals=5)
    for i in range(10):
        ticker.tick()
        time.sleep(random.random() / 10)
    print(ticker)

This code returns the time interval (in seconds) between the last five
:meth:`~backpack.timepiece.Ticker.tick()` calls, as well as some basic statistics of them::

    <Ticker intervals=[0.0899, 0.0632, 0.0543, 0.0713, 0.0681] min=0.0543 mean=0.0694 max=0.0899>

StopWatch
^^^^^^^^^

With :class:`~backpack.timepiece.StopWatch`, you can measure the execution time of a code block,
even repeatedly, and get statistics about the time spent on different invocations. You can use
:class:`~backpack.timepiece.StopWatch`, for example, to profile the inference time of your machine
learning model or your preprocessing or postprocessing functions. Stopwatches can be organized in
a hierarchy, where the parent watch measures the summary of the time of child watches.

Example usage:

.. code-block:: python

    import time
    import random

    with StopWatch('root') as root:
        with root.child('task1', max_intervals=5) as task1:
            time.sleep(0.01)
            with task1.child('subtask1_1') as subtask1_1:
                time.sleep(0.03)
            with task1.child('subtask1_2'):
                time.sleep(0.07)
            with task1.child('subtask1_3'):
                time.sleep(0.09)
            with subtask1_1:
                time.sleep(0.05)
        for i in range(5)
            with root.child('task2') as task2:
                time.sleep(random.random() / 10)
    print(root)

Results::

    <StopWatch name=root intervals=[0.5416] min=0.5416 mean=0.5416 max=0.5416 children=[
        <StopWatch name=task1 intervals=[0.2505] min=0.2505 mean=0.2505 max=0.2505 children=[
            <StopWatch name=subtask1_1 intervals=[0.0301, 0.0501] min=0.0301 mean=0.0401 max=0.0501>,
            <StopWatch name=subtask1_2 intervals=[0.0701] min=0.0701 mean=0.0701 max=0.0701>,
            <StopWatch name=subtask1_3 intervals=[0.0901] min=0.0901 mean=0.0901 max=0.0901>
        ]>,
        <StopWatch name=task2 intervals=[0.0275, 0.0825, 0.0334, 0.0843, 0.0633] min=0.0275 mean=0.0582 max=0.0843>
    ]>

You can access all interval data, as well as the statistical values using
:class:`~backpack.timepiece.StopWatch` properties.

Schedules
^^^^^^^^^

Schedules allow you to schedule the execution of a function at a later time.

It is important to note that :class:`~backpack.timepiece.Schedule` instances do not intrinsically
have an event loop or use kernel-based timing operations. Instead, call regularly the
:meth:`~backpack.timepiece.Schedule.tick` method of the :class:`~backpack.timepiece.Schedule`, and
the scheduled function will be executed when the next :meth:`~backpack.timepiece.Schedule.tick` is
called after the scheduled time. When developing Panorama applications, you typically call the
:meth:`~backpack.timepiece.Schedule.tick` function in the frame processing loop.

You can also specify a `python executor`_ when creating :class:`~backpack.timepiece.Schedule`
objects. If an executor is specified, the scheduled function will be called asynchronously using
that executor, the :meth:`~backpack.timepiece.Schedule.tick` method can immediately return, and the
scheduled function will be executed in another thread.

.. _`python executor`: https://docs.python.org/3/library/concurrent.futures.html

The following Schedules are available to you:

 - :class:`~backpack.timepiece.AtSchedule`: executes a function at a given time in the future
 - :class:`~backpack.timepiece.IntervalSchedule`: executes a function repeatedly at given intervals
 - :class:`~backpack.timepiece.OrdinalSchedule`: executes a function once in each *n* invocation of
   :meth:`~backpack.timepiece.OrdinalSchedule.tick`.

Finally, :class:`~backpack.timepiece.AlarmClock` allows you to handle a collection of
:class:`~backpack.timepiece.Schedule` instances with the invocation of a single
:meth:`~backpack.timepiece.AlarmClock.tick` method.

Example usage:

.. code-block:: python

    import time, datetime
    from concurrent.futures import ThreadPoolExecutor
    from backpack.timepiece import (
        local_now, AtSchedule, IntervalSchedule, AlarmClock, OrdinalSchedule, Callback
    )

    def get_callback(name, executor):
        return Callback(
            cb=lambda name: print(f'{name} was called at {datetime.datetime.now()}'),
            cbkwargs={'name': name},
            executor=executor
        )

    executor = ThreadPoolExecutor()

    at = local_now() + datetime.timedelta(seconds=3)
    atschedule = AtSchedule(
        at=at,
        callback=get_callback('AtSchedule', executor)
    )

    iv = datetime.timedelta(seconds=1.35)
    ivschedule = IntervalSchedule(
        interval=iv,
        callback=get_callback('IntervalSchedule', executor)
    )

    ordinalschedule = OrdinalSchedule(
        ordinal=17,
        callback=get_callback('OrdinalSchedule', executor),
    )

    alarmclock = AlarmClock([atschedule, ivschedule, ordinalschedule])

    for i in range(25*5):
        alarmclock.tick()
        time.sleep(1/25)

Results::

    IntervalSchedule was called at 2022-02-18 13:08:27.025772+00:00
    OrdinalSchedule was called at 2022-02-18 13:08:27.669900+00:00
    OrdinalSchedule was called at 2022-02-18 13:08:28.354350+00:00
    IntervalSchedule was called at 2022-02-18 13:08:28.395027+00:00
    OrdinalSchedule was called at 2022-02-18 13:08:29.039454+00:00
    OrdinalSchedule was called at 2022-02-18 13:08:29.724104+00:00
    IntervalSchedule was called at 2022-02-18 13:08:29.764723+00:00
    AtSchedule was called at 2022-02-18 13:08:30.046814+00:00
    OrdinalSchedule was called at 2022-02-18 13:08:30.409206+00:00
    IntervalSchedule was called at 2022-02-18 13:08:31.093138+00:00
    OrdinalSchedule was called at 2022-02-18 13:08:31.093451+00:00
    OrdinalSchedule was called at 2022-02-18 13:08:31.776985+00:00


Tachometer
^^^^^^^^^^

A :class:`~backpack.timepiece.Tachometer` combines a :class:`~backpack.timepiece.Ticker` and an
:class:`~backpack.timepiece.IntervalSchedule` to measure the time interval of a recurring event and
periodically report statistics about it. You can use it, for example, to report the frame processing
time statistics to an external service. You can specify the reporting interval and a callback
function that will be called with the timing statistics. You should consider using an *executor*, as
your reporting callback can take a considerable amount of time to finish, and you might not want to
hold up the processing loop synchronously meanwhile.

Example usage:

.. code-block:: python

    import datetime, time, random
    from concurrent.futures import ThreadPoolExecutor
    from backpack.timepiece import Tachometer

    def stats_callback(timestamp, ticker):
        print('timestamp:', timestamp)
        print(f'min: {ticker.min():.4f}, max: {ticker.max():.4f}, '
              f'sum: {ticker.sum():.4f}, num: {ticker.len()}')

    tach = Tachometer(
        stats_callback=stats_callback,
        stats_interval=datetime.timedelta(seconds=2),
        executor=ThreadPoolExecutor()
    )

    for i in range(200):
        tach.tick()
        time.sleep(random.random() / 10)

Results::

    timestamp: 2022-02-18 13:08:34.074238+00:00
    min: 0.0003, max: 0.0979, sum: 2.0156, num: 36
    timestamp: 2022-02-18 13:08:36.102133+00:00
    min: 0.0005, max: 0.0998, sum: 2.0279, num: 40
    timestamp: 2022-02-18 13:08:38.105702+00:00
    min: 0.0005, max: 0.0984, sum: 2.0036, num: 43
    timestamp: 2022-02-18 13:08:40.083832+00:00
    min: 0.0028, max: 0.0975, sum: 1.9781, num: 39


CWTachometer
^^^^^^^^^^^^

:class:`~backpack.timepiece.CWTachometer` is a :class:`~backpack.timepiece.Tachometer` subclass that
reports frame processing time statistics to `AWS CloudWatch Metrics` service. You can use this class
as a drop-in to your frame processing loop. It will give you detailed statistics about the behavior
the timing of your application and you can mount `CloudWatch alarms`_ on this metric to receive
email or SMS notifications when your application stops processing the video for whatever reason.

.. _`AWS CloudWatch Metrics`: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html
.. _`CloudWatch alarms`: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html

To successfully use :class:`~backpack.timepiece.CWTachometer`, you should grant the execution of the
following operations to the Panorama Application IAM Role:

 - ``cloudwatch:PutMetricData``

The following example (a snippet from a Panorama Application implementation) shows you how you can
combine together :class:`~backpack.autoidentity.AutoIdentity` and
:class:`~backpack.timepiece.CWTachometer` to get frame processing time metrics in the CloudWatch
service of your AWS account:

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor
    import boto3
    from backpack.autoidentity import AutoIdentity
    from backpack.cwtacho import CWTachometer

    # You might want to read these values from Panorama application parameters
    service_region = 'us-east-1'
    device_region = 'us-east-1'

    class Application(panoramasdk.node):

        def __init__(self):
            super().__init__()
            self.session = boto3.Session(region_name=service_region)
            self.executor = ThreadPoolExecutor()
            self.auto_identity = AutoIdentity(device_region=device_region)
            self.tacho = CWTachometer(
                namespace='MyPanoramaMetrics',
                metric_name='frame_processing_time',
                dimensions={
                    'application_name': self.auto_identity.application_name or 'unknown',
                    'device_id': self.auto_identity.device_id or 'unknown',
                    'application_instance_id': self.auto_identity.application_instance_id or 'unknown'
                },
                executor=self.executor,
                boto3_session=self.session
            )

        def process_streams(self):

            # call Tachometer
            self.tacho.tick()

            # this  will block until next frame is available
            streams = self.inputs.video_in.get()

            for stream in streams:
                # process stream.image here ...
                pass

            self.outputs.video_out.put(streams)

    def main():
        try:
            app = Application()
            while True:
                app.process_streams()
        except Exception:
            print('Exception during processing loop.')

    main()

For more information, refer to the :ref:`timepiece API documentation <timepiece-api>`.