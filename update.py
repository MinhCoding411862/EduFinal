import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QListWidget,
                             QFrame, QGridLayout, QScrollArea, QLineEdit, QSizePolicy)
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QPieSeries, QDateTimeAxis
from PyQt6.QtCore import Qt, QDateTime, QSize
from PyQt6.QtGui import QPainter, QColor, QIcon

class SidebarButton(QPushButton):
    def __init__(self, text, icon_name, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setIcon(QIcon(f"icons/{icon_name}.svg"))
        self.setIconSize(QSize(20, 20))

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_ui()
        self.load_stylesheet()

    def load_stylesheet(self):
        with open('dashboard_style.qss', 'r') as f:
            self.setStyleSheet(f.read())

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Top bar
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Dashboard"))
        top_bar.addStretch()
        start_workout_btn = QPushButton("Start Workout")
        start_workout_btn.setObjectName("startWorkoutBtn")
        top_bar.addWidget(start_workout_btn)
        main_layout.addLayout(top_bar)

        # Main metric section with line graph
        main_layout.addWidget(self.create_main_metric())

        # Four widgets in 2x2 grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.create_leaderboard(), 0, 0)
        grid_layout.addWidget(self.create_point_distribution(), 0, 1)
        grid_layout.addWidget(self.create_recent_activities(), 1, 0)
        grid_layout.addWidget(self.create_ai_coach(), 1, 1)
        main_layout.addLayout(grid_layout)

    def create_main_metric(self):
        frame = QFrame()
        frame.setObjectName("mainMetric")
        layout = QVBoxLayout(frame)

        header = QHBoxLayout()
        header.addWidget(QLabel("User Points Over Time"))
        header.addStretch()
        header.addWidget(QLabel("Last 30 days"))
        layout.addLayout(header)

        points_label = QLabel("Total Points: 240")
        points_label.setObjectName("totalPoints")
        layout.addWidget(points_label)

        chart = QChart()
        series = QLineSeries()
        
        # Add sample data for the last 30 days
        current_date = QDateTime.currentDateTime()
        for i in range(30):
            date = current_date.addDays(-29 + i)
            points = i * 10  # This will create a rising trend
            series.append(date.toMSecsSinceEpoch(), points)
        
        chart.addSeries(series)
        
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM dd")
        axis_x.setTickCount(6)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        axis_y.setTickCount(5)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        chart.legend().hide()
        chart.setBackgroundVisible(False)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setFixedHeight(200)
        layout.addWidget(chart_view)

        return frame

    def create_leaderboard(self):
        frame = QFrame()
        frame.setObjectName("leaderboard")
        layout = QVBoxLayout(frame)

        layout.addWidget(QLabel("Leaderboard"))
        leaderboard = QListWidget()
        leaderboard.addItems(["1. User A - 500 pts", "2. User B - 450 pts", "3. User C - 400 pts"])
        layout.addWidget(leaderboard)

        return frame

    def create_point_distribution(self):
        frame = QFrame()
        frame.setObjectName("pointDistribution")
        layout = QVBoxLayout(frame)

        layout.addWidget(QLabel("Point Distribution"))

        chart = QChart()
        series = QPieSeries()
        
        series.append("Workouts", 50)
        series.append("Challenges", 30)
        series.append("Consistency", 20)
        
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(chart_view)

        return frame

    def create_recent_activities(self):
        frame = QFrame()
        frame.setObjectName("recentActivities")
        layout = QVBoxLayout(frame)

        layout.addWidget(QLabel("Recent Activities"))
        activities_list = QListWidget()
        activities_list.addItems([
            "2023-07-22: Workout completed - +15 points",
            "2023-07-21: Challenge completed - +20 points",
            "2023-07-20: Consistency bonus - +10 points"
        ])
        layout.addWidget(activities_list)

        return frame

    def create_ai_coach(self):
        frame = QFrame()
        frame.setObjectName("aiCoach")
        layout = QVBoxLayout(frame)

        layout.addWidget(QLabel("AI Coach"))
        chat_input = QLineEdit()
        chat_input.setPlaceholderText("Ask your AI coach...")
        layout.addWidget(chat_input)
        chat_button = QPushButton("Send")
        chat_button.setObjectName("sendButton")
        chat_button.clicked.connect(self.on_chat_send)
        layout.addWidget(chat_button)

        return frame

    def on_chat_send(self):
        print("Sending message to AI coach")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())