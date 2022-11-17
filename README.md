# Backpack

![pipeline](https://s3.eu-west-1.amazonaws.com/github-ci.experiments.neosperience.com/Neosperience/backpack/build/pipeline.svg?)
[![coverage](https://s3.eu-west-1.amazonaws.com/github-ci.experiments.neosperience.com/Neosperience/backpack/build/coverage.svg?)](https://s3.eu-west-1.amazonaws.com/github-ci.experiments.neosperience.com/Neosperience/backpack/build/coverage/index.html)
[![pylint](https://s3.eu-west-1.amazonaws.com/github-ci.experiments.neosperience.com/Neosperience/backpack/build/pylint.svg?)](https://s3.eu-west-1.amazonaws.com/github-ci.experiments.neosperience.com/Neosperience/backpack/build/lint/pylint.txt)

> Your hiking equipment for an enjoyable Panorama development experience

You can read also the [structured and extended version of this documentation](https://panorama-backpack.readthedocs.io/).

Backpack is a toolset that makes development for AWS Panorama hopefully more enjoyable. AWS Panorama is a machine learning appliance and software development kit that can be used to develop intelligent video analytics and computer vision applications deployed on an edge device. For more information, refer to the [Panorama page](https://aws.amazon.com/panorama/) on the AWS website.

Backpack provides the following modules:

- *AutoIdentity* allows your application to learn more about itself and the host device. It gives access to the Panorama device id, application instance id, application name and description, and other similar information.
- *Timepiece* is a collection of timing and profiling classes that allows you to efficiently measure the frame processing time of your app, time profile different stages of frame processing (preprocessing, model invocation, postprocessing), and send a selected subset of these metrics to AWS CloudWatch to monitor your application in real-time, and even create CloudWatch alarms if your app stops processing frames.
- *SkyLine* provides a framework to re-stream the processed video (annotated by your application) to media endpoints supported by *GStreamer*. *KVSSkyLine* is an implementation of a SkyLine pipeline that lets you send the processed video to AWS Kinesis Video Streams.
- *Annotation* is a unified API for drawing on different backends like the core `panoramasdk.media` class or OpenCV images.

## Installation

Backpack consists of several loosely coupled components, each solving a specific task. Backpack python package is expected to be installed in the docker container of your Panorama application with pip, so you would add the following line to your `Dockerfile`:

```docker
RUN pip install git+https://github.com/neosperience/backpack.git
```

Some components have particular dependencies that can not be installed with the standard pip dependency resolver. For example, if you want to use `KVSSkyLine` to re-stream the output video of your machine learning model to AWS Kinesis Video Streams, you should have several particularly configured libraries in the docker container to make everything work correctly. You will find detailed instructions and `Dockerfile` snippets in the rest of this documentation that will help you put together all dependencies.

## Permissions

Several components of Backpack call AWS services in the account where your Panorama appliance is provisioned. To use these components, you should grant permissions to the Panorama Application IAM Role to use these services. Please refer to [AWS Panorama documentation](https://docs.aws.amazon.com/panorama/latest/dev/permissions-application.html) for more information. For each component, we will list the services required by the component. For example, `AutoIdentity` needs permission to execute the following AWS service operations:

- `panorama:ListApplicationInstances`

To make this component work correctly, you should include the following inline policy in the Panorama Application Role:

```yaml
  Policies:
    - PolicyName: panorama-listapplicationinstances
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Action: 'panorama:ListApplicationInstances'
            Resource: '*'
```

The rest of this readme discusses the different components in Backpack.

## AutoIdentity

When your application's code is running in a Panorama application, there is no official way to know which device is running your app or which deployment version of your app is currently running. `AutoIdentity` queries these details directly by calling AWS Panorama management services based on the UID of your Application that you typically can find in the `AppGraph_Uid` environment variable. When instantiating the `AutoIdentity` object, you should pass the AWS region name where you provisioned the Panorama appliance. You can pass the region name, for example, as an application parameter.

To successfully use AutoIdentity, you should grant the execution of the following operations to the Panorama Application IAM Role:

- `panorama:ListApplicationInstances`

Example usage:

```python
from backpack.autoidentity import AutoIdentity

auto_identity = AutoIdentity(device_region='us-east-1')
print(auto_identity)
```

The code above prints details of the running application in the CloudWatch log stream of your Panorama app, something similar to:

```text
<AutoIdentity
    application_created_time="2022-02-17 16:38:05.510000+00:00"
    application_description="Sample application description"
    application_instance_id="applicationInstance-0123456789abcdefghijklmn"
    application_name="sample_app"
    application_status="RUNNING"
    application_tags={"foo": "bar"}
    device_id="device-0123456789abcdefghijklmn"
    device_name="my_panorama"
>
```

You can access all these details as the properties of the `AutoIdentity` object, for example, with `auto_identity.application_description`.

## Timepiece

Timepiece component includes classes that allow you to quickly time profile the video processing pipeline. For detailed information, please check the API documentation.

### Ticker

`Ticker` allows you to calculate statistics of the time intervals between recurring events. You can use a ticker, for example, to get statistics about how much time the application spends to process frames.

Example usage:

```python
import time
import random
from backpack.timepiece import Ticker

ticker = Ticker(max_intervals=5)
for i in range(10):
    ticker.tick()
    time.sleep(random.random() / 10)
print(ticker)
```

This code returns the time interval (in seconds) between the last five `tick()` calls, as well as some basic statistics of them:

```text
<Ticker intervals=[0.0899, 0.0632, 0.0543, 0.0713, 0.0681] min=0.0543 mean=0.0694 max=0.0899>
```

### StopWatch

With `StopWatch`, you can measure the execution time of a code block, even repeatedly, and get statistics about the time spent on different invocations. You can use `StopWatch`, for example, to profile the inference time of your machine learning model or your preprocessing or postprocessing functions. Stopwatches can be organized in a hierarchy, where the parent watch measures the summary of the time of child watches.

Example usage:

```python
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
```

Results:

```text
<StopWatch name=root intervals=[0.5416] min=0.5416 mean=0.5416 max=0.5416 children=[
    <StopWatch name=task1 intervals=[0.2505] min=0.2505 mean=0.2505 max=0.2505 children=[
        <StopWatch name=subtask1_1 intervals=[0.0301, 0.0501] min=0.0301 mean=0.0401 max=0.0501>,
        <StopWatch name=subtask1_2 intervals=[0.0701] min=0.0701 mean=0.0701 max=0.0701>,
        <StopWatch name=subtask1_3 intervals=[0.0901] min=0.0901 mean=0.0901 max=0.0901>
    ]>,
    <StopWatch name=task2 intervals=[0.0275, 0.0825, 0.0334, 0.0843, 0.0633] min=0.0275 mean=0.0582 max=0.0843>
]>
```

You can access all interval data, as well as the statistical values using `StopWatch` properties.

### Schedules

Schedules allow you to schedule the execution of a function at a later time.

It is important to note that `Schedule` instances do not intrinsically have an event loop or use kernel-based timing operations. Instead, call regularly the `tick()` method of the `Schedule`, and the scheduled function will be executed when the next `tick()` is called after the scheduled time. When developing Panorama applications, you typically call the `tick()` function in the frame processing loop.

You can also specify a [python executor](https://docs.python.org/3/library/concurrent.futures.html) when creating `Schedule` objects. If an executor is specified, the scheduled function will be called asynchronously using that executor, the `tick()` method can immediately return, and the scheduled function will be executed in another thread.

The following Schedules are available to you:

- `AtSchedule`: executes a function at a given time in the future
- `IntervalSchedule`: executes a function repeatedly at given intervals
- `OrdinalSchedule`: executes a function once in each *n* invocation of `tick()`

Finally, `AlarmClock` allows you to handle a collection of `Schedule` instances with the invocation of a single `tick()` method.

Example usage:

```python
import datetime
from concurrent.futures import ThreadPoolExecutor
from backpack.timepiece import (
    local_now, AtSchedule, IntervalSchedule, AlarmClock, OrdinalSchedule
)

cb = lambda name: print(f'{name} was called at {datetime.datetime.now()}')
executor = ThreadPoolExecutor()

at = local_now() + datetime.timedelta(seconds=3)
atschedule = AtSchedule(at=at, callback=cb, cbkwargs={'name': 'AtSchedule'}, executor=executor)

iv = datetime.timedelta(seconds=1.35)
ivschedule = IntervalSchedule(interval=iv, callback=cb, cbkwargs={'name': 'IntervalSchedule'},
                              executor=executor)

ordinalschedule = OrdinalSchedule(ordinal=17, callback=cb, cbkwargs={'name': 'OrdinalSchedule'},
                                  executor=executor)

alarmclock = AlarmClock([atschedule, ivschedule, ordinalschedule])

for i in range(25*5):
    alarmclock.tick()
    time.sleep(1/25)
```

Results:

```text
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
```

### Tachometer

A `Tachometer` combines a `Ticker` and an `IntervalSchedule` to measure the time interval of a recurring event and periodically report statistics about it. You can use it, for example, to report the frame processing time statistics to an external service. You can specify the reporting interval and a callback function that will be called with the timing statistics. You should consider using an *executor*, as your reporting callback can take a considerable amount of time to finish, and you might not want to hold up the processing loop synchronously meanwhile.

Example usage:

```python
import datetime
import random
from concurrent.futures import ThreadPoolExecutor
from backpack.timepiece import Tachometer

def stats_callback(timestamp, min_proc_time, max_proc_time, sum_proc_time, num_events):
    print('timestamp:', timestamp)
    print(f'min: {min_proc_time:.4f}, max: {max_proc_time:.4f}, '
          f'sum: {sum_proc_time:.4f}, num: {num_events}')

tach = Tachometer(stats_callback, datetime.timedelta(seconds=2))

for i in range(200):
    tach.tick()
    time.sleep(random.random() / 10)

```

Results:

```text
timestamp: 2022-02-18 13:08:34.074238+00:00
min: 0.0003, max: 0.0979, sum: 2.0156, num: 36
timestamp: 2022-02-18 13:08:36.102133+00:00
min: 0.0005, max: 0.0998, sum: 2.0279, num: 40
timestamp: 2022-02-18 13:08:38.105702+00:00
min: 0.0005, max: 0.0984, sum: 2.0036, num: 43
timestamp: 2022-02-18 13:08:40.083832+00:00
min: 0.0028, max: 0.0975, sum: 1.9781, num: 39
```

### CWTachometer

`CWTachometer` is a `Tachometer` subclass that reports frame processing time statistics to [AWS CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html) service. You can use this class as a drop-in to your frame processing loop. It will give you detailed statistics about the behavior the timing of your application and you can mount [CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html) on this metric to receive email or SMS notifications when your application stops processing the video for whatever reason.

To successfully use `CWTachometer`, you should grant the execution of the following operations to the Panorama Application IAM Role:

- `cloudwatch:PutMetricData`

The following example (a snippet from a Panorama Application implementation) shows you how you can combine together `AutoIdentity` and `CWTachometer` to get frame processing time metrics in the CloudWatch service of your AWS account:

```python
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
```

## SkyLine

As you may know, the only official way to get visual feedback on the correct functionality of your Panorama application is to physically connect a display to the HDMI port of the Panorama appliance. When connected, the display will show the output video stream of a single application deployed on the device. However, physically accessing the appliance is not always feasible. SkyLine allows you to re-stream the output video of your Panorama application to an external service, for example to [AWS Kinesis Video Streams](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/what-is-kinesis-video.html). This can be very convenient to remotely monitor your application.

### Warning notes about using SkyLine

Even if SkyLine is a very helpful tool, using it might arise two concerns that you should consider carefully. For the same reason we discourage using SkyLine in a production environment: it is principally a development aid or at most a debugging tool.

The first concern is of technical nature. Currently the application code in a Panorama app does not have direct access to the onboard GPU, thus all video encoding codecs used by SkyLine run on the CPU of the device. This could take precious computing time from the CPUs that occupy with streaming the output instead of processing the video. We measured that streaming a single output stream with SkyLine could require anything between 10-30% of the CPU capacity of the device.

The second concern regards data protection. The Panorama appliance is designed so to strongly protect the video streams being processed: it has even two ethernet interfaces to physically separate the network of the video cameras (typically a closed-circuit local area network) and the Internet access of the device. Using SkyLine you might effectively relay the video stream from the protected, closed-circuit camera network to the public Internet. For this reason, you should carefully examine the data protection requirements of your application and the camera network before integrating SkyLine.

### How does it work?

Technically speaking, SkyLine instantiates a [GStreamer pipeline](https://gstreamer.freedesktop.org/documentation/application-development/introduction/basics.html) with an [appsrc](https://gstreamer.freedesktop.org/documentation/app/appsrc.html) element at the head. An [OpenCV VideoWriter](https://docs.opencv.org/4.5.5/dd/d43/tutorial_py_video_display.html) is configured to write to the `appsrc` element: instead of saving the consecutive frames to a video file, it streams to the output sink. When opening the `VideoWriter` instance, the user should specify the frame width and height, as well as the frame rate of the output stream. You can manually specify these parameters or let SkyLine infer these values from the input dimensions and the frequency you send new frames to it. If using this auto-configuration feature, some frames (by default 100) will be discarded at the beginning of the streaming, as they will be used to calculate statistics of the frame rate and measure the frame dimensions. This phase is referred to as the "warmup" state of SkyLine. If later on, you send frames of different dimensions compared to the expected width and height, SkyLine will redimension the input, but this has a performance penalty of the pipeline. You are also expected to send new frames to SkyLine with the frequency specified in the frame-per-second parameter. If you send frames slower or faster, the KVS video fragments get out of sync and you won't be able to play back the video continuously.

### Configuring the Panorama Application Docker container

SkyLine depends on a set of custom compiled external libraries. You should have all these libraries compiled and configured correctly in your application's docker container in order to make `SkyLine` work correctly. These libraries include:

- GStreamer 1.0 installed with standard plugins pack, libav, tools, and development libraries
- OpenCV 4.2.0, compiled with GStreamer support and Python bindings
- numpy (it is typically installed by the base docker image of your Panorama application)

Furthermore, if you want to use `KVSSkyLine`, the `SkyLine` implementation that streams the video to Kinesis Video Streams, you will need also the following libraries:

- Amazon Kinesis Video Streams (KVS) Producer SDK compiled with GStreamer plugin support
- Environment variable GST_PLUGIN_PATH configured to point to the directory where the compiled
  binaries of KVS Producer SDK GStreamer plugin is placed
- Environment variable LD_LIBRARY_PATH including the open-source third-party dependencies
  compiled by KVS Producer SDK
- boto3 (it is typically installed by the base docker image of your Panorama application)

We provide a sample Dockerfile in the examples folder that shows you how to install correctly these libraries in your Docker container. In most cases, it should be enough to copy the relevant sections from the sample to your application's Dockerfile. The first time you compile the docker container, it might take up to one hour to correctly compile all libraries.

### Using KVSSkyLine

Compared to the `SkyLine` base class, `KVSSkyLine` adds an additional element to the pipeline: the Amazon Kinesis Video Streams (KVS) Producer library, wrapped in a GStreamer sink element. KVS Producer needs AWS credentials to function correctly: it does not use automatically the credentials associated with the Panorama Application Role. You have different options to provide credentials using `KVSCredentialsHandler` subclasses, provided in the `kvs` module. For testing purposes, you can create an IAM user in your AWS account that has the privileges only to the following operations to write media to KVS:

- `kinesisvideo:DescribeStream`
- `kinesisvideo:GetStreamingEndpoint`
- `kinesisvideo:PutMedia`

You should configure this user to have programmatic access to AWS resources, and get the AWS Access Key and Secret Key pair of the user. These are so-called static credentials that do not expire. You can create a `KVSInlineCredentialsHandler` or `KVSEnvironmentCredentialsHandler` instance to pass these credentials to KVS Producer Plugin directly in the GStreamer pipeline definition, or as environment variables. However as these credentials do not expire, it is not recommended to use this setting in a production environment. Even in a development and testing environment, you should take the appropriate security measures to protect these credentials: never hard code them in the source code. Instead, use AWS Secret Manager or a similar service to provision these parameters.

`KVSSkyLine` can use also the Panorama Application Role to pass the application's credentials to KVS Producer. These credentials are temporary, meaning that they expire within a couple of hours, and they should be renewed. The Producer library expects temporary credentials in a text file. `KVSFileCredentialsHandler` takes manages the renewal of the credentials and periodically updates the text file with the new credentials. You should always test your Panorama application - KVS integration that it still works when the credentials are refreshed. This means letting run your application for several hours and periodically checking if it still streams the video to KVS. You will also find diagnostic information in the CloudWatch logs of your application when the credentials were renewed.

`KvsSkyLine` needs also two correctly configured environment variables to make GStreamer find the KVS Producer plugin. The name of these variables are `GST_PLUGIN_PATH` and `LD_LIBRARY_PATH`. They point to the folder where the KVS Producer binary and its 3rd party dependencies can be found. If you've used the example Dockerfile provided, the correct values of these variables are written to a small configuration file at `/panorama/.env`. You should pass the path of this file to `KvsSkyLine` or otherwise ensure that these variables contain the correct value.

At instantiation time, you should pass at least the AWS region name where your stream is created, the name of the stream, and a credentials handler instance. If you want to configure manually the frame rate and the dimensions of the frames, you should also pass them here: if both are specified, the warmup period will be skipped and your first frame will be sent directly to KVS. When you are ready to send the frames, you should call the `start_streaming` method: this will open the GStreamer pipeline. After this method is called, you are expected to send new frames to the stream calling the `put` method periodically, with the frequency of the frame rate specified, or inferred by `KvsSkyLine`. You can stop and restart streaming any number of times on the same `KvsSkyLine` instance.

Example usage:

```python
import panoramasdk
from backpack.kvs import KVSSkyLine, KVSFileCredentialsHandler

# You might want to read these values from Panorama application parameters
stream_region = 'us-east-1'
stream_name = 'panorama-video'

# The example Dockerfile writes static configuration variables to this file
# If you change the .env file path in the Dockerfile, you should change it also here
DOTENV_PATH = '/panorama/.env'

class Application(panoramasdk.node):

    def __init__(self):
        super().__init__()
        # ...
        credentials_handler = KVSFileCredentialsHandler()
        self.skyline = KVSSkyLine(
            stream_region=stream_region,
            stream_name=stream_name,
            credentials_handler=credentials_handler,
            dotenv_path=DOTENV_PATH
        )
        # This call opens the streaming pipeline:
        self.skyline.start_streaming()

    # called from video processing loop:
    def process_streams(self):
        streams = self.inputs.video_in.get()

        for idx, stream in enumerate(streams):

            # Process the stream, for example with:
            # self.process_media(stream)

            # TODO: eventually multiplex streams to a single frame
            if idx == 0:
                self.skyline.put(stream.image)
```

If everything worked well, you can watch the restreamed video in the [Kinesis Video Streams page](https://console.aws.amazon.com/kinesisvideo/home) of the AWS console.

## Annotations

*Annotations* and *annotation drivers* provide a unified way to draw annotations on different rendering backends. Currently, two annotation drivers are implemented:

- `PanoramaMediaAnnotationDriver` allows you to draw on `panoramasdk.media` object, and
- `OpenCVImageAnnotationDriver` allows you to draw on an OpenCV image (numpy array) object.

Two types of annotations can be drawn: labels and rectangles. Not all annotation drivers necessarily implement all features specified by annotations, for example, one driver might decide to ignore colors.

### Using annotations

You can create one or more annotation driver instances at the beginning of the video frame processing loop, depending on the available backends. During the process of a single frame, you are expected to collect all annotations to be drawn on the frame in a python collection (for example, in a `list`). When the processing is finished, you can call the `render` method on any number of drivers, passing the same collection of annotations. All coordinates used in annotation are normalized to the range of `[0; 1)`.

Example usage:

```python
import panoramasdk
from backpack.geometry import Point
from backpack.annotation import (
    LabelAnnotation, RectAnnotation, TimestampAnnotation,
)

from backpack.annotation.opencv import OpenCVImageAnnotationDriver
from backpack.annotation.panorama import PanoramaMediaAnnotationDriver

class Application(panoramasdk.node):

    def __init__(self):
        super().__init__()
        # self.skyline = ...
        self.panorama_driver = PanoramaMediaAnnotationDriver()
        self.cv2_driver = OpenCVImageAnnotationDriver()

    # called from video processing loop:
    def process_streams(self):
        streams = self.inputs.video_in.get()
        for idx, stream in enumerate(streams):
            annotations = [
                TimestampAnnotation(),
                RectAnnotation(point1=Point(0.1, 0.1), point2=Point(0.9, 0.9)),
                LabelAnnotation(point=Point(0.5, 0.5), text='Hello World!')
            ]
            self.panorama_driver.render(annotations, stream)

            # TODO: eventually multiplex streams to a single frame
            if idx == 0:
                rendered = self.cv2_driver.render(annotations, stream.image.copy())
                # self.skyline.put(rendered)
```
