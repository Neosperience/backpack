import time
from collections import deque
from itertools import islice
from typing import Optional

class StopWatch:
    
    ''' A simple performance profiler with context managers.
    
    There are two ways to use StopWatch: as a context manager, or with the `tick()`
    method. You can use the same StopWatch object in both ways at the same time.
    
    When used as a context managaer, StopWatch can be used to measure the 
    performance of python code using an elegant API based on context manager. 
    You can measure nested and serial execution.
    
    The second way is to measure the average execution of repeating tasks with 
    the `tick()` function call. After enough data samples were collected with 
    `tick()`, you can calculate the average execution of the task calling
    `mean_tick()`.
    
    Example usage:
    ```python
    import time
    with StopWatch('root') as root:
        with root.child('task1', max_ticks=5) as task:
            time.sleep(0.01)
            for i in range(10):
                task.tick()
                time.sleep((i+1)/100)
            with task.child('subtask1.1'):
                time.sleep(0.03)
            with task.child('subtask1.2'):
                time.sleep(0.07)
            with task.child('subtask1.3'):
                time.sleep(0.09)
        with root.child('task2') as task:
            time.sleep(0.17)
    print(root)
    ```
    
    Results:
    ```
    <StopWatch name=root total_elapsed=0.9222 children=[
        <StopWatch name=task1 total_elapsed=0.7520 ticks=[0.0501, 0.0601, 0.0701, 0.0802, 0.0902] mean_tick=0.0701 children=[
            <StopWatch name=subtask1.1 total_elapsed=0.0301>, 
            <StopWatch name=subtask1.2 total_elapsed=0.0701>, 
            <StopWatch name=subtask1.3 total_elapsed=0.0902>
        ]>, 
        <StopWatch name=task2 total_elapsed=0.1702>
    ]>
    ```
    
    :ivar name: Name of the StopWatch
    :ivar max_ticks: Maximum number of ticks to be recorded. Only the last max_ticks
        number of ticks will be kept.
    :ivar ticks: The recorded ticks
    :ivar children: The list of the children StopWatches
    :ivar parent: The parent StopWatch
    :ivar total_elapsed: Total elapsed time if the StopWatch was used as a context manager.
    '''
    
    def __init__(self, name:str, max_ticks:int=10):
        self.name = name
        self.children = []
        self.ticks = deque(maxlen=max_ticks + 1)
        self.max_ticks = max_ticks
        self.parent = None
        self.total_elapsed = 0.0
    
    def child(self, name:str, max_ticks:Optional[int]=None):
        ''' Creates a child StopWatch. 
        
        :param name: Name of the child StopWatch
        :param max_ticks: Maximum number of ticks to be recorded. If None, max_ticks
            from the parent will be used.
        '''
        if max_ticks is None:
            max_ticks = self.max_ticks
        child = StopWatch(name, max_ticks=max_ticks)
        child.parent = self
        self.children.append(child)
        return child
    
    def parents(self):
        current = self
        while True:
            yield current
            current = current.parent
            if not current:
                break
        
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.total_elapsed = time.perf_counter() - self._start
        
    def tick(self):
        self.ticks.append(time.perf_counter())
        
    def elapsed_ticks(self):
        shift = zip(islice(self.ticks, len(self.ticks) - 1), 
                    islice(self.ticks, 1, None))
        return [t2 - t1 for t1, t2 in shift]
        
    def stat_ticks(self):
        et = self.elapsed_ticks()
        return min(et), sum(et) / len(et), max(et)

    @property
    def level(self):
        return len(list(self.parents()))

    def __repr__(self):
        lvl = self.level
        indent = "    " * lvl
        nl = '\n'
        props = [f'name={self.name}', f'total_elapsed={self.total_elapsed:.4f}']
        if self.ticks:
            et_list = [f'{et:.4f}' for et in self.elapsed_ticks()]
            props.append(f'elapsed_ticks={et_list}')
            min_et, mean_et, max_et = self.stat_ticks()
            props.append(f'min_tick={min_et:.4f}')
            props.append(f'mean_tick={mean_et:.4f}')
            props.append(f'max_tick={max_et:.4f}')
        if self.children:
            props.append(f'children=[{", ".join(repr(c) for c in self.children)}\n{indent}]')
        return f'{nl if lvl > 0 else ""}{indent}<StopWatch {" ".join(props)}>'
