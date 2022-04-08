import backpack.rtsp, gi, numpy as np, time, os, logging
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init()
os.environ['GST_DEBUG'] = '3'
logging.basicConfig(level=logging.INFO)

server = backpack.rtsp.RTSPServer(port='8554')
sg1 = backpack.rtsp.RTSPSpyGlass(server, '/stream1')
sg2 = backpack.rtsp.RTSPSpyGlass(server, '/stream2')
sg1.start_streaming(30, 640, 480)
sg2.start_streaming(30, 640, 480)
server.start()
i = 0
while True:
    i = (i + 10) % 256
    _ = sg1.put(np.full((640, 480, 3), [255, i, 0], dtype=np.uint8))
    _ = sg2.put(np.full((640, 480, 3), [0, 255, i], dtype=np.uint8))
    time.sleep(1/30)
