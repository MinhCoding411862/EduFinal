import cv2
import numpy as np
import mediapipe as mp
import math as m
from enum import Enum
from collections import deque
import heapq

class SquatState(Enum):
    IDLE = 0
    SQUAT_START = 1
    SQUAT_DOWN = 2
    SQUAT_HOLD = 3
    SQUAT_UP = 4

class BicepCurlState(Enum):
    IDLE = 0
    CURL_START = 1
    CURL_UP = 2
    CURL_HOLD = 3  
    CURL_DOWN = 4

class FeedbackPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class FeedbackManager:
    def __init__(self, window_size=5):
        self.feedback_window = deque(maxlen=window_size)
        self.current_feedback = []
        self.priority_queue = []

    def add_feedback(self, feedback, priority):
        heapq.heappush(self.priority_queue, (-priority.value, feedback))
        self.feedback_window.append((feedback, priority))
        self._process_feedback()

    def _process_feedback(self):
        feedback_count = {}
        for feedback, priority in self.feedback_window:
            if feedback in feedback_count:
                feedback_count[feedback] += 1
            else:
                feedback_count[feedback] = 1

        threshold = len(self.feedback_window) // 2
        self.current_feedback = [fb for fb, count in feedback_count.items() if count > threshold]

    def get_feedback(self):
        if self.priority_queue:
            _, top_feedback = self.priority_queue[0]
            return [top_feedback]
        return []

    def clear_feedback(self):
        self.feedback_window.clear()
        self.current_feedback = []
        self.priority_queue = []
    
class PoseDetector:
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # Change this to 2 for the most complex model
            smooth_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
    def find_pose(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        return results

    def draw_landmarks(self, image, results):
        self.mp_drawing.draw_landmarks(
            image, 
            results.pose_landmarks, 
            self.mp_pose.POSE_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)
        )

class AngleCalculator:
    @staticmethod
    def calculate_angle(a, b, c):
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        
        return angle if angle <= 180.0 else 360 - angle


    @staticmethod
    def calculate_vertical_angle(point1, point2):
        x1, y1 = point1
        x2, y2 = point2
        dx = x2 - x1
        dy = y2 - y1
        angle = np.abs(np.arctan2(dx, -dy) * 180.0 / np.pi)
        return angle        
    
    @staticmethod
    def findDistance(x1, y1, x2, y2):
        dist = m.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return dist

    @staticmethod
    def findAngle(x1, y1, x2, y2):
        theta = m.acos((y2 - y1) * (-y1) / (m.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * y1))
        degree = int(180 / m.pi) * theta
        return degree
    
    @staticmethod
    def angle_deg(p1, pref, p2):
            # Ensure all points are 2D
            p1 = np.array(p1[:2])
            pref = np.array(pref[:2])
            p2 = np.array(p2[:2])
            
            p1ref = p1 - pref
            p2ref = p2 - pref
            
            dot_product = np.dot(p1ref, p2ref)
            magnitude_p1ref = np.linalg.norm(p1ref)
            magnitude_p2ref = np.linalg.norm(p2ref)
            
            cos_theta = dot_product / (magnitude_p1ref * magnitude_p2ref)
            angle_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))
            angle_deg = np.degrees(angle_rad)
            
            return angle_deg
    
    @staticmethod
    def calculate_elbow_torso_angle(left_hip, left_shoulder, left_elbow, 
                                    right_hip, right_shoulder, right_elbow, 
                                    visibility_threshold=0.6):
        def is_visible(points):
            return all(point[2] > visibility_threshold for point in points)

        left_visible = is_visible([left_hip, left_shoulder, left_elbow])
        right_visible = is_visible([right_hip, right_shoulder, right_elbow])

        if left_visible and right_visible:
            # Front view - calculate both angles
            left_angle = AngleCalculator.angle_deg(left_hip, left_shoulder, left_elbow)
            right_angle = AngleCalculator.angle_deg(right_hip, right_shoulder, right_elbow)
            return left_angle, right_angle, (left_angle + right_angle) / 2, "front"
        elif left_visible:
            # Left side view
            left_angle = AngleCalculator.angle_deg(left_hip, left_shoulder, left_elbow)
            return left_angle, None, left_angle, "left_side"
        elif right_visible:
            # Right side view
            right_angle = AngleCalculator.angle_deg(right_hip, right_shoulder, right_elbow)
            return None, right_angle, right_angle, "right_side"
        else:
            # No clear view
            return None, None, None, "unclear"
        
    @staticmethod
    def calculate_hip_shoulder_angle(hip, shoulder, visibility_threshold=0.6):
        if hip[2] > visibility_threshold and shoulder[2] > visibility_threshold:
            return AngleCalculator.findAngle(hip[0], hip[1], shoulder[0], shoulder[1])
        else:
            return None

class ExerciseCounter:
    def __init__(self, analyze_squat_form_callback):
        self.curl_counter = 0
        self.bicep_curl_state = BicepCurlState.IDLE
        self.bicep_curl_analyzer = BicepCurlAnalyzer()
        self.prev_bicep_angle = 180
        self.curl_start_threshold = 160
        self.curl_up_threshold = 90
        self.curl_down_threshold = 150
        self.curl_feedback = []

        self.squat_counter = 0  
        self.squat_state = SquatState.IDLE
        self.squat_feedback = []
        self.prev_knee_angle = 180  # Initialize with a straight leg angle
        self.squat_threshold = 80  # Adjust this value based on your needs
        self.start_threshold = 160  # Threshold to detect the start of a squat

        self.bicep_curl_analyzer = BicepCurlAnalyzer()

        self.is_curling = False
        self.curl_start_detected = False

        self.current_exercise = None
        self.total_reps = 0

        self.analyze_squat_form_callback = analyze_squat_form_callback

        #feedback 
        self.bicep_curl_feedback_manager = FeedbackManager()
        self.squat_feedback_manager = FeedbackManager()
        self.rep_error = False

    def reset_counter(self):
        self.bicep_curl_state = BicepCurlState.IDLE
        self.squat_state = SquatState.IDLE

    def process_bicep_curl(self, shoulder, elbow, wrist, hip, bicep_angle, elbow_torso_angle, hip_shoulder_angle):
        is_start = False

        if self.bicep_curl_state == BicepCurlState.IDLE:
            if bicep_angle < self.curl_start_threshold:
                self.bicep_curl_state = BicepCurlState.CURL_START
                is_start = True
                self.bicep_curl_feedback_manager.clear_feedback()
                self.rep_error = False

        elif self.bicep_curl_state == BicepCurlState.CURL_START:
            if bicep_angle < self.curl_up_threshold:
                self.bicep_curl_state = BicepCurlState.CURL_UP
            elif bicep_angle > self.prev_bicep_angle:
                self.bicep_curl_state = BicepCurlState.IDLE

        elif self.bicep_curl_state == BicepCurlState.CURL_UP:
            if bicep_angle <= self.prev_bicep_angle:
                self.bicep_curl_state = BicepCurlState.CURL_HOLD

        elif self.bicep_curl_state == BicepCurlState.CURL_HOLD:
            if bicep_angle > self.prev_bicep_angle:
                self.bicep_curl_state = BicepCurlState.CURL_DOWN

        elif self.bicep_curl_state == BicepCurlState.CURL_DOWN:
            if bicep_angle >= self.curl_down_threshold:
                self.bicep_curl_state = BicepCurlState.IDLE
                self.curl_counter += 1

        self.prev_bicep_angle = bicep_angle

        # Analyze curl and add feedback
        curl_feedback = self.bicep_curl_analyzer.analyze_curl(
            shoulder, elbow, wrist, hip, bicep_angle, elbow_torso_angle, hip_shoulder_angle, is_start, self.bicep_curl_state
        )
        
        for feedback in curl_feedback:
            if "Correct form" not in feedback:
                self.rep_error = True
                self.bicep_curl_feedback_manager.add_feedback(feedback, FeedbackPriority.HIGH)
            elif not self.rep_error:
                self.bicep_curl_feedback_manager.add_feedback(feedback, FeedbackPriority.LOW)

        return self.bicep_curl_state, self.bicep_curl_feedback_manager.get_feedback()
    
    def get_bicep_curl_feedback(self):
        return self.bicep_curl_feedback_manager.get_feedback()

    def get_bicep_curl_state(self):
        return self.bicep_curl_state.name

    def process_squat(self, knee_angle, back_angle):
        if self.squat_state == SquatState.IDLE:
            if knee_angle < self.start_threshold:
                self.squat_state = SquatState.SQUAT_START
                self.squat_feedback_manager.clear_feedback()
            else:
                # Clear feedback when in IDLE state
                self.squat_feedback_manager.clear_feedback()
                return self.squat_state, []  # Return empty feedback list when IDLE

        elif self.squat_state == SquatState.SQUAT_START:
            if knee_angle < self.squat_threshold:
                self.squat_state = SquatState.SQUAT_DOWN
            elif knee_angle > self.prev_knee_angle:
                self.squat_state = SquatState.IDLE
                self.squat_feedback_manager.clear_feedback()
                return self.squat_state, []  # Return empty feedback list when returning to IDLE

        elif self.squat_state == SquatState.SQUAT_DOWN:
            if knee_angle <= self.prev_knee_angle:
                self.squat_state = SquatState.SQUAT_HOLD
                # Generate feedback when reaching the bottom of the squat
                squat_feedback = self.analyze_squat_form_callback(back_angle, knee_angle)
                for feedback in squat_feedback:
                    if "Correct form" not in feedback:
                        self.squat_feedback_manager.add_feedback(feedback, FeedbackPriority.HIGH)
                    else:
                        self.squat_feedback_manager.add_feedback(feedback, FeedbackPriority.LOW)

        elif self.squat_state == SquatState.SQUAT_HOLD:
            if knee_angle > self.prev_knee_angle:
                self.squat_state = SquatState.SQUAT_UP

        elif self.squat_state == SquatState.SQUAT_UP:
            if knee_angle >= self.start_threshold:
                self.squat_state = SquatState.IDLE
                self.squat_counter += 1
                # Generate feedback at the end of the squat
                squat_feedback = self.analyze_squat_form_callback(back_angle, knee_angle)
                for feedback in squat_feedback:
                    if "Correct form" not in feedback:
                        self.squat_feedback_manager.add_feedback(feedback, FeedbackPriority.HIGH)
                    else:
                        self.squat_feedback_manager.add_feedback(feedback, FeedbackPriority.LOW)

        self.prev_knee_angle = knee_angle

        return self.squat_state, self.squat_feedback_manager.get_feedback()

    def get_squat_feedback(self):
        return self.squat_feedback_manager.get_feedback()

    def get_squat_state(self):
        return self.squat_state.name
    
    def reset_counters(self):
        self.curl_counter = 0
        self.squat_counter = 0
        self.bicep_curl_state = BicepCurlState.IDLE
        self.squat_state = SquatState.IDLE

    def is_exercise_completed(self, exercise_name, target_reps):
        if exercise_name.lower() == 'bicep curl' or exercise_name.lower() == 'curl':
            return self.curl_counter >= target_reps
        elif exercise_name.lower() == 'squat':
            return self.squat_counter >= target_reps
        return False

    def set_total_reps(self, total_reps):
        self.total_reps = total_reps

class BicepCurlAnalyzer:
    def __init__(self):
        self.start_shoulder_pos = None
        self.start_hip_pos = None
        self.start_elbow_pos = None
        self.start_time = None
        self.rep_start_time = None
        self.last_angle = None
        self.max_angle = 0
        self.min_angle = 180
        self.feedback = []
        self.fully_extended = False
        self.curled_high_enough = False
        self.body_swing_threshold = 0.625
        self.shoulder_movement_threshold = 0.5
        self.elbow_movement_threshold = 0.5
        self.curl_completion_threshold = 65 # Minimum angle change for a complete curl
        self.max_elbow_angle = 0
        self.start_hip_shoulder_angle = None
        self.body_swing_angle_threshold = 18  # Adjust this value based on testing
        self.max_swing_angle = 0
        self.elbow_angle_buffer = []
        self.elbow_detection_confidence = 1.0
        self.confidence_threshold = 0.7
        self.low_confidence_count = 0
        self.max_low_confidence_frames = 8
        self.angle_calculator = AngleCalculator()  


    def reset(self):
        self.start_shoulder_pos = None
        self.start_hip_pos = None
        self.start_elbow_pos = None
        self.start_time = None
        self.rep_start_time = None
        self.last_angle = None
        self.max_angle = 0
        self.min_angle = 180
        self.feedback = []
        self.fully_extended = False
        self.curled_high_enough = False
        self.max_elbow_angle = 0
        self.start_hip_shoulder_angle = None
        self.max_swing_angle = 0

    def detect_body_swing(self, hip_shoulder_angle):
        if self.start_hip_shoulder_angle is None or hip_shoulder_angle is None:
            return False
        
        angle_diff = abs(hip_shoulder_angle - self.start_hip_shoulder_angle)
        self.max_swing_angle = max(self.max_swing_angle, angle_diff)
        return angle_diff > self.body_swing_angle_threshold

    def is_curl_completed(self):
        return self.max_angle - self.min_angle > self.curl_completion_threshold

    def calculate_elbow_confidence(self, shoulder, elbow, wrist):
        # Check if visibility data is available
        if len(shoulder) > 2 and len(elbow) > 2 and len(wrist) > 2:
            visibility = min(shoulder[2], elbow[2], wrist[2])
        else:
            visibility = 1.0  # Assume full visibility if data is not available

        # Calculate distances
        shoulder_elbow_dist = self.angle_calculator.findDistance(shoulder[0], shoulder[1], elbow[0], elbow[1])
        shoulder_wrist_dist = self.angle_calculator.findDistance(shoulder[0], shoulder[1], wrist[0], wrist[1])
        
        # Avoid division by zero
        if shoulder_wrist_dist == 0:
            distance_confidence = 0
        else:
            distance_confidence = 1.0 - (shoulder_elbow_dist / shoulder_wrist_dist)

        return visibility * max(0, min(1, distance_confidence))

    def update_elbow_angle(self, elbow_torso_angle):
        self.elbow_angle_buffer.append(elbow_torso_angle)
        if len(self.elbow_angle_buffer) > 5:
            self.elbow_angle_buffer.pop(0)
        return sum(self.elbow_angle_buffer) / len(self.elbow_angle_buffer)
    
    def analyze_curl(self, shoulder, elbow, wrist, hip, bicep_angle, elbow_torso_angle, hip_shoulder_angle, is_start, current_state):
        if is_start or self.start_shoulder_pos is None:
            self.reset()
            self.start_shoulder_pos = shoulder
            self.start_hip_pos = hip
            self.start_elbow_pos = elbow
            self.start_hip_shoulder_angle = hip_shoulder_angle
            self.last_angle = bicep_angle
            return []

        self.feedback = []
        has_issues = False
        # Update elbow detection confidence
        self.elbow_detection_confidence = self.calculate_elbow_confidence(shoulder, elbow, wrist)

        # Check for swinging (using momentum)
        shoulder_movement = ((shoulder[0] - self.start_shoulder_pos[0])**2 + 
                            (shoulder[1] - self.start_shoulder_pos[1])**2)**0.5
        if shoulder_movement > self.shoulder_movement_threshold:
            self.feedback.append("Keep your upper arm still")
            has_issues = True

        # Check elbow movement
        elbow_movement = ((elbow[0] - self.start_elbow_pos[0])**2 + 
                        (elbow[1] - self.start_elbow_pos[1])**2)**0.5
        if elbow_movement > self.elbow_movement_threshold:
            self.feedback.append("Keep your elbow in place")
            has_issues = True

        # Check for body swinging
        if self.detect_body_swing(hip_shoulder_angle):
            swing_severity = "slightly" if self.max_swing_angle <= 20 else "excessively"
            self.feedback.append(f"Your body is {swing_severity} swinging. Keep your body stable.")
            has_issues = True

        # Check for excessive elbow movement
        if elbow_torso_angle is not None:
            smoothed_elbow_angle = self.update_elbow_angle(elbow_torso_angle)
            self.max_elbow_angle = max(self.max_elbow_angle, smoothed_elbow_angle)
            if self.max_elbow_angle > 35 and self.elbow_detection_confidence > self.confidence_threshold:
                self.feedback.append("Keep your upper arm still, excessive elbow movement")
                has_issues = True
            self.low_confidence_count = 0
        else:
            self.low_confidence_count += 1
            if self.low_confidence_count >= self.max_low_confidence_frames:
                self.feedback.append("Unable to detect elbow movement accurately")
                self.low_confidence_count = 0

        # Update max and min angles
        self.max_angle = max(self.max_angle, bicep_angle)
        self.min_angle = min(self.min_angle, bicep_angle)

        # Check for full rep and reset if necessary
        if self.last_angle < 90 and bicep_angle > 160:
            self.max_angle = bicep_angle
            self.min_angle = bicep_angle
            self.fully_extended = False
            self.curled_high_enough = False

        self.last_angle = bicep_angle

        # If no issues were detected and the curl is completed, add positive feedback
        if not has_issues and self.is_curl_completed():
            self.feedback.append("Correct form, keep it up")

        return self.feedback  # Always return the feedback list
    
class PostureAnalyzer:
    def __init__(self, fps):
        self.fps = fps
        self.bad_frames = 0
        self.good_frames = 0

    def analyze_posture(self, left_neck_inclination, right_neck_inclination, left_torso_inclination, right_torso_inclination):
        # Use the worse angle for each measurement
        neck_inclination = max(left_neck_inclination, right_neck_inclination)
        torso_inclination = max(left_torso_inclination, right_torso_inclination)

        if neck_inclination < 40 and torso_inclination < 10:
            self.good_frames += 1
            self.bad_frames = 0
            return True
        else:
            self.good_frames = 0
            self.bad_frames += 1
            return False

    def get_posture_times(self):
        good_time = (1 / self.fps) * self.good_frames
        bad_time = (1 / self.fps) * self.bad_frames
        return good_time, bad_time

class VideoProcessor:
    def __init__(self, visibility_threshold=0.6):
        self.pose_detector = PoseDetector()
        self.angle_calculator = AngleCalculator()
        self.cap = cv2.VideoCapture(0)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.posture_analyzer = PostureAnalyzer(self.fps)
        self.squat_feedback = []
        self.bicep_curl_analyzer = BicepCurlAnalyzer()
        self.exercise_counter = ExerciseCounter(self.analyze_squat_form)
        self.bicep_curl_feedback = []
        self.visibility_threshold = visibility_threshold
        self.current_exercise = None

        self.exercise_data = {
            'curl_counter': 0,
            'squat_counter': 0,
            'curl_state': '',
            'squat_state': '',
            'bicep_curl_feedback': [],
            'squat_feedback': [],
            'total_reps': 0
        }
        
    def analyze_squat_form(self, back_angle, knee_angle):
        feedback = []
        
        # Only analyze form if not in IDLE state (knee angle less than start_threshold)
        if knee_angle < self.exercise_counter.start_threshold:
            if back_angle < 19:
                feedback.append("Bend forward more")
            elif back_angle > 50:
                feedback.append("Forward bending too much")
            
            if knee_angle < 68:
                feedback.append("Lower your hips")
            elif knee_angle >= 91:
                feedback.append("Don't squat too deep")
            
            if not feedback:
                feedback.append("Correct form")
        
        return feedback
    

    def process_frame(self, frame, current_exercise):
        results = self.pose_detector.find_pose(frame)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            landmark_data = self.process_landmarks(frame, landmarks, current_exercise)
            if landmark_data:
                self.exercise_data.update(landmark_data)
        
        self.pose_detector.draw_landmarks(frame, results)
        
        return frame, self.exercise_data

    def process_landmarks(self, frame, landmarks, current_exercise):
        mp_pose = self.pose_detector.mp_pose
        h, w, _ = frame.shape
        
        # Extract coordinates and visibility for both left and right sides
        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, 
                        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y,
                        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility]
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, 
                        landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y,
                        landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].visibility]
        left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, 
                    landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y,
                    landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].visibility]
        right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, 
                    landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y,
                    landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].visibility]
        left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, 
                    landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y,
                    landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].visibility]
        right_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, 
                    landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y,
                    landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].visibility]
        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, 
                    landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y,
                    landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].visibility]
        right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, 
                    landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y,
                    landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].visibility]
        left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, 
                    landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y,
                    landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].visibility]
        right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, 
                    landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y,
                    landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].visibility]
        left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, 
                    landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y,
                    landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].visibility]
        right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, 
                    landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y,
                    landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].visibility]
        left_ear = [landmarks[mp_pose.PoseLandmark.LEFT_EAR.value].x, 
                    landmarks[mp_pose.PoseLandmark.LEFT_EAR.value].y,
                    landmarks[mp_pose.PoseLandmark.LEFT_EAR.value].visibility]
        right_ear = [landmarks[mp_pose.PoseLandmark.RIGHT_EAR.value].x, 
                    landmarks[mp_pose.PoseLandmark.RIGHT_EAR.value].y,
                    landmarks[mp_pose.PoseLandmark.RIGHT_EAR.value].visibility]

        # Calculate angles for both sides
        offset = self.angle_calculator.findDistance(left_shoulder[0], left_shoulder[1], right_shoulder[0], right_shoulder[1])
        left_neck_inclination = self.angle_calculator.findAngle(left_shoulder[0], left_shoulder[1], left_ear[0], left_ear[1])
        right_neck_inclination = self.angle_calculator.findAngle(right_shoulder[0], right_shoulder[1], right_ear[0], right_ear[1])
        left_torso_inclination = self.angle_calculator.findAngle(left_hip[0], left_hip[1], left_shoulder[0], left_shoulder[1])
        right_torso_inclination = self.angle_calculator.findAngle(right_hip[0], right_hip[1], right_shoulder[0], right_shoulder[1])
        
        # Calculate hip-to-shoulder angle
        left_hip_shoulder_angle = self.angle_calculator.calculate_hip_shoulder_angle(left_hip, left_shoulder, self.visibility_threshold)
        right_hip_shoulder_angle = self.angle_calculator.calculate_hip_shoulder_angle(right_hip, right_shoulder, self.visibility_threshold)

        # Use the angle from the side that's more visible
        hip_shoulder_angle = left_hip_shoulder_angle if left_hip_shoulder_angle is not None else right_hip_shoulder_angle

        # Calculate bicep curl angles
        left_bicep_angle = self.angle_calculator.angle_deg(left_shoulder[:2], left_elbow[:2], left_wrist[:2])
        right_bicep_angle = self.angle_calculator.angle_deg(right_shoulder[:2], right_elbow[:2], right_wrist[:2])

        # Calculate squat angles for both legs
        left_squat_angle = self.angle_calculator.angle_deg(left_hip[:2], left_knee[:2], left_ankle[:2])
        right_squat_angle = self.angle_calculator.angle_deg(right_hip[:2], right_knee[:2], right_ankle[:2])

        # Calculate elbow-torso angles
        left_elbow_torso_angle, right_elbow_torso_angle, avg_elbow_torso_angle, view = self.angle_calculator.calculate_elbow_torso_angle(
                left_hip, left_shoulder, left_elbow,
                right_hip, right_shoulder, right_elbow,
                visibility_threshold=self.visibility_threshold
            )
        
        # Calculate knee angle and back angle
        knee_angle = (left_squat_angle + right_squat_angle) / 2
        back_angle = (self.angle_calculator.angle_deg(left_hip[:2], left_shoulder[:2], [left_shoulder[0], left_hip[1]]) +
                    self.angle_calculator.angle_deg(right_hip[:2], right_shoulder[:2], [right_shoulder[0], right_hip[1]])) / 2

        # Process exercises
        if current_exercise:
            if current_exercise['name'].lower() in ['bicep curl', 'curl']:
                if left_bicep_angle < right_bicep_angle:
                    self.bicep_curl_state, self.bicep_curl_feedback = self.exercise_counter.process_bicep_curl(
                        left_shoulder, left_elbow, left_wrist, left_hip, left_bicep_angle, left_elbow_torso_angle, hip_shoulder_angle
                    )
                else:
                    self.bicep_curl_state, self.bicep_curl_feedback = self.exercise_counter.process_bicep_curl(
                        right_shoulder, right_elbow, right_wrist, right_hip, right_bicep_angle, right_elbow_torso_angle, hip_shoulder_angle
                    )
            elif current_exercise['name'].lower() == 'squat':
                self.squat_state, self.squat_feedback = self.exercise_counter.process_squat(knee_angle, back_angle)



        # Analyze posture
        good_posture = self.posture_analyzer.analyze_posture(
            left_neck_inclination, right_neck_inclination, 
            left_torso_inclination, right_torso_inclination
        )
        # Analyze squat form
        self.squat_feedback = self.analyze_squat_form(back_angle, knee_angle)

        # Visualize
        self.visualize_posture(frame, left_shoulder, right_shoulder, left_ear, right_ear, left_hip, right_hip, 
                            left_neck_inclination, right_neck_inclination, 
                            left_torso_inclination, right_torso_inclination, good_posture, offset)
        self.visualize_angles(frame, left_elbow, right_elbow, left_knee, right_knee, 
                            left_bicep_angle, right_bicep_angle, left_squat_angle, right_squat_angle, back_angle, knee_angle)

        # Return processed data
        return {
            'curl_counter': self.exercise_counter.curl_counter,
            'squat_counter': self.exercise_counter.squat_counter,
            'curl_state': self.exercise_counter.bicep_curl_state.name if self.exercise_counter.bicep_curl_state else '',
            'squat_state': self.exercise_counter.squat_state.name if self.exercise_counter.squat_state else '',
            'bicep_curl_feedback': self.exercise_counter.get_bicep_curl_feedback(),
            'squat_feedback': self.exercise_counter.get_squat_feedback(),
            'total_reps': self.exercise_counter.total_reps
        }

    def visualize_posture(self, frame, left_shoulder, right_shoulder, left_ear, right_ear, left_hip, right_hip,
                          left_neck_inclination, right_neck_inclination,
                          left_torso_inclination, right_torso_inclination, good_posture, offset):
        # Colors (using your existing color definitions)
        red = (50, 50, 255)
        green = (127, 255, 0)
        yellow = (0, 255, 255)

        # Font
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Alignment assistant
        if offset < 100:
            cv2.putText(frame, f'{int(offset)} Aligned', (frame.shape[1] - 150, 30), font, 0.9, green, 2)
        else:
            cv2.putText(frame, f'{int(offset)} Not Aligned', (frame.shape[1] - 150, 30), font, 0.9, red, 2)
        # Draw landmarks
        for point in [left_shoulder, right_shoulder, left_ear, right_ear, left_hip, right_hip]:
            cv2.circle(frame, (int(point[0]*frame.shape[1]), int(point[1]*frame.shape[0])), 5, yellow, -1)

        # Posture and angle inclination text
        angle_text_string = f'L Neck: {int(left_neck_inclination)} R Neck: {int(right_neck_inclination)}'
        cv2.putText(frame, angle_text_string, (10, 30), font, 0.7, green if good_posture else red, 2)
        angle_text_string = f'L Torso: {int(left_torso_inclination)} R Torso: {int(right_torso_inclination)}'
        cv2.putText(frame, angle_text_string, (10, 60), font, 0.7, green if good_posture else red, 2)

        # Join landmarks
        color = green if good_posture else red
        for start, end in [(left_shoulder, left_ear), (right_shoulder, right_ear),
                           (left_shoulder, left_hip), (right_shoulder, right_hip)]:
            cv2.line(frame,
                     (int(start[0]*frame.shape[1]), int(start[1]*frame.shape[0])),
                     (int(end[0]*frame.shape[1]), int(end[1]*frame.shape[0])),
                     color, 2)
            
    def visualize_angles(self, frame, left_elbow, right_elbow, left_knee, right_knee, 
                         left_bicep_angle, right_bicep_angle, left_squat_angle, right_squat_angle, back_angle, knee_angle):
        cv2.putText(frame, f"L Curl: {left_bicep_angle:.1f}", 
                    (int(left_elbow[0]*frame.shape[1]), int(left_elbow[1]*frame.shape[0])), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, f"R Curl: {right_bicep_angle:.1f}", 
                    (int(right_elbow[0]*frame.shape[1]), int(right_elbow[1]*frame.shape[0])), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, f"L Squat: {left_squat_angle:.1f}", 
                    (int(left_knee[0]*frame.shape[1]), int(left_knee[1]*frame.shape[0])), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, f"R Squat: {right_squat_angle:.1f}", 
                    (int(right_knee[0]*frame.shape[1]), int(right_knee[1]*frame.shape[0])), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Display back and knee angles
        cv2.putText(frame, f"Back angle: {back_angle:.1f}", 
                    (10, frame.shape[0] - 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, f"Knee angle: {knee_angle:.1f}", 
                    (10, frame.shape[0] - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    def set_current_exercise(self, exercise):
            self.current_exercise = exercise
            self.exercise_counter.set_total_reps(exercise['reps'] * exercise['sets'])

if __name__ == "__main__":
    processor = VideoProcessor()
    processor.run()