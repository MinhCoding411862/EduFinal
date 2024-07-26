import sys
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel,QWidget,QMainWindow,QHBoxLayout,QListWidget,QApplication, QPushButton,QScrollArea,QGridLayout,QLineEdit,QListWidgetItem
from PyQt6.QtCharts import QChart, QChartView, QBarSet, QStackedBarSeries, QBarCategoryAxis, QValueAxis
from PyQt6.QtCore import Qt, QMargins,QRectF,QPointF
from PyQt6.QtGui import QColor, QPainter, QFont, QPen
from db_manager import setup_database, get_score_data
class CustomChartView(QChartView):
    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        self.setMouseTracking(True)
        self.tooltip = QLabel(self)
        self.tooltip.setStyleSheet("""
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        """)
        self.tooltip.hide()
        self.chart_rect = QRectF()
        self.bar_sets = []
        self.dates = []
        self.column_width = 0
        self.update_chart_data()

    def update_chart_data(self):
        if self.chart():
            self.chart_rect = self.chart().plotArea()
            series = self.chart().series()[0]
            if isinstance(series, QStackedBarSeries):
                self.bar_sets = series.barSets()
                axis_x = self.chart().axes(Qt.Orientation.Horizontal)[0]
                self.dates = axis_x.categories()
                self.column_width = self.chart_rect.width() / len(self.dates)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_chart_data()

    def mouseMoveEvent(self, event):
        pos = QPointF(event.position())  # Convert to QPointF
        if self.chart_rect.contains(pos):
            x = int((pos.x() - self.chart_rect.left()) / self.column_width)
            if 0 <= x < len(self.dates):
                self.show_tooltip(x, pos)
            else:
                self.tooltip.hide()
        else:
            self.tooltip.hide()

    def leaveEvent(self, event):
        self.tooltip.hide()

    def show_tooltip(self, x, pos):
        squat = self.bar_sets[0].at(x)
        bicep_curl = self.bar_sets[1].at(x)
        push_up = self.bar_sets[2].at(x)
        total = squat + bicep_curl + push_up
        date = self.dates[x]
        tooltip_text = f"<b>Date: {date}</b><br>Total: {total}<br>"
        tooltip_text += f"<font color='#FF6B6B'>Squat: {squat}</font><br>"
        tooltip_text += f"<font color='#4ECDC4'>Bicep Curl: {bicep_curl}</font><br>"
        tooltip_text += f"<font color='#45B7D1'>Push Up: {push_up}</font>"
        self.tooltip.setText(tooltip_text)
        self.tooltip.adjustSize()
        self.position_tooltip(pos)
        self.tooltip.show()

    def position_tooltip(self, cursor_pos):
        tooltip_rect = self.tooltip.rect()
        chart_rect = self.rect()
        
        x = cursor_pos.x() + 10
        y = cursor_pos.y() - tooltip_rect.height() // 2
        
        if x + tooltip_rect.width() > chart_rect.width():
            x = cursor_pos.x() - tooltip_rect.width() - 10
        
        y = max(0, min(y, chart_rect.height() - tooltip_rect.height()))
        
        self.tooltip.move(int(x), int(y))

class LeaderboardItem(QWidget):
    def __init__(self, rank, name, points, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        rank_label = QLabel(str(rank))
        rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_label.setStyleSheet(f"""
            background-color: {"#FFD700" if rank == 1 else "#C0C0C0" if rank == 2 else "#CD7F32"};
            color: #1e1e1e;
            border-radius: 15px;
            padding: 5px;
            font-weight: bold;
        """)
        rank_label.setFixedSize(30, 30)
        
        name_label = QLabel(name)
        name_label.setFont(QFont("Arial", 12))
        
        points_label = QLabel(str(points))
        points_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        points_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(rank_label)
        layout.addWidget(name_label, 1)
        layout.addWidget(points_label)

class ActivenessGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.percentage = 0
        self.setMinimumSize(200, 120)  # Increased width to ensure semicircle shape

    def setPercentage(self, value):
        self.percentage = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate the rectangle for the arc
        width = self.width()
        height = self.height()
        diameter = min(width, height * 2)
        rect = QRectF((width - diameter) / 2, height - diameter / 2, diameter, diameter)
        # Draw background arc
        painter.setPen(QPen(QColor("#333333"), 10))
        painter.drawArc(rect, 0, 180 * 16)

        # Determine color based on percentage
        if self.percentage < 31:
            color = QColor("#FF6B6B")  # Red
        elif self.percentage < 61:
            color = QColor("#4ECDC4")  # Blue
        else:
            color = QColor("#45B7D1")  # Green

        # Draw foreground arc
        painter.setPen(QPen(color, 10))
        span_angle = int(self.percentage * 1.8 * 16)
        painter.drawArc(rect, 180 * 16, -span_angle)

        # Draw percentage text
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        text_rect = QRectF(0, height / 2, width, height / 2)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{self.percentage}%")


class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        setup_database()
        self.setup_ui()
        self.load_stylesheet()

    def load_stylesheet(self):
        with open('dashboard_style.qss', 'r') as f:
            self.setStyleSheet(f.read())

    def setup_ui(self):
        # Create a central widget and set it as the central widget of the main window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a main vertical layout for the central widget
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create a widget to hold all the dashboard content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Add the top bar
        content_layout.addLayout(self.create_top_bar())

        # Add the main metric section
        content_layout.addWidget(self.create_main_metric())

        # Create and add the grid layout for the four widgets
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.create_leaderboard(), 0, 0)
        grid_layout.addWidget(self.create_activeness_rate(), 0, 1)
        grid_layout.addWidget(self.create_recent_activities(), 1, 0)
        grid_layout.addWidget(self.create_ai_coach(), 1, 1)
        content_layout.addLayout(grid_layout)

        # Set the content widget as the widget for the scroll area
        scroll_area.setWidget(content_widget)

        # Add the scroll area to the main layout
        main_layout.addWidget(scroll_area)

    def create_top_bar(self):
        top_bar = QHBoxLayout()
        dashboard_label = QLabel("Dashboard")
        dashboard_label.setObjectName("dashboardTitle")
        top_bar.addWidget(dashboard_label)
        top_bar.addStretch()
        start_workout_btn = QPushButton("Start Workout")
        start_workout_btn.setObjectName("startWorkoutBtn")
        top_bar.addWidget(start_workout_btn)
        return top_bar
    
    def create_main_metric(self):
        frame = QFrame()
        frame.setObjectName("mainMetric")
        frame.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        layout = QVBoxLayout(frame)

        # Create a container for the title and description
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Weekly Exercise Progress")
        title.setObjectName("widgetTitle")
        title.setStyleSheet("font-size: 25px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        layout.addWidget(header_container)

        # Fetch data from the database
        chart_data, _ = get_score_data()

        if not chart_data:
            # No data available
            no_data_label = QLabel("No exercise data available. Start working out to see your progress!")
            no_data_label.setWordWrap(True)
            no_data_label.setStyleSheet("font-size: 14px; color: #aaaaaa; margin-top: 10px;")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data_label)
        else:
            # Only display the last 7 days
            chart_data = chart_data[-7:]

            chart = QChart()
            series = QStackedBarSeries()

            squat_set = QBarSet("Squat")
            squat_set.setColor(QColor("#FF6B6B"))
            bicep_curl_set = QBarSet("Bicep Curl")
            bicep_curl_set.setColor(QColor("#4ECDC4"))
            push_up_set = QBarSet("Push Up")
            push_up_set.setColor(QColor("#45B7D1"))

            dates = []
            for row in chart_data:
                dates.append(row['score_date'].strftime('%b %d'))
                squat_set.append(row['squat_points'])
                bicep_curl_set.append(row['bicep_curl_points'])
                push_up_set.append(row['push_up_points'])

            series.append(squat_set)
            series.append(bicep_curl_set)
            series.append(push_up_set)

            chart.addSeries(series)

            axis_x = QBarCategoryAxis()
            axis_x.append(dates)
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axis_x)

            axis_y = QValueAxis()
            max_points = max(row['total_points'] for row in chart_data)
            axis_y.setRange(0, max_points)
            axis_y.setTickCount(6)
            axis_y.setLabelFormat("%d")
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)

            # Style the chart for dark theme
            chart.setBackgroundVisible(True)
            chart.setBackgroundBrush(QColor("#2d2d2d"))
            chart.setPlotAreaBackgroundVisible(False)
            chart.setMargins(QMargins(10, 10, 10, 10))

            axis_y.setGridLineVisible(True)
            axis_y.setGridLineColor(QColor("#3a3a3a"))
            axis_x.setGridLineVisible(False)

            axis_x.setLabelsColor(QColor("#ffffff"))
            axis_y.setLabelsColor(QColor("#ffffff"))

            font = QFont()
            font.setPointSize(8)
            axis_x.setLabelsFont(font)
            axis_y.setLabelsFont(font)

            chart.legend().setVisible(True)
            chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
            chart.legend().setFont(font)
            chart.legend().setLabelColor(QColor("#ffffff"))
            chart.setTitle("")

            chart_view = CustomChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            chart_view.setMinimumHeight(300)
            layout.addWidget(chart_view)

        return frame

    def create_widget_frame(self, title):
        frame = QFrame()
        frame.setObjectName("widgetFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)  # Increased padding
        layout.setSpacing(15)  # Increased spacing between elements

        title_label = QLabel(title)
        title_label.setObjectName("widgetTitle")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
            padding-bottom: 10px;
        """)
        layout.addWidget(title_label)

        return frame, layout

    def create_leaderboard(self):
        frame, layout = self.create_widget_frame("Leaderboard")

        _, total_points = get_score_data()

        leaderboard_data = [
            (1, "You", total_points),
            (2, "Michael", 450),
            (3, "David", 400)
        ]

        for rank, name, points in leaderboard_data:
            item = LeaderboardItem(rank, name, points)
            layout.addWidget(item)

        layout.addStretch()
        return frame

    def create_activeness_rate(self):
        frame, layout = self.create_widget_frame("Activeness Rate")
        
        score_data, _ = get_score_data()
        days_considered = min(30, len(score_data))
        recent_data = score_data[:days_considered]
        
        active_days = sum(1 for day in recent_data if day['total_points'] >= 40)
        activeness_rate = round((active_days / days_considered) * 100)

        gauge = ActivenessGauge()
        gauge.setPercentage(activeness_rate)
        
        # Create a container widget to center the gauge
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(gauge, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(container)
        layout.addStretch()
        
        return frame

    def create_recent_activities(self):
        frame, layout = self.create_widget_frame("Recent Activities")

        activities_list = QListWidget()
        activities_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: #ffffff;
                font-size: 16px;  /* Increased font size */
                border: none;
            }
            QListWidget::item {
                padding: 5px 0;
            }
        """)

        data, _ = get_score_data()
        
        recent_data = sorted(data, key=lambda x: x['score_date'], reverse=True)[:4]

        for row in recent_data:
            activity_string = f"{row['score_date'].strftime('%Y-%m-%d')}: Workout completed - +{row['total_points']} points"
            item = QListWidgetItem(activity_string)
            activities_list.addItem(item)

        layout.addWidget(activities_list)
        return frame

    def create_ai_coach(self):
        frame, layout = self.create_widget_frame("AI Coach")
        chat_input = QLineEdit()
        chat_input.setPlaceholderText("Ask your AI coach...")
        chat_input.returnPressed.connect(self.on_chat_send)
        layout.addWidget(chat_input)

        return frame

    def on_chat_send(self):
        chat_input = self.sender()
        message = chat_input.text()
        if message:
            print(f"Sending message to AI coach: {message}")
            chat_input.clear()
        # Here you would typically process the message and update the chat display

# ... (rest of the Dashboard class remains the same)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())