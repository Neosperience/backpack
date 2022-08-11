if __name__ == '__main__':
    import backpack.rtsp, gi, numpy as np, time, os, logging
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init()
    os.environ['GST_DEBUG'] = '3'
    logging.basicConfig(level=logging.INFO)

    server = backpack.rtsp.RTSPServer(port='8554')
    sl1 = backpack.rtsp.RTSPSkyLine(server, 'rainbow')
    sl2 = backpack.rtsp.RTSPSkyLine(server, 'bw')
    sl1.start_streaming(30, 640, 480)
    sl2.start_streaming(30, 640, 480)
    server.start()

    # Generate some fake videos
    import colorsys
    from backpack.annotation import TimestampAnnotation
    from backpack.annotation.opencv import OpenCVImageAnnotationDriver
    i = 0
    driver = OpenCVImageAnnotationDriver()
    while True:
        i = (i + 1) % 256
        (r, g, b) = colorsys.hsv_to_rgb(255 - i / 255, 1.0, 1.0)
        R, G, B = int(255 * r), int(255 * g), int(255 * b)
        annos = [TimestampAnnotation()]
        frame1 = np.full((640, 480, 3), [R, G, B], dtype=np.uint8)
        _ = driver.render(annos, frame1)
        frame2 = np.full((640, 480, 3), [i, i, i], dtype=np.uint8)
        _ = driver.render(annos, frame2)
        _ = sl1.put(frame1)
        _ = sl2.put(frame2)
        time.sleep(1/30)
