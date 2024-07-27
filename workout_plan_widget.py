from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect, QVBoxLayout, QWidget, QScrollArea, QLineEdit, QComboBox, QFormLayout, QDialog, QMessageBox
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QDrag, QPainter, QColor, QPen, QBrush

class ExerciseItem(QFrame):
    delete_clicked = pyqtSignal(dict)
    drag_started = pyqtSignal(dict)

    def __init__(self, exercise):
        super().__init__()
        self.exercise = exercise
        self.setStyleSheet("""
            background-color: #3d3d3d;
            border-radius: 15px;
            padding: 10px;
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.name_label = QLabel(exercise['name'])
        self.name_label.setStyleSheet("""
            color: #ffffff; 
            font-weight: bold; 
            font-size: 14px;
        """)        
        layout.addWidget(self.name_label)
        
        if exercise.get('is_timed', False):
            reps_label = QLabel(f"{exercise['reps']} seconds")
        else:
            reps_label = QLabel(f"{exercise.get('sets', '1')} x {exercise['reps']}")
        reps_label.setStyleSheet("""
            color: #cccccc; 
            font-size: 12px;
        """)        
        layout.addWidget(reps_label)

        self.completion_label = QLabel("✓")
        self.completion_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 16px;")
        self.completion_label.setVisible(False)
        layout.addWidget(self.completion_label)

        delete_button = QPushButton("-")
        delete_button.setStyleSheet("""
            background-color: #ff4d4d;
            color: white;
            border-radius: 10px;
            padding: 5px;
            font-size: 12px;
            font-weight: bold;
            max-width: 20px;
        """)
        delete_button.clicked.connect(self.delete_exercise)
        layout.addWidget(delete_button)

        self.setFixedHeight(60)

    def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(self.exercise['name'])
                drag.setMimeData(mime_data)
                
                pixmap = self.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(event.position().toPoint())

                fade_effect = QGraphicsOpacityEffect(self)
                self.setGraphicsEffect(fade_effect)
                fade_animation = QPropertyAnimation(fade_effect, b"opacity")
                fade_animation.setDuration(300)
                fade_animation.setStartValue(1)
                fade_animation.setEndValue(0.5)
                fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                fade_animation.start()

                drag.exec()

                fade_animation.setStartValue(0.5)
                fade_animation.setEndValue(1)
                fade_animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QPen(QColor("#2d2d2d"), 2))
        painter.setBrush(QBrush(QColor("#3d3d3d")))
        painter.drawRoundedRect(self.rect(), 15, 15)

        painter.end()

    def mark_completed(self):
        self.completion_label.setVisible(True)

    def delete_exercise(self):
        self.delete_clicked.emit(self.exercise)

class DayWidget(QFrame):
    exercise_added = pyqtSignal(str, dict)
    exercise_deleted = pyqtSignal(str, dict)
    exercise_reordered = pyqtSignal(str, list)

    def __init__(self, day_plan):
        super().__init__()
        self.day_plan = day_plan
        self.is_expanded = True
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("background-color: #2d2d2d; border-radius: 10px; padding: 10px;")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)
        
        self.header_button = QPushButton(self.day_plan['day'])
        self.header_button.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border: none;
                text-align: left;
                padding: 10px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.header_button.clicked.connect(self.toggle_expand)
        self.main_layout.addWidget(self.header_button)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget)

        self.update_exercises()

        self.setAcceptDrops(True)

    def update_exercises(self):
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for exercise in self.day_plan['exercises']:
            exercise_item = ExerciseItem(exercise)
            exercise_item.delete_clicked.connect(self.delete_exercise)
            self.content_layout.addWidget(exercise_item)

        add_button = QPushButton("+")
        add_button.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            border-radius: 15px;
            font-size: 20px;
            font-weight: bold;
            padding: 5px;
            max-width: 30px;
        """)
        add_button.clicked.connect(self.add_exercise)
        self.content_layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignRight)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        drop_position = event.position().y()
        source_exercise_name = event.mimeData().text()
        
        source_index = next(i for i, e in enumerate(self.day_plan['exercises']) if e['name'] == source_exercise_name)
        source_exercise = self.day_plan['exercises'].pop(source_index)

        target_index = min(int(drop_position // 70), len(self.day_plan['exercises']))
        self.day_plan['exercises'].insert(target_index, source_exercise)

        self.update_exercises()
        self.exercise_reordered.emit(self.day_plan['day'], self.day_plan['exercises'])

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)

    def add_exercise(self):
        dialog = AddExerciseDialog(self)
        if dialog.exec():
            new_exercise = dialog.get_exercise_data()
            self.day_plan['exercises'].append(new_exercise)
            self.update_exercises()
            self.exercise_added.emit(self.day_plan['day'], new_exercise)

    def delete_exercise(self, exercise):
        self.day_plan['exercises'].remove(exercise)
        self.update_exercises()
        self.exercise_deleted.emit(self.day_plan['day'], exercise)

class WorkoutPlanWidget(QWidget):
    exercise_selected = pyqtSignal(dict)
    plan_updated = pyqtSignal()
    exercise_completed = pyqtSignal(dict)  

    def __init__(self, workout_plan):
        super().__init__()
        self.workout_plan = workout_plan
        self.current_day = 0
        self.current_exercise = 0
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(20)
        
        self.update_plan()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def update_plan(self):
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().setParent(None)
        
        for day_plan in self.workout_plan:
            day_widget = DayWidget(day_plan)
            day_widget.exercise_added.connect(self.on_exercise_added)
            day_widget.exercise_deleted.connect(self.on_exercise_deleted)
            day_widget.exercise_reordered.connect(self.on_exercise_reordered)
            self.content_layout.addWidget(day_widget)

    def on_exercise_added(self, day, exercise):
        self.plan_updated.emit()

    def on_exercise_deleted(self, day, exercise):
        self.plan_updated.emit()

    def on_exercise_reordered(self, day, exercises):
        for i, day_plan in enumerate(self.workout_plan):
            if day_plan['day'] == day:
                self.workout_plan[i]['exercises'] = exercises
                break
        self.update_current_exercise()
        self.plan_updated.emit()

    def next_exercise(self):
        current_day = self.workout_plan[self.current_day]
        current_exercise = current_day['exercises'][self.current_exercise]
        
        day_widget = self.content_layout.itemAt(self.current_day).widget()
        exercise_item = day_widget.content_layout.itemAt(self.current_exercise).widget()
        exercise_item.mark_completed()
        
        self.current_exercise += 1
        if self.current_exercise >= len(current_day['exercises']):
            self.current_exercise = 0
            self.current_day += 1
            if self.current_day >= len(self.workout_plan):
                self.current_day = 0  # Loop back to the first day
        
        next_exercise = self.workout_plan[self.current_day]['exercises'][self.current_exercise]
        self.exercise_selected.emit(next_exercise)

    def mark_current_exercise_completed(self):
        if self.current_day < len(self.workout_plan) and self.current_exercise < len(self.workout_plan[self.current_day]['exercises']):
            day_widget = self.content_layout.itemAt(self.current_day).widget()
            if day_widget and isinstance(day_widget, DayWidget):
                exercise_item = day_widget.content_layout.itemAt(self.current_exercise).widget()
                if exercise_item and isinstance(exercise_item, ExerciseItem):
                    exercise_item.mark_completed()

    def get_next_exercise(self):
            self.current_exercise += 1
            if self.current_exercise >= len(self.workout_plan[self.current_day]['exercises']):
                self.current_exercise = 0
                self.current_day += 1
                if self.current_day >= len(self.workout_plan):
                    self.current_day = 0  # Loop back to the first day
                    return None  # Workout completed

            return self.workout_plan[self.current_day]['exercises'][self.current_exercise]


    def get_current_exercise(self):
        if self.current_day < len(self.workout_plan) and self.current_exercise < len(self.workout_plan[self.current_day]['exercises']):
            return self.workout_plan[self.current_day]['exercises'][self.current_exercise]
        return None
    
    def set_workout_plan(self, workout_plan):
            self.workout_plan = workout_plan
            self.current_day = 0
            self.current_exercise = 0
            self.update_plan()

    def calculate_total_reps(self, exercise):
        return exercise['sets'] * exercise['reps']

    def update_current_exercise(self):
        top_exercise = self.get_top_exercise()
        if top_exercise:
            self.exercise_selected.emit(top_exercise)
            
    def get_top_exercise(self):
        if self.workout_plan and self.workout_plan[self.current_day]['exercises']:
            return self.workout_plan[self.current_day]['exercises'][0]
        return None


class AddExerciseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Exercise")
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        layout.addRow("Exercise Name:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Reps", "Time"])
        layout.addRow("Exercise Type:", self.type_combo)

        self.value_input = QLineEdit()
        layout.addRow("Reps/Seconds:", self.value_input)

        self.sets_input = QLineEdit()
        layout.addRow("Sets:", self.sets_input)

        add_button = QPushButton("Add Exercise")
        add_button.clicked.connect(self.validate_and_accept)
        layout.addRow(add_button)

    def validate_and_accept(self):
        if not self.name_input.text():
            self.show_error("Exercise name is required.")
            return

        try:
            value = int(self.value_input.text())
            if value <= 0:
                raise ValueError
        except ValueError:
            self.show_error("Please enter a valid positive integer for Reps/Seconds.")
            return

        try:
            sets = int(self.sets_input.text())
            if sets <= 0:
                raise ValueError
        except ValueError:
            self.show_error("Please enter a valid positive integer for Sets.")
            return

        self.accept()

    def show_error(self, message):
        QMessageBox.warning(self, "Input Error", message)

    def get_exercise_data(self):
        return {
            "name": self.name_input.text(),
            "is_timed": self.type_combo.currentText() == "Time",
            "reps": int(self.value_input.text()),
            "sets": int(self.sets_input.text())
        }