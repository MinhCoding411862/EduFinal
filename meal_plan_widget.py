from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QScrollArea
from PyQt6.QtCore import Qt

class MealPlanWidget(QWidget):
    def __init__(self, meal_plan=None):
        super().__init__()
        self.meal_plan = meal_plan
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        self.update_plan()

    def update_plan(self):
        # Clear existing widgets
        for i in reversed(range(self.content_layout.count())): 
            self.content_layout.itemAt(i).widget().setParent(None)

        if self.meal_plan:
            for day in self.meal_plan:
                day_widget = self.create_day_widget(day)
                self.content_layout.addWidget(day_widget)
        else:
            self.display_no_plan_message()

    def create_day_widget(self, day):
        day_widget = QWidget()
        day_layout = QVBoxLayout(day_widget)
        
        day_label = QLabel(day['day'])
        day_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        day_layout.addWidget(day_label)
        
        for meal, food in day['meals'].items():
            meal_label = QLabel(f"{meal.capitalize()}: {food}")
            meal_label.setStyleSheet("color: #cccccc; font-size: 14px;")
            day_layout.addWidget(meal_label)
        
        day_widget.setStyleSheet("background-color: #2d2d2d; border-radius: 10px; padding: 10px; margin-bottom: 10px;")
        return day_widget

    def display_no_plan_message(self):
        message_label = QLabel("No meal plan generated yet.")
        message_label.setStyleSheet("""
            color: #cccccc;
            font-size: 16px;
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 10px;
            qproperty-alignment: AlignCenter;
        """)
        self.content_layout.addWidget(message_label)

    def set_meal_plan(self, meal_plan):
        self.meal_plan = meal_plan
        self.update_plan()