# Example Dockerfile that installs all required dependencies for KVSTelescope

FROM public.ecr.aws/panorama/panorama-application

ENV DEBIAN_FRONTEND=noninteractive

# Install build tools and gstreamer

RUN apt-get update -y && \
    apt-get install -y libgstreamer1.0-0 \
            build-essential cmake m4 git \
            pkg-config python3.7-dev \
            gstreamer1.0-plugins-base \
            gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad \
            gstreamer1.0-plugins-ugly \
            gstreamer1.0-libav \
            gstreamer1.0-doc \
            gstreamer1.0-tools \
            libgstreamer1.0-dev \
            libgstreamer-plugins-base1.0-dev \
            protobuf-compiler \
            libgtk2.0-dev \
            ocl-icd-opencl-dev \
            libgirepository1.0-dev

# Install GLib python bindings
RUN python3 -m pip install PyGObject --ignore-installed

# Fix GLib libraries path and numpy includes path
RUN ln -s $(python3 -c "import numpy as np; print(np.__path__[0])")/core/include/numpy /usr/include/numpy

# Clone OpenCV repo

RUN mkdir -p /opt && \
    git clone https://github.com/opencv/opencv.git --branch 4.2.0 /opt/opencv
WORKDIR /opt/opencv

# Build OpenCV

RUN mkdir -p /opt/opencv/build
WORKDIR /opt/opencv/build

ENV PYTHON_EXECUTABLE=/usr/bin/python3

RUN PYTHON3_INCLUDE_DIR=$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") && \
    PYTHON3_PACKAGES_PATH=$(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") && \
    mkdir -p $PYTHON3_INCLUDE_DIR && \
    mkdir -p $PYTHON3_PACKAGES_PATH && \
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
        -D INSTALL_PYTHON_EXAMPLES=OFF \
        -D INSTALL_C_EXAMPLES=OFF \
        -D PYTHON2_EXECUTABLE=$(which python) \
        -D PYTHON_EXECUTABLE=$(which python3) \
        -D PYTHON3_EXECUTABLE=$(which python3) \
        -D PYTHON3_INCLUDE_DIR=$PYTHON3_INCLUDE_DIR \
        -D PYTHON3_PACKAGES_PATH=$PYTHON3_PACKAGES_PATH \
        -D PYTHON_DEFAULT_EXECUTABLE=$(which python3) \
        -D PYTHON3_LIBRARY=$PYTHON3_PACKAGES_PATH \
        -D BUILD_NEW_PYTHON_SUPPORT=ON \
        -D BUILD_opencv_python3=ON \
        -D HAVE_opencv_python3=ON \
        -D BUILD_opencv_python2=OFF \
        -D BUILD_TESTS=OFF \
        -D DBUILD_PERF_TESTS=OFF \
        -D CMAKE_INSTALL_PREFIX=$(python3 -c "import sys; print(sys.prefix)") \
        -D WITH_GSTREAMER=ON \
        -D BUILD_EXAMPLES=OFF \
        -D WITH_GTK=OFF \
        ..
RUN make -j $(($(nproc) <= 4 ? $(nproc) : 4))

# Install OpenCV

RUN make install
RUN ldconfig

ENV LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1
ENV PYTHONPATH=/usr/lib/python3.7/site-packages

# Create GStreamer cache directory
RUN mkdir -p /root/.cache/gstreamer-1.0/

WORKDIR /
RUN mkdir -p /panorama



# ###### Optional section if you want to use backpack.kvs ######

# Download Kinesis Video Streams producer C++ SDK

WORKDIR /opt
RUN git clone https://github.com/awslabs/amazon-kinesis-video-streams-producer-sdk-cpp.git

# Build KVS producer C++ SDK

RUN mkdir -p /opt/amazon-kinesis-video-streams-producer-sdk-cpp/build
WORKDIR /opt/amazon-kinesis-video-streams-producer-sdk-cpp/build
RUN cmake -D BUILD_GSTREAMER_PLUGIN=ON \
    -D BUILD_TEST=FALSE \
    ..

RUN make -j $(($(nproc) <= 4 ? $(nproc) : 4))

ENV GST_PLUGIN_PATH=/opt/amazon-kinesis-video-streams-producer-sdk-cpp/build
ENV LD_LIBRARY_PATH=/opt/amazon-kinesis-video-streams-producer-sdk-cpp/open-source/local/lib

# for some reason, the GST_PLUGIN_PATH and LD_LIBRARY_PATH environment variables defined
# above are not visible from within the container. We will replicate them in the
# /panorama/.env file that will be read from application code.
RUN echo "GST_PLUGIN_PATH=\"${GST_PLUGIN_PATH}\"\nLD_LIBRARY_PATH=\"${LD_LIBRARY_PATH}\"\n" > /panorama/.env

# kvs log configuration example. Feel free to download and modify this file and copy your
# custom version into the container
RUN curl https://github.com/neosperience/backpack/raw/main/resources/kvs_log_configuration -o /kvs_log_configuration

# ###### End of optional section for backpack.kvs ######



# ###### Optional section if you want to use backpack.rtsp ######

RUN apt-get install -y libgstrtspserver-1.0-dev

# ###### End of optional section for backpack.rtsp ######

# GLib libraries for python 3.7
RUN ln -s /usr/lib/python3/dist-packages/gi/_gi.cpython-{36m,37m}-$(uname -m)-linux-gnu.so

WORKDIR /

# Install backpack
# RUN pip install git+https://github.com/neosperience/backpack.git

# Install your application dependencies and copy your application code here, for example:
# RUN pip install requests
# COPY src /panorama

# For local testing, build this container from the root of the backpack repo with this command:
# $ docker build . -f examples/Dockerfile -t panorama-backpack:1.0
COPY . /opt/backpack
RUN python3 -m pip install /opt/backpack

WORKDIR /panorama
COPY tests /panorama
