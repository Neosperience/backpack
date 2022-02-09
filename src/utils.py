from typing import Tuple
import datetime
from typing import Optional

import cv2

def add_timestamp(
    img: 'np.array',
    timestamp: Optional[datetime.datetime]=None,
    origin: Tuple[int, int]=(10, 20),
    color: Tuple[int, int, int]=(255, 255, 255)
):
    ''' Adds a timestamp to the cv2 image. '''
    timestamp = timestamp or datetime.datetime.now()
    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    cv2.putText(img, time_str, origin, cv2.FONT_HERSHEY_PLAIN, 1.0, color)

def to_datetime(panorama_ts: Tuple[int, int]) -> datetime.datetime:
    ''' Converts panoramasdk.media.time_stamp (seconds, microsececonds) tuple to python datetime. '''
    sec, microsec = panorama_ts
    return datetime.datetime.fromtimestamp(sec + microsec / 1000000.0)
