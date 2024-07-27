import sys
import cv2
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,  QListWidget, QFrame, QTextEdit,
    QLineEdit, QFormLayout, QRadioButton, QButtonGroup, QStackedWidget, QMessageBox, QStyleFactory,  QSizePolicy, QToolBar
)
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRectF, pyqtSignal, pyqtProperty, pyqtSlot, QRunnable, QObject, QThreadPool 
from PyQt6.QtGui import QImage, QPixmap, QIcon, QPainter, QColor, QPalette,  QPen, QBrush
from workout_extractor import WorkoutExtractor
from PyQt6.QtMultimedia import QMediaPlayer
import google.generativeai as genai
from home_tab import *
import math
import logging
from demo1 import VideoProcessor
from workout_plan_widget import WorkoutPlanWidget
from elevenlabs import Voice, VoiceSettings, play
from elevenlabs.client import ElevenLabs
import mysql.connector
from mysql.connector import Error
import datetime
from dashboard import Dashboard  # Import the Dashboard class
from threshold_adjuster import ThresholdAdjuster
from meal_plan_extractor import MealPlanExtractor

class SessionManager:
    def __init__(self, db):
        self.db = db
        self.current_session_id = None

    def start_new_session(self):
        cursor = self.db.connection.cursor()
        cursor.execute("INSERT INTO sessions (start_time) VALUES (NOW())")
        self.db.connection.commit()
        self.current_session_id = cursor.lastrowid
        return self.current_session_id

    def get_previous_sessions(self):
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT id, start_time FROM sessions ORDER BY start_time DESC")
        return cursor.fetchall()

    def load_session(self, session_id):
        self.current_session_id = session_id
        # Load chat history for this session
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT sender, message FROM chat_log WHERE session_id = %s ORDER BY timestamp", (session_id,))
        return cursor.fetchall()

    def save_message(self, sender, message):
        cursor = self.db.connection.cursor()
        cursor.execute("INSERT INTO chat_log (session_id, timestamp, sender, message) VALUES (%s, NOW(), %s, %s)",
                       (self.current_session_id, sender, message))
        self.db.connection.commit()
class AIWorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class AIWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = AIWorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit(str(e))
        else:
            self.signals.finished.emit(result)

class ScoreBoard(QWidget):
    def __init__(self):
        super().__init__()
        self.points = 0
        self.layout = QHBoxLayout(self)
        self.label = QLabel(f"Score: {self.points}")
        self.layout.addWidget(self.label)

    def add_points(self, points):
        self.points += points
        self.label.setText(f"Score: {self.points}")

class ChatBubble(QTextEdit):
    def __init__(self, text, is_user, parent=None):
        super().__init__(text, parent)
        self.is_user = is_user
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(
            f"""
            background-color: {'#DCF8C6' if is_user else '#E8E8E8'};
            color: #000000;
            border-radius: 10px;
            padding: 10px;
            """
        )
        self.document().contentsChanged.connect(self.sizeChange)
        self.heightMin = 0
        self.heightMax = 65000
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeChange(self):
        docHeight = self.document().size().height()
        if self.heightMin <= docHeight <= self.heightMax:
            self.setMinimumHeight(int(docHeight) + 20)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizeChange()

def create_chat_bubble(text, is_user, parent_width):
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    
    bubble = ChatBubble(text, is_user)
    bubble_width = int(parent_width * 0.9)  # Use 90% of parent width
    bubble.setFixedWidth(bubble_width)
    
    if is_user:
        layout.addStretch()
        layout.addWidget(bubble)
    else:
        layout.addWidget(bubble)
        layout.addStretch()
    
    return container

class ToggleSwitch(QWidget):
    stateChanged = pyqtSignal(bool)  # Add this line at the class level
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 30)
        self._is_checked = False
        self._track_color = QColor(255, 255, 255)
        self._thumb_color = QColor(76, 175, 80)
        self._track_opacity = 0.5
        
        self._thumb_position = 4
        self._animation = QPropertyAnimation(self, b"thumb_position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(200)  # 200ms for the animation
        
    @pyqtProperty(float)

    def thumb_position(self):
        return self._thumb_position
    
    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw track
        track_opacity = self._track_opacity if self._is_checked else 1.0
        painter.setBrush(QBrush(self._track_color.darker(120)))
        painter.setOpacity(track_opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        
        # Draw thumb
        painter.setBrush(QBrush(self._thumb_color))
        painter.setOpacity(1.0)
        painter.drawEllipse(QRectF(self._thumb_position, 4, 22, 22))
        
        # Draw icons
        painter.setPen(QPen(Qt.GlobalColor.white))
        if self._is_checked:
            # Draw moon
            painter.drawEllipse(QRectF(self._thumb_position + 6, 10, 10, 10))
            painter.drawEllipse(QRectF(self._thumb_position + 9, 7, 10, 10))
        else:
            # Draw sun
            painter.drawEllipse(QRectF(self._thumb_position + 6, 10, 10, 10))
            for i in range(8):
                angle = i * 45
                x = self._thumb_position + 11 + 8 * math.cos(math.radians(angle))
                y = 15 + 8 * math.sin(math.radians(angle))
                painter.drawLine(int(x), int(y), int(x + 2 * math.cos(math.radians(angle))), int(y + 2 * math.sin(math.radians(angle))))
    
    def mousePressEvent(self, event):
        self._is_checked = not self._is_checked
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(34 if self._is_checked else 4)
        self._animation.start()
        
        if self._is_checked:
            self._track_color = QColor(0, 0, 0)
            self._thumb_color = QColor(76, 175, 80)
        else:
            self._track_color = QColor(255, 255, 255)
            self._thumb_color = QColor(76, 175, 80)
        
        self.update()
        self.stateChanged.emit(self._is_checked)  # Emit the signal when state changes

class ThemeManager:
    @staticmethod
    def set_dark_theme(app):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(dark_palette)
        app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")

    @staticmethod
    def set_light_theme(app):
        app.setStyle(QStyleFactory.create("Fusion"))
        app.setPalette(app.style().standardPalette())

class ChatDatabase:
    def __init__(self):
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                database='workout_assistant',
                user='root',
                password=''  # Default password for XAMPP is empty
            )
            if self.connection.is_connected():
                print("Connected to MySQL database")
                self.create_tables()
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")

    def create_tables(self):
        try:
            cursor = self.connection.cursor()
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    start_time DATETIME
                )
            ''')
            
            # Create chat_log table with session_id
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id INT,
                    timestamp DATETIME,
                    sender VARCHAR(255),
                    message TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            ''')
            
            self.connection.commit()
            print("Tables created successfully")
        except Error as e:
            print(f"Error creating tables: {e}")



    def save_message(self, sender, message):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO chat_log (timestamp, sender, message) VALUES (%s, %s, %s)"
            cursor.execute(query, (datetime.datetime.now(), sender, message))
            self.connection.commit()
            print(f"Message saved successfully: {sender} - {message[:50]}...")  # Log first 50 characters
        except Error as e:
            print(f"Error saving message: {e}")

    def get_chat_history(self):
        try:
            cursor = self.connection.cursor()
            query = "SELECT timestamp, sender, message FROM chat_log ORDER BY timestamp"
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"Retrieved {len(results)} messages from chat history")  # Log number of messages retrieved
            return results
        except Error as e:
            print(f"Error retrieving chat history: {e}")
            return []

    def close_connection(self):
        if self.connection.is_connected():
            self.connection.close()
            print("MySQL connection is closed")

class WorkoutApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Workout Assistant")
        self.setGeometry(100, 100, 1200, 800)
        self.db = ChatDatabase()
        self.is_chat_log_displayed = False
        self.current_chat_messages = []
        # Load styles
        with open("style.qss", "r") as f:
            self.dark_style = f.read()
        with open("light_style.qss", "r") as f:
            self.light_style = f.read()

        # Set initial style to dark
        self.setStyleSheet(self.dark_style)

        self.scoreboard = ScoreBoard()  
        self.dashboard = None


        # Create central stacked widget
        self.central_stacked_widget = QStackedWidget()
        self.setCentralWidget(self.central_stacked_widget)

        # Create main layout
        self.main_layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.main_layout)
        self.central_stacked_widget.addWidget(self.central_widget)
        
        # Initialize workout plan and widget
        self.workout_plan = []
        self.workout_plan_widget = None
        self.meal_plan = None  # Add this line

        # Create and add the theme toggle switch
        self.theme_toggle = ToggleSwitch()
        self.theme_toggle.stateChanged.connect(self.switch_theme)
        toggle_layout = QHBoxLayout()
        toggle_layout.addStretch(1)
        toggle_layout.addWidget(self.theme_toggle)
        self.main_layout.addLayout(toggle_layout)

        # Initialize theme manager
        self.theme_manager = ThemeManager()
        self.theme_manager.set_dark_theme(QApplication.instance())

        # Create tabs
        self.home_screen = SplitScreen(self.central_stacked_widget)
        self.home_tab = self.home_screen
        self.ai_tab = QWidget()
        self.workout_tab = QWidget()

        # Add tabs to the stacked widget
        self.central_stacked_widget.addWidget(self.home_tab)
        self.central_stacked_widget.addWidget(self.ai_tab)
        self.central_stacked_widget.addWidget(self.workout_tab)

        # Set the initial screen to home
        self.central_stacked_widget.setCurrentWidget(self.home_tab)

        # Initialize other attributes
        self.survey_completed = False
        self.ai_tab_accessed = False
        self.tts_mode = False

        # A stop button 
        self.stop_button = QPushButton("Stop Audio")
        self.stop_button.clicked.connect(self.stop_audio)
        self.stop_button.setVisible(False)  # Initially hidden

        # Create content areas
        self.create_content_area()
        self.create_tab_bar()

        #elevenlab
        self.last_announced_rep = None
        self.eleven_labs_client = ElevenLabs(api_key="sk_02c02e595901fe869a0db07bfceac0ad188ccf5d55da133d")
        self.is_speaking = False
        self.current_audio = None
        
        self.reps_left = 0
        self.time_left = 0

        # Set up AI and speech components
        self.gemini_api_key = "AIzaSyAnDOY0QfkgyucCZ8r323YiQ1ZULqGGWwc"
        self.workout_extractor = WorkoutExtractor(self.gemini_api_key)
        self.current_exercise = None
        self.meal_plan_extractor = MealPlanExtractor(self.gemini_api_key)
        self.threshold_adjuster = ThresholdAdjuster(self.gemini_api_key)
        self.setup_threshold_chat()

        genai.configure(api_key=self.gemini_api_key)
        self.genai_model = genai.GenerativeModel(
            model_name='gemini-1.5-flash', 
            system_instruction="You are a highly knowledgeable fitness assistant trainer. Your only goal is to assist people during their fitness journey. You will comprehensive and detailed advice about fitness and wellness.   ")
        self.chat = self.genai_model.start_chat(history=[])
        
         # Initialize camera-related attributes
        self.capture = None
        self.timer = None
        self.video_processor = VideoProcessor()
        # Set up camera
        self.setup_camera()

        self.threadpool = QThreadPool()

        self.workout_timer = QTimer(self)
        self.workout_timer.timeout.connect(self.main_workout_loop)
        self.workout_timer.start(30)  # Update every 30ms

        # Create chat interface
        self.create_chat_interface()

        #  attribute to track initial plan extraction
        self.initial_plan_extracted = False 


        # Define landmark names
        self.landmark_names = [
            'nose', 'left_eye_inner', 'left_eye', 'left_eye_outer',
            'right_eye_inner', 'right_eye', 'right_eye_outer',
            'left_ear', 'right_ear', 'mouth_left', 'mouth_right',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_pinky', 'right_pinky',
            'left_index', 'right_index', 'left_thumb', 'right_thumb',
            'left_hip', 'right_hip', 'left_knee', 'right_knee',
            'left_ankle', 'right_ankle', 'left_heel', 'right_heel',
            'left_foot_index', 'right_foot_index'
        ]

        # Connect signals
        if self.workout_plan_widget:
            self.workout_plan_widget.plan_updated.connect(self.on_workout_plan_updated)
            
    def on_workout_plan_updated(self):
        # This method is called when the workout plan is modified
        # You can use this to update any other parts of the UI that depend on the workout plan
        pass

    def text_to_speech(self, text):
        if self.is_speaking:
            self.stop_audio()
            return

        try:
            audio = self.eleven_labs_client.generate(
                text=text,
                voice = Voice(
                    voice_id='hwP9cnHIj7hHZyifOUIm',
                    settings=VoiceSettings(stability=0.85, similarity_boost=0.9, style=0.25, use_speaker_boost=True)
                )
                            )
            self.current_audio = audio
            self.is_speaking = True
            play(audio)
            self.is_speaking = False
            self.current_audio = None
        except Exception as e:
            print(f"Error in text-to-speech: {str(e)}")
            QMessageBox.warning(self, "Text-to-Speech Error", f"Failed to generate speech: {str(e)}")

    def cleanup_temp_audio(self, status, temp_audio_path):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()
            try:
                os.remove(temp_audio_path)
            except Exception as e:
                print(f"Error removing temporary audio file: {str(e)}")

    def save_thresholds(self):
        with open(self.threshold_file, 'w') as f:
            json.dump(self.video_processor.thresholds, f)

    def load_thresholds(self):
        if os.path.exists(self.threshold_file):
            with open(self.threshold_file, 'r') as f:
                loaded_thresholds = json.load(f)
                self.video_processor.thresholds.update(loaded_thresholds)


    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop_button.setVisible(False)
            
    def setup_threshold_chat(self):
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)

        self.threshold_chat_display = QTextEdit()
        self.threshold_chat_display.setReadOnly(True)
        chat_layout.addWidget(self.threshold_chat_display)

        self.threshold_chat_input = QLineEdit()
        self.threshold_chat_input.setPlaceholderText("Change the feedback behavior here...")
        self.threshold_chat_input.returnPressed.connect(self.process_threshold_adjustment)
        chat_layout.addWidget(self.threshold_chat_input)

        self.right_layout.addWidget(chat_widget)


    def process_threshold_adjustment(self):
        user_input = self.threshold_chat_input.text()
        self.threshold_chat_input.clear()

        new_threshold, _, _ = self.threshold_adjuster.adjust_threshold(user_input, self.video_processor.thresholds)
        
        if new_threshold is not None:
            response = self.threshold_adjuster.model.generate_content(self.threshold_adjuster.generate_prompt(user_input, self.video_processor.thresholds))
            result = self.threshold_adjuster.extract_json_from_response(response.text)
            
            if result and 'feedback_condition' in result:
                feedback_condition = result['feedback_condition']
                threshold_key = feedback_condition  # Use only the feedback condition as the key
                
                if threshold_key in self.video_processor.thresholds:
                    old_threshold = self.video_processor.thresholds[threshold_key]
                    self.video_processor.thresholds[threshold_key] = new_threshold
                    self.save_thresholds()  # Save thresholds immediately after updating
                    message = f"Adjusted {threshold_key} from {old_threshold} to {new_threshold} degrees."
                    self.threshold_chat_display.append(message)
                    
                    # Use text-to-speech for successful adjustments
                    speech_message = f"Threshold adjusted. {threshold_key} is now set to {new_threshold} degrees."
                    self.text_to_speech(speech_message)
                else:
                    message = f"Error: Invalid threshold key '{threshold_key}'. Available keys are: {', '.join(self.video_processor.thresholds.keys())}"
                    self.threshold_chat_display.append(message)
            else:
                message = "Error: Invalid response from AI. Please try again."
                self.threshold_chat_display.append(message)
        else:
            message = "Error: Failed to determine new threshold. Please try again with different wording."
            self.threshold_chat_display.append(message)

        print(message)  # This will print the message to the console for debugging

    def stop_audio(self):
        if self.is_speaking and self.current_audio:
            # This is a placeholder as ElevenLabs doesn't provide a direct way to stop playback
            # You might need to implement a custom solution or use a different audio playback library
            self.is_speaking = False
            self.current_audio = None
            print("Audio playback stopped")
            
    def update_workout_display(self, exercise_data):
        if not exercise_data:
            self.squat_info_label.setText("No squat data available")
            self.bicep_curl_info_label.setText("No bicep curl data available")
            return

        # Create formatted HTML strings for squat and bicep curl information
        squat_info = f"""
        <h3 style='color: #4CAF50;'>SQUATS</h3>
        <p><strong>Counter:</strong> {exercise_data.get('squat_counter', 0)}</p>
        <p><strong>State:</strong> {exercise_data.get('squat_state', '')}</p>
        <p><strong>Feedback:</strong><br>
        {' | '.join(exercise_data.get('squat_feedback', [])[:2])}</p>
        """

        bicep_curl_info = f"""
        <h3 style='color: #4CAF50;'>BICEP CURLS</h3>
        <p><strong>Counter:</strong> {exercise_data.get('curl_counter', 0)}</p>
        <p><strong>State:</strong> {exercise_data.get('curl_state', '')}</p>
        <p><strong>Feedback:</strong><br>
        {' | '.join(exercise_data.get('bicep_curl_feedback', [])[:2])}</p>
        """

        # Update the exercise info labels
        self.squat_info_label.setText(squat_info)
        self.bicep_curl_info_label.setText(bicep_curl_info)


    def update_frame_display(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.camera_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)
    
    def handle_exercise_reordering(self):
        current_exercise = self.workout_plan_widget.get_current_exercise()
        if current_exercise:
            if current_exercise['name'].lower() in ['bicep curl', 'squat']:
                self.current_exercise = current_exercise
                self.reps_left = self.workout_plan_widget.calculate_total_reps(current_exercise)
                self.video_processor.exercise_counter.set_total_reps(self.reps_left)
            else:
                self.current_exercise = None
                self.exercise_progress_label.setText("Please select a supported exercise (Bicep Curl or Squat)")
        else:
            self.current_exercise = None
            self.exercise_progress_label.setText("No exercises in the plan")

    def main_workout_loop(self):
        if self.capture is None or not self.capture.isOpened():
            return

        ret, frame = self.capture.read()
        if not ret:
            return

        current_exercise = self.workout_plan_widget.get_current_exercise()
        processed_frame, exercise_data = self.video_processor.process_frame(frame, current_exercise)

        if current_exercise and exercise_data:
                if current_exercise['name'].lower() in ['bicep curl', 'curl']:
                    reps_done = exercise_data['curl_counter']
                elif current_exercise['name'].lower() == 'squat':
                    reps_done = exercise_data['squat_counter']
                else:
                    reps_done = 0

                target_reps = current_exercise['reps'] * current_exercise['sets']
                self.reps_left = max(0, target_reps - reps_done)


                if 0 < self.reps_left <= 5 and self.reps_left != self.last_announced_rep:
                    if self.reps_left == 5:
                        self.text_to_speech("Only 5 reps left. You can do this!")
                    else:
                        self.text_to_speech(str(self.reps_left))
                    self.last_announced_rep = self.reps_left

                if self.reps_left == 0:
                    self.on_exercise_completed(current_exercise)
                    self.text_to_speech("Amazing, good job!")
                    self.last_announced_rep = None  # Reset for the next exercise
                
                # Update exercise progress display
                self.exercise_progress_label.setText(f"Reps left: {self.reps_left}")
        else:
            self.exercise_progress_label.setText("No exercise in progress")

        self.update_workout_display(exercise_data)
        self.update_frame_display(processed_frame)

    def on_exercise_selected(self, exercise):
            self.current_exercise = exercise
            if exercise['is_timed']:
                self.time_left = exercise['reps']
            else:
                self.reps_left = exercise['reps'] * exercise['sets']
            self.update_exercise_progress_display()

    def on_exercise_completed(self, exercise):
        self.scoreboard.add_points(10)
        self.workout_plan_widget.mark_current_exercise_completed()
        self.workout_plan_widget.next_exercise()
        next_exercise = self.workout_plan_widget.get_current_exercise()
        if next_exercise:
            self.current_exercise = next_exercise
            self.reps_left = self.workout_plan_widget.calculate_total_reps(next_exercise)
            self.video_processor.exercise_counter.reset_counter()
        else:
            self.current_exercise = None
            self.reps_left = 0
        self.last_announced_rep = None  # Reset for the new exercise


    def create_tab_bar(self):
        self.tab_bar = self.TabBar()
        self.tab_bar.addTab("home_icon.png", "Home")
        self.tab_bar.addTab("ai_icon.png", "ChatBox")
        self.tab_bar.addTab("workout_icon.png", "Workout")

        # Create a QToolBar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        # Create a central widget to hold the tab bar
        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.addStretch()
        central_layout.addWidget(self.tab_bar)
        central_layout.addStretch()

        # Set a fixed size for the tab bar
        self.tab_bar.setFixedSize(300, 50)
        
        # Connect tab bar index changes to the central_stacked_widget
        self.tab_bar.currentChanged.connect(self.on_tab_changed)

        # Add the central widget to the toolbar
        toolbar.addWidget(central_widget)

        # Create and add the theme toggle switch
        self.theme_toggle = ToggleSwitch()
        self.theme_toggle.stateChanged.connect(self.switch_theme)
        toolbar.addWidget(self.theme_toggle)

        # Add the toolbar to the main window
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def on_tab_changed(self, index):
            if index == 0:  # Home tab index
                self.central_stacked_widget.setCurrentWidget(self.home_tab)
                self.stop_camera()
            elif index == 1:  # AI tab index
                self.central_stacked_widget.setCurrentWidget(self.ai_tab)
                self.stop_camera()
                if not self.ai_tab_accessed:
                    self.ai_tab_accessed = True
                    self.show_survey_or_chat()
                    if self.survey_completed:
                        self.create_chat_interface()
            elif index == 2:  # Workout tab index
                self.central_stacked_widget.setCurrentWidget(self.workout_tab)
                self.start_camera()

    def setup_camera(self):
            if self.capture is None:
                try:
                    self.capture = cv2.VideoCapture(0)
                    if not self.capture.isOpened():
                        raise Exception("Failed to open camera")
                    self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    print("Camera setup successful")
                except Exception as e:
                    print(f"Error setting up camera: {str(e)}")

    def start_camera(self):
        if self.capture is None or not self.capture.isOpened():
            self.setup_camera()
        if self.capture is not None and self.capture.isOpened():
            self.main_workout_loop()  # Start the main workout loop
        else:
            print("Failed to start camera")

    def stop_camera(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def create_chat_interface(self):
        chat_widget = QWidget()
        chat_widget.setObjectName("chatWidget")
        chat_layout = QVBoxLayout(chat_widget)

        # Create the chat list widget
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet("background-color: #F0F0F0; border: none;")
        self.chat_list.setSpacing(10)
        self.chat_list.setWordWrap(True)
        chat_layout.addWidget(self.chat_list)

        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("How do I meal prep?")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
            }
        """)
        input_layout.addWidget(self.chat_input)

        self.send_button = QPushButton('')  # Store as an attribute of the class
        self.send_button.setIcon(QIcon('right-arrows.png'))
        self.send_button.setIconSize(QSize(24, 24))  
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 9px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        input_layout.addWidget(self.send_button)

        # Add the stop button to the input layout
        input_layout.addWidget(self.stop_button)

        chat_layout.addLayout(input_layout)

        self.chat_widget = chat_widget
        self.ai_layout.addWidget(chat_widget)

        # Add a button to view chat history
        self.history_button = QPushButton("View Chat History")
        self.history_button.clicked.connect(self.toggle_chat_log)
        input_layout.addWidget(self.history_button)
        
    def toggle_chat_log(self):
        if not self.is_chat_log_displayed:
            self.display_chat_log()
        else:
            self.restore_current_chat()

    def add_message(self, message, is_user):
        item = QListWidgetItem(self.chat_list)
        parent_width = self.chat_list.viewport().width()
        chat_bubble = create_chat_bubble(message, is_user, parent_width)
        
        if not is_user:
            controls_layout = QHBoxLayout()
            
            speaker_icon = QPushButton()
            speaker_icon.setIcon(QIcon('speaker_icon.png'))
            speaker_icon.clicked.connect(lambda: self.text_to_speech(message))
            controls_layout.addWidget(speaker_icon)
            
            chat_bubble.layout().addLayout(controls_layout)
        
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, chat_bubble)
        
        item.setSizeHint(chat_bubble.sizeHint())
        
        self.chat_list.scrollToBottom()

    def send_message(self, message=None, is_initial_prompt=False):
        if not message:
            message = self.chat_input.text()

        if message:
            self.add_message(message, True)
            self.chat_input.clear()
            
            try:
                worker = AIWorker(self.get_ai_response, message)
                worker.signals.finished.connect(lambda response: self.handle_ai_response(response, is_initial_prompt))
                worker.signals.error.connect(self.handle_ai_error)
                
                self.threadpool.start(worker)
                
                # Save the user message to the database
                self.db.save_message("User", message)
                
            except Exception as e:
                error_response = f"Error: Unable to process message. {str(e)}"
                self.add_message(error_response, False)
                self.db.save_message("System", error_response)
    
    def handle_ai_response(self, response, is_initial_prompt):
        self.add_message(response, False)
        
        # Save the AI response to the database
        self.db.save_message("AI", response)
        
        if is_initial_prompt and not self.initial_plan_extracted:
            self.extract_and_create_workout_plan(response)
    
    def handle_ai_error(self, error):
        error_response = f"Error: Unable to get AI response. {str(error)}"
        self.add_message(error_response, False)
        self.db.save_message("System", error_response)
    
    def get_ai_response(self, prompt):
        return self.chat.send_message(prompt).text
        
    def display_chat_log(self):
        try:
            # Store current chat messages
            self.current_chat_messages = [
                (self.chat_list.itemWidget(self.chat_list.item(i)).findChild(ChatBubble).toPlainText(),
                 self.chat_list.itemWidget(self.chat_list.item(i)).findChild(ChatBubble).is_user)
                for i in range(self.chat_list.count())
            ]
            
            # Clear the chat list and display chat history
            self.chat_list.clear()
            chat_history = self.db.get_chat_history()
            if chat_history:
                for timestamp, sender, message in chat_history:
                    self.add_message(f"[{timestamp}] {sender}: {message}", sender == "User")
            else:
                self.add_message("No chat history available.", False)
            
            self.is_chat_log_displayed = True
            self.history_button.setText("Return to Current Chat")

        except Exception as e:
            print(f"Error displaying chat log: {e}")
            QMessageBox.warning(self, "Error", f"Failed to display chat history: {str(e)}")

    def restore_current_chat(self):
        try:
            # Clear the chat list
            self.chat_list.clear()

            # Restore the current chat messages
            for message, is_user in self.current_chat_messages:
                self.add_message(message, is_user)
            
            self.is_chat_log_displayed = False
            self.history_button.setText("View Chat History")

        except Exception as e:
            print(f"Error restoring current chat: {e}")
            QMessageBox.warning(self, "Error", f"Failed to restore current chat: {str(e)}")

    class TabBar(QWidget):
        currentChanged = pyqtSignal(int)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.layout = QHBoxLayout(self)
            self.layout.setContentsMargins(5, 5, 5, 5)
            self.layout.setSpacing(10)
            self.buttons = []
            self.current_index = 0
            self._is_dark_mode = True  # Default to dark mode
            self.indicator = QWidget(self)
            self.indicator.setStyleSheet("""
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 15px;
            """)
            self.indicator.raise_()  # Ensure indicator is above buttons

            # Define default colors
            self.text_color = "rgba(255, 255, 255, 0.7)"
            self.active_color = "rgba(255, 255, 255, 0.2)"
            self.indicator_color = "rgba(255, 255, 255, 0.2)"
            
        def set_theme(self, is_dark_mode):
            self._is_dark_mode = is_dark_mode
            if is_dark_mode:
                self.text_color = "rgba(255, 255, 255, 0.7)"
                self.active_color = "rgba(255, 255, 255, 0.2)"
                self.indicator_color = "rgba(255, 255, 255, 0.2)"
            else:
                self.text_color = "rgba(0, 0, 0, 0.7)"
                self.active_color = "rgba(0, 0, 0, 0.1)"
                self.indicator_color = "rgba(0, 0, 0, 0.2)"

            for button in self.buttons:
                button.setStyleSheet(f"color: {self.text_color};")

            self.indicator.setStyleSheet(f"background-color: {self.indicator_color}; border-radius: 15px;")
            self.updateButtonStyles()

        def addTab(self, icon, text):
            button = QPushButton(QIcon(icon), text)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, index=len(self.buttons): self.setCurrentIndex(index))
            self.layout.addWidget(button)
            self.buttons.append(button)
            self.updateButtonStyles()

        def setCurrentIndex(self, index):
            if index != self.current_index and 0 <= index < len(self.buttons):
                self.current_index = index
                self.updateButtonStyles()
                self.animateIndicator(self.buttons[index])
                self.currentChanged.emit(index)

        def updateButtonStyles(self):
            for i, button in enumerate(self.buttons):
                if i == self.current_index:
                    button.setChecked(True)
                    button.setStyleSheet(f"background-color: {self.active_color}; color: {'white' if self._is_dark_mode else 'black'};")
                else:
                    button.setChecked(False)
                    button.setStyleSheet(f"background-color: transparent; color: {self.text_color};")
            self.updateIndicator(self.buttons[self.current_index])


        def updateIndicator(self, button):
            self.indicator.setGeometry(button.geometry())

        def animateIndicator(self, target_button):
            animation = QPropertyAnimation(self.indicator, b"geometry")
            animation.setDuration(250)
            animation.setStartValue(self.indicator.geometry())
            animation.setEndValue(target_button.geometry())
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.updateButtonStyles()

        def showEvent(self, event):
            super().showEvent(event)
            self.updateButtonStyles()

    def switch_theme(self, is_checked):
        if is_checked:
            self.setStyleSheet(self.dark_style)
            text_color = "white"
        else:
            self.setStyleSheet(self.light_style)
            text_color = "black"
        
        # Update tab bar appearance
        self.tab_bar.set_theme(is_checked)
        
        # Update other components that need theme change
        self.home_screen.update_theme(is_checked)
        
        # Update Workout Tab theme
        self.update_workout_tab_theme(is_checked)

    def update_workout_tab_theme(self, is_dark_mode):
        if is_dark_mode:
            self.workout_tab.setStyleSheet(self.dark_style)
        else:
            self.workout_tab.setStyleSheet(self.light_style)
        
        # Update the exercise info labels
        label_style = f"""
            color: {'white' if is_dark_mode else 'black'};
            background-color: {'#2d2d2d' if is_dark_mode else '#f0f0f0'};
            border-radius: 15px;
            padding: 10px;
            font-size: 16px;
        """
        self.squat_info_label.setStyleSheet(label_style)
        self.bicep_curl_info_label.setStyleSheet(label_style)

        # Update the exercise info frame if needed
        self.exercise_info_frame.setStyleSheet(f"""
            background-color: {'#2d2d2d' if is_dark_mode else '#f0f0f0'};
            border-radius: 15px;
            padding: 10px;
        """)

    def show_survey_or_chat(self):
        if not self.survey_completed:
            if not hasattr(self, 'survey_widget'):
                self.create_survey_form()
            self.survey_widget.show()
            if hasattr(self, 'chat_widget'):
                self.chat_widget.hide()
        else:
            if hasattr(self, 'survey_widget'):
                self.survey_widget.hide()
            self.show_chat_interface()

    def show_dashboard(self, email):
        if self.dashboard is None:
            self.dashboard = Dashboard(self.meal_plan)  # Pass meal_plan here
        self.central_stacked_widget.addWidget(self.dashboard)
        self.central_stacked_widget.setCurrentWidget(self.dashboard)

    
    def convert_landmarks_to_dict(self, landmarks):
        landmark_dict = {}
        landmark_names = [
            'nose', 'left_eye_inner', 'left_eye', 'left_eye_outer',
            'right_eye_inner', 'right_eye', 'right_eye_outer',
            'left_ear', 'right_ear', 'mouth_left', 'mouth_right',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_pinky', 'right_pinky',
            'left_index', 'right_index', 'left_thumb', 'right_thumb',
            'left_hip', 'right_hip', 'left_knee', 'right_knee',
            'left_ankle', 'right_ankle', 'left_heel', 'right_heel',
            'left_foot_index', 'right_foot_index'
        ]
        for name, landmark in zip(landmark_names, landmarks):
            landmark_dict[name] = {'x': landmark.x, 'y': landmark.y, 'z': landmark.z}
        return landmark_dict
    
    def update_exercise_display(self, exercise_data):
        # Create a formatted string with all the exercise information
        info_text = f"""
        BICEP CURLS: {exercise_data['curl_counter']}
        SQUATS: {exercise_data['squat_counter']}
        
        CURL STATE: {exercise_data['curl_state']}
        SQUAT STATE: {exercise_data['squat_state']}
        
        BICEP CURL FEEDBACK:
        {' | '.join(exercise_data['bicep_curl_feedback'][:2])}
        
        SQUAT FEEDBACK:
        {' | '.join(exercise_data['squat_feedback'][:2])}
        """
        
        # Update the exercise info label
        self.exercise_info_label.setText(info_text)

    def update_exercise_progress_display(self):
        if self.current_exercise:
            if self.current_exercise['is_timed']:
                self.exercise_progress_label.setText(f"Time left: {self.time_left}s")
            else:
                self.exercise_progress_label.setText(f"Reps left: {self.reps_left}")
        else:
            self.exercise_progress_label.setText("No exercise in progress")

    def closeEvent(self, event):
            # Release the camera when closing the application
            self.stop_camera()
            super().closeEvent(event)

    def process_survey_data(self):
        # Collect data from survey form
        survey_data = {
            "weight": self.weight_input.text(),
            "height": self.height_input.text(),
            "gender": self.gender_group.checkedButton().text().lower() if self.gender_group.checkedButton() else "",
            "activity": self.activity_group.checkedButton().text().lower() if self.activity_group.checkedButton() else "",
            "goal": self.goal_group.checkedButton().text().lower() if self.goal_group.checkedButton() else "",
            "intensity": self.intensity_group.checkedButton().text().lower() if self.intensity_group.checkedButton() else ""
        }
        
        # Validate the input
        if not all(survey_data.values()):
            QMessageBox.warning(self, "Incomplete Form", "Please fill out all fields before submitting.")
            return



        # Create initial prompt for AI
        initial_prompt = self.create_initial_prompt(survey_data)
        
        # Send initial prompt to AI and display response
        response = self.send_message(initial_prompt, is_initial_prompt=True)

        # Hide survey form and show chat interface
        self.survey_widget.hide()
        self.show_chat_interface()

        # Extract workout plan from AI response
        self.workout_plan = self.workout_extractor.extract_workout_plan(response)
        if not self.workout_plan:
            logging.warning("Failed to extract workout plan, attempting to clean and structure response")
            self.workout_plan = self.workout_extractor.clean_and_structure_response(response)

        if self.workout_plan:
            self.update_workout_plan_widget()
            self.initial_plan_extracted = True
        else:
            logging.error("Failed to create workout plan")

        # Enable chat functionality
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)

        
        worker = AIWorker(self.get_ai_response, initial_prompt)
        worker.signals.finished.connect(self.handle_ai_response)
        worker.signals.error.connect(self.handle_ai_error)
        
        self.threadpool.start(worker)
        self.prompt_for_meal_plan()

    def prompt_for_meal_plan(self):
        if hasattr(self, 'survey_data') and self.survey_data:
            self.add_message("Do you want to create a 7-day meal plan based on your survey information too?", False)
            self.chat_input.setPlaceholderText("Type 'Yes' or 'No'")
            self.chat_input.returnPressed.connect(self.handle_meal_plan_response)
        else:
            self.add_message("Please complete the survey before creating a meal plan.", False)
    
    def handle_meal_plan_response(self):
        response = self.chat_input.text().lower()
        self.chat_input.clear()
        self.add_message(response, True)
        
        if response == "yes":
            self.generate_meal_plan()
        else:
            self.add_message("Alright, no meal plan will be created.", False)
        
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.returnPressed.disconnect(self.handle_meal_plan_response)
        self.chat_input.returnPressed.connect(self.send_message)
    
    def generate_meal_plan(self):
        self.add_message("Generating your 7-day meal plan...", False)
        if hasattr(self, 'survey_data') and self.survey_data:
            self.meal_plan = self.meal_plan_extractor.extract_meal_plan(self.survey_data)
            self.display_meal_plan(self.meal_plan)
        else:
            error_message = "Error: Survey data is not available. Please complete the survey first."
            self.add_message(error_message, False)
            print(error_message)  # For debugging purposes
    
    def display_meal_plan(self, meal_plan):
        meal_plan_text = self.format_meal_plan(meal_plan)
        self.add_message(meal_plan_text, False)
        self.add_message("Your 7-day meal plan has been created and is displayed above.", False)
    
    def format_meal_plan(self, meal_plan):
        formatted_plan = "7-Day Meal Plan:\n\n"
        for day in meal_plan:
            formatted_plan += f"{day['day']}:\n"
            for meal, food in day['meals'].items():
                formatted_plan += f"  {meal.capitalize()}: {food}\n"
            formatted_plan += "\n"
        return formatted_plan
    
    def create_content_area(self):
        # Home Tab
        home_layout = QVBoxLayout(self.home_tab)
        home_layout.addWidget(self.home_screen)

        # AI Assistant Tab
        self.setup_ai_tab()

        # Workout Tab
        self.setup_workout_tab()

        # Add tabs to the stacked widget
        self.central_stacked_widget.addWidget(self.home_tab)
        self.central_stacked_widget.addWidget(self.ai_tab)
        self.central_stacked_widget.addWidget(self.workout_tab)

    def get_ai_response(self, prompt):
        return self.chat.send_message(prompt).text
    
    def setup_ai_tab(self):
            self.ai_layout = QVBoxLayout(self.ai_tab)
            # Show survey or chat based on completion status
            self.show_survey_or_chat()
            # Create chat interface (initially hidden)
            self.create_chat_interface()
            self.chat_widget.hide()
    def handle_ai_response(self, response):
        self.extract_and_create_workout_plan(response)

    def handle_ai_error(self, error):
        QMessageBox.critical(self, "Error", f"An error occurred: {error}")

    def extract_and_create_workout_plan(self, response):
        workout_plan = self.workout_extractor.extract_workout_plan(response)
        if not workout_plan:
            workout_plan = self.workout_extractor.clean_and_structure_response(response)

        if workout_plan:
            self.workout_plan = workout_plan
            self.update_workout_plan_widget()
            self.initial_plan_extracted = True
            if self.central_stacked_widget.currentWidget() == self.workout_tab:
                self.start_camera()
        else:
            QMessageBox.warning(self, "Warning", "Failed to create workout plan. Please try again.")

    def update_workout_plan_widget(self):
        if self.workout_plan_widget is None:
            self.workout_plan_widget = WorkoutPlanWidget(self.workout_plan)
            self.workout_plan_widget.exercise_selected.connect(self.on_exercise_selected)
            self.workout_plan_widget.plan_updated.connect(self.on_workout_plan_updated)
            self.workout_plan_widget.exercise_completed.connect(self.on_exercise_completed)
            self.right_layout.addWidget(self.workout_plan_widget)
        else:
            self.workout_plan_widget.set_workout_plan(self.workout_plan)

        # Ensure the workout tab shows the updated plan
        self.central_stacked_widget.setCurrentWidget(self.workout_tab)

    def send_message(self, message=None, is_initial_prompt=False):
        if not message:
            message = self.chat_input.text()

        if message:
            self.add_message(message, True)
            self.chat_input.clear()
            
            worker = AIWorker(self.get_ai_response, message)
            worker.signals.finished.connect(self.handle_chat_response)
            worker.signals.error.connect(self.handle_ai_error)
            
            self.threadpool.start(worker)

    def handle_chat_response(self, response):
        self.add_message(response, False)

    def setup_workout_tab(self):
        if not hasattr(self, 'workout_layout'):
            self.workout_layout = QHBoxLayout(self.workout_tab)
            
            # Left side: Camera feed and exercise info
            left_layout = QVBoxLayout()
            
            # Camera feed
            self.camera_label = QLabel()
            self.camera_label.setStyleSheet("background-color: #3d3d3d; border-radius: 15px;")
            self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            left_layout.addWidget(self.camera_label, 4)

            # Exercise info display
            self.exercise_info_frame = QFrame()
            self.exercise_info_frame.setStyleSheet("background-color: #2d2d2d; border-radius: 15px; padding: 10px;")
            exercise_info_layout = QHBoxLayout(self.exercise_info_frame)

            self.squat_info_label = QLabel()
            self.bicep_curl_info_label = QLabel()
            for label in [self.squat_info_label, self.bicep_curl_info_label]:
                label.setStyleSheet("color: white; font-size: 14px;")
                label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                label.setWordWrap(True)
            
            exercise_info_layout.addWidget(self.squat_info_label)
            exercise_info_layout.addWidget(self.bicep_curl_info_label)

            left_layout.addWidget(self.exercise_info_frame, 2)

            # Add exercise progress display
            self.exercise_progress_label = QLabel()
            self.exercise_progress_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
            left_layout.addWidget(self.exercise_progress_label)

            self.workout_layout.addLayout(left_layout, 2)

            # Right side: Workout plan
            self.right_layout = QVBoxLayout()
            
            # Add scoreboard
            self.right_layout.addWidget(self.scoreboard, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
            self.workout_layout.addLayout(self.right_layout, 1)

             # Ensure the camera is started if we're on the workout tab
            if self.central_stacked_widget.currentWidget() == self.workout_tab:
                self.start_camera()

        # Update only the right side with the new workout plan
        self.update_workout_plan_widget()

    def create_survey_form(self):
        survey_widget = QWidget()
        survey_widget.setObjectName("surveyWidget")
        survey_layout = QVBoxLayout(survey_widget)
        form_layout = QFormLayout()

        # Weight
        weight_label = QLabel("1. What is your current weight? (kg)")
        weight_label.setObjectName("weightLabel")
        weight_label.setStyleSheet("""#weightLabel {background-color: transparent; font-size: 20px;}""")
        
        self.weight_input = QLineEdit()
        self.weight_input.setObjectName("weight1")
        form_layout.addRow(weight_label)
        form_layout.addRow(self.weight_input)

        # Height
        height_label = QLabel("2. How tall are you? (cm)")
        height_label.setObjectName("heightLabel")
        height_label.setStyleSheet("""
                #heightLabel {
                        background-color: transparent; 
                        font-size: 20px;
                                      }
                                   """)
        self.height_input = QLineEdit()
        self.height_input.setObjectName("height1")
        form_layout.addRow(height_label)
        form_layout.addRow(self.height_input)

        # Gender
        gender_label = QLabel("3. What is your sex?")
        gender_label.setObjectName("genderLabel")
        gender_label.setStyleSheet("""
                #genderLabel {
                        background-color: transparent; 
                        font-size: 20px;
                                      }
                                   """)
        self.gender_group = QButtonGroup()
        gender_layout = QHBoxLayout()
        male_radio = QRadioButton("Male")
        female_radio = QRadioButton("Female")
        self.gender_group.setObjectName("genderButtonGroup")
        self.gender_group.addButton(male_radio)
        self.gender_group.addButton(female_radio)
        gender_layout.addWidget(male_radio)
        gender_layout.addWidget(female_radio)
        form_layout.addRow(gender_label)
        form_layout.addRow(gender_layout)

        # Activity Level
        activity_label = QLabel("4. How active is your current lifestyle?")
        activity_label.setObjectName("activityLabel")
        activity_label.setStyleSheet("""
                #activityLabel {
                        background-color: transparent; 
                        font-size: 20px;
                                     }
                                     """)
        self.activity_group = QButtonGroup()
        self.activity_group.setObjectName("activityButtonGroup")
        activity_layout = QVBoxLayout()
        activity_options = ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extremely Active"]
        for option in activity_options:
            radio = QRadioButton(option)
            self.activity_group.addButton(radio)
            activity_layout.addWidget(radio)
        form_layout.addRow(activity_label)
        form_layout.addRow(activity_layout)

        # Fitness Goal
        goal_label = QLabel("5. What is your fitness goal?")
        goal_label.setObjectName("goalLabel")
        goal_label.setStyleSheet("""
                #goalLabel {
                        background-color: transparent; 
                        font-size: 20px;
                                      }
                                   """)
        self.goal_group = QButtonGroup()
        self.goal_group.setObjectName("goalButtonGroup")
        goal_layout = QVBoxLayout()
        goal_options = ["Lose Weight", "Gain Muscle", "Recovery", "Improve Fitness"]
        for option in goal_options:
            radio = QRadioButton(option)
            self.goal_group.addButton(radio)
            goal_layout.addWidget(radio)
        form_layout.addRow(goal_label)
        form_layout.addRow(goal_layout)

        # Workout Intensity
        intensity_label = QLabel("6. Which workout intensity do you prefer?")
        intensity_label.setObjectName("intensityLabel")
        intensity_label.setStyleSheet("""
                #intensityLabel {
                        background-color: transparent; 
                        font-size: 20px;
                                      }
                                   """)
        self.intensity_group = QButtonGroup()
        intensity_layout = QVBoxLayout()
        intensity_options = ["Extreme", "Intense", "Moderate", "Chill", "Very Chill"]
        for option in intensity_options:
            radio = QRadioButton(option)
            self.intensity_group.addButton(radio)
            intensity_layout.addWidget(radio)
        form_layout.addRow(intensity_label)
        form_layout.addRow(intensity_layout)

        survey_layout.addLayout(form_layout)

        submit_button = QPushButton("Generate Workout Plan")
        submit_button.setObjectName("submitbutton")
        submit_button.setStyleSheet("""
                #submitbutton {
                        border-radius: 12px;
                        background-color: #4CAF50;
                        font-size: 20px;
                                      }
                                    
                #submitbutton:hover {
                background-color: #45a049;
            }
                                   """)
        submit_button.clicked.connect(self.process_survey_data)
        survey_layout.addWidget(submit_button)

        self.survey_widget = survey_widget
        self.ai_layout.addWidget(survey_widget)


    def update_toggle_style(self, button, is_active):
        if is_active:
            button.setStyleSheet("background-color: #4CAF50; color: white;")
        else:
            button.setStyleSheet("")

    def show_chat_interface(self):
        self.chat_widget.show()
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)

    def create_initial_prompt(self, survey_data):
        return f"""
        You are a specialized workout plan generator. Create a strict 7-day workout plan based on the following information:
        - Weight: {survey_data['weight']} kg
        - Height: {survey_data['height']} cm
        - Gender: {survey_data['gender']}
        - Current activity level: {survey_data['activity']}
        - Fitness goal: {survey_data['goal']}
        - Desired Workout Intensity: {survey_data['intensity']}

        Adhere to these rules strictly:
        1. Provide exactly 7 days of workouts, labeled Day 1 through Day 7.
        2. Each day must have 3-5 exercises.
        3. Use only the following exercises:
        Reps-based: curl, squat, lunge, pushup, shoulder press
        Duration-based: plank, jumping jack, jump rope, knee tap, mountain climber
        4. Format each exercise as follows:
        Reps-based: [Exercise Name]: [Sets] x [Reps]
        Duration-based: [Exercise Name]: [Duration] seconds
        5. Do not include any introductions, explanations, or dietary advice.
        6. Use the exact exercise names provided, with correct spelling.

        Example of correct formatting:
        Day 1:
        Jumping Jack: 30 seconds
        Pushup: 3 x 10
        Plank: 60 seconds
        Squat: 3 x 15
        Mountain Climber: 45 seconds

        Your response must follow this exact structure for all 7 days. DO NOT deviate from this format or include any additional information.

        Begin the 7-day workout plan NOW:
        """

    def clear_survey_form(self):
        self.weight_input.clear()
        self.height_input.clear()
        for button in self.gender_group.buttons():
            button.setChecked(False)
        self.activity_combo.setCurrentIndex(0)
        self.goal_combo.setCurrentIndex(0)
        self.dietary_combo.setCurrentIndex(0)

    def send_message(self, message=None, is_initial_prompt=False):
        if not message:
            message = self.chat_input.text()

        if message:
            self.add_message(message, True)
            self.chat_input.clear()
            
            try:
                response = self.chat.send_message(message).text
                self.add_message(response, False)
                
                # Save the message and response to the database
                self.db.save_message("User", message)
                self.db.save_message("AI", response)
                
                if is_initial_prompt and not self.initial_plan_extracted:
                    self.extract_and_create_workout_plan(response)
                
            except Exception as e:
                error_response = f"Error: Unable to get AI response. {str(e)}"
                self.add_message(error_response, False)
                self.db.save_message("User", message)
                self.db.save_message("AI", error_response)
            
            return response

    def create_workout_plan_widget(self, workout_plan):
        if not workout_plan:
            logging.error("Workout plan is empty or None")
            return

        if self.workout_plan_widget is None:
            self.workout_plan_widget = WorkoutPlanWidget(workout_plan)
            self.workout_plan_widget.exercise_selected.connect(self.on_exercise_selected)
        else:
            # Only update the plan if it hasn't been extracted yet
            if not self.initial_plan_extracted:
                self.workout_plan_widget.set_workout_plan(workout_plan)

        # Ensure the workout tab shows the updated plan
        self.central_stacked_widget.setCurrentWidget(self.workout_tab)
        
    def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.send_message()
            else:
                super().keyPressEvent(event)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_chat_bubbles()


    def update_chat_bubbles(self):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            widget = self.chat_list.itemWidget(item)
            if widget:
                bubble = widget.findChild(ChatBubble)
                if bubble:
                    bubble.setFixedWidth(int(self.chat_list.viewport().width() * 0.9))
                    bubble.sizeChange()
                    item.setSizeHint(widget.sizeHint())
        self.chat_list.updateGeometry()

    def update_workout_plan_widget(self):
        # Remove the old workout plan widget if it exists
        if hasattr(self, 'workout_plan_widget') and self.workout_plan_widget is not None:
            self.right_layout.removeWidget(self.workout_plan_widget)
            self.workout_plan_widget.deleteLater()

        # Create or update the workout_plan_widget
        if not hasattr(self, 'workout_plan') or self.workout_plan is None:
            self.workout_plan = []  # Initialize with an empty list if it doesn't exist

        self.workout_plan_widget = WorkoutPlanWidget(self.workout_plan)
        self.workout_plan_widget.exercise_selected.connect(self.on_exercise_selected)
        self.workout_plan_widget.plan_updated.connect(self.on_workout_plan_updated)
        self.workout_plan_widget.exercise_completed.connect(self.on_exercise_completed)
        self.right_layout.addWidget(self.workout_plan_widget)

    def update_workout_plan(self, workout_plan):
        logging.info("Updating workout plan")
        
        # Clear existing workout list
        self.workout_list_widget.clear()

        try:
            # Update the WorkoutPlanWidget
            if hasattr(self, 'workout_plan_widget') and self.workout_plan_widget:
                self.workout_plan_widget.deleteLater()
            self.create_workout_plan_widget(workout_plan)

            # Add detailed workout plan to the list widget for backup/alternative view
            for day in workout_plan:
                day_item = f"{day['day']}:"
                self.workout_list_widget.addItem(day_item)
                for exercise in day['exercises']:
                    exercise_item = f"  - {exercise['name']}: {exercise['sets']} sets"
                    if exercise['reps']:
                        if exercise['is_timed']:
                            exercise_item += f" of {exercise['reps']} {exercise['unit']}s"
                        else:
                            exercise_item += f" of {exercise['reps']} {exercise['unit']}s"
                    self.workout_list_widget.addItem(exercise_item)

            logging.info("Workout plan updated successfully")
        except Exception as e:
            logging.error(f"Error updating workout plan: {str(e)}")
            # Fallback to simple list view if there's an error with the WorkoutPlanWidget
            if not self.workout_list_widget.count():
                self.workout_list_widget.addItem("Error loading workout plan. Please try again.")

        # Ensure the workout tab shows the updated plan
        self.tab_widget.setCurrentWidget(self.workout_tab)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WorkoutApp()
    window.show()
    sys.exit(app.exec())