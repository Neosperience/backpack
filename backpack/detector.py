''' This module contains a generic interface for object detectors. '''

from typing import List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

import numpy as np

from .geometry import Rectangle

@dataclass(frozen=True)
class Detection:
    ''' The detection result of a single object in the image.

    Args:
        box (Rectangle): The bounding box of the detected object. The coordinate pairs should
            be normalized to the `[0; 1]` range respect to the size of the original image.
        score (float): The confidence score of the detection in the `[0; 1]` range.
        class_id (int): The class identifier of the detected object.
        class_name (str): The class name of the detected object, if known.
    '''

    box: Rectangle
    ''' The bounding box of the detected object. '''

    score: float
    ''' The confidence score of the detection. '''

    class_id: int
    ''' The class identifier of the detected object. '''

    class_name: Optional[str] = None
    ''' The class name of the detected object. '''


class Detector(ABC):

    @abstractmethod
    def process_frame(image: np.ndarray) -> List[Detection]:
        ''' Processes a single frame and returns the list of detections.

        Args:
            image: the input image

        Returns: The list of detections.
        '''
