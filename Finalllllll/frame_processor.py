import threading
import queue
import cv2
from workout_logic import ImprovedExerciseDetector

class FrameProcessor(threading.Thread):
    def __init__(self, frame_queue, result_queue):
        threading.Thread.__init__(self)
        self.frame_queue = frame_queue
        self.result_queue = result_queue
        self.detector = ImprovedExerciseDetector()
        self.running = True

    def run(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1)
                processed_frame, exercise_data = self.detector.process_frame(frame)
                self.result_queue.put((processed_frame, exercise_data))
            except queue.Empty:
                pass

    def stop(self):
        self.running = False