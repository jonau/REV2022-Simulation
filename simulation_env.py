from typing import Any, List, Tuple

class SimulationEnvironment:
    time: int
    events_occured: bool
    event_list: List[Tuple[int, Any]] 

    def __init__(self):
        self.time = 0
        self.events_occured = True
        self.event_list = []
    
    def create_event(self, time, event):
        lo = 0
        hi = len(self.event_list)
        while lo < hi:
            mid = (lo+hi)//2
            if time < self.event_list[mid][0]:
                hi = mid
            else:
                lo = mid+1
        self.event_list.insert(lo, (time, event))

    def step(self):
        self.time += 1
        while len(self.event_list) and self.event_list[0][0]==self.time:
            _, event = self.event_list.pop(0)
            self.events_occured=True
            self.handle_event(self.time, event)
        self.handle_time_step(self.time, self.events_occured)
        self.events_occured=False

    def run(self, stop_time: int):
        self._stop=False
        while self.time < stop_time and not self._stop:
            self.step()

    def stop(self):
        self._stop=True

    def handle_event(self, time: int, event: Any):
        """
        Will be called for every event.
        """
        pass

    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """
        pass