import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QCheckBox, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QToolButton, QLineEdit, QListWidget, QListWidgetItem, QFrame,
                             QMessageBox, QStackedWidget)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QImage, QColor, QPainter, QPalette, QBrush, QTransform, QMouseEvent, QCursor
from sign_up import SignUpWidget  # Import the SignUpWidget


class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.text())
        super().mousePressEvent(event)


class FeatureItem(QWidget):
    def __init__(self, icon, title, description, text_color="white"):
        super().__init__()
        
        self.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        icon_label = QLabel(icon)
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        text_layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setProperty("isTitle", True)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.desc_label = QLabel(description)
        self.desc_label.setFont(QFont("Arial", 8))
        self.desc_label.setWordWrap(True)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        
        layout.addWidget(icon_label)
        layout.addLayout(text_layout, 1)
        
        self.set_text_color(text_color)
    
    def set_text_color(self, color):
        self.title_label.setStyleSheet(f"color: {color};")
        self.desc_label.setStyleSheet(f"color: {color};")

class SplitScreen(QWidget):
    login_successful = pyqtSignal(str)  # Signal to emit when login is successful
    def __init__(self, stacked_widget):
            super().__init__()
            self.stacked_widget = stacked_widget
            self.initUI()

    def initUI(self):
            main_layout = QVBoxLayout(self)
            main_layout.setSpacing(0)
            main_layout.setContentsMargins(0, 0, 0, 0)

            # Right panel (now centered)
            self.right_panel = QWidget()
            self.right_panel.setObjectName("rightPanel")
            right_layout = QVBoxLayout(self.right_panel)
            right_layout.setContentsMargins(50, 50, 50, 50)

            # Login form
            self.setup_login_form(right_layout)

            # Add panel to main layout
            main_layout.addWidget(self.right_panel, alignment=Qt.AlignmentFlag.AlignCenter)

    def update_theme(self, is_dark_mode):
        if is_dark_mode:
            self.setStyleSheet("""
                #rightPanel { background-color: #2d2d2d; }
                QLabel, QCheckBox { color: white;  background-color: transparent}
                #welcomeback { color: #4CAF50;  background-color: transparent;}
                QLineEdit { background-color: #3d3d3d; color: white; border: 1px solid #555; }
                QPushButton { background-color: #4CAF50; color: white; }
                #forgotPassword { color: #2196F3; background-color: transparent; }
                QCheckBox::indicator:checked {
                    background-color: #4CAF50;
                    border: 2px solid #4CAF50;
                    content: '✓';
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                #rightPanel { background-color: white; }
                QLabel, QCheckBox { color: black; background-color: transparent }
                #welcomeback { color: #4CAF50; background-color: transparent; }
                QLineEdit { background-color: #f0f0f0; color: black; border: 1px solid #ccc; }
                #passwordInput { background-color: #f0f0f0; }
                QPushButton { background-color: #4CAF50; color: white; }
                #forgotPassword { color: #2196F3; background-color: transparent; }
                QCheckBox::indicator:checked {
                    background-color: #4CAF50;
                    border: 2px solid #4CAF50;
                    content: '✓';
                    border-radius: 12px;
                }
            """)
    def setup_login_form(self, layout):
        # Subtitle
        subtitle = QLabel("Welcome back!")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("welcomeback")
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # Input fields
        self.email = self.create_styled_input("Email or Phone number")
        self.email.setObjectName("email")
        layout.addWidget(self.email)
        layout.addSpacing(10)

           # Password input with show/hide button
        password_layout = QHBoxLayout()
        self.password = self.create_styled_input("Password", is_password=True)
        self.password.setObjectName("passwordInput")
        self.password.setStyleSheet(" #passwordInput {background-color: transprarent;} ")
        password_layout.addWidget(self.password)

        self.password_toggle = QPushButton()
        self.password_toggle.setIcon(QIcon("hide.png"))
        self.password_toggle.setObjectName("passwordToggle")
        self.password_toggle.pressed.connect(self.show_password)
        self.password_toggle.released.connect(self.hide_password)
        password_layout.addWidget(self.password_toggle)

        layout.addLayout(password_layout)
        layout.addSpacing(10)

        # Remember me checkbox and Forgot Password link
        remember_forgot_layout = QHBoxLayout()
        self.remember_me = QCheckBox("Remember me")
        self.remember_me.setObjectName("rememberMe")
        remember_forgot_layout.addWidget(self.remember_me)

        forgot_password = QPushButton("Forgot Password?")
        forgot_password.setObjectName("forgotPassword")
        forgot_password.clicked.connect(self.forgot_password_clicked)
        remember_forgot_layout.addWidget(forgot_password, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(remember_forgot_layout)
        layout.addSpacing(10)

        # Sign up button
        sign_up_button = QPushButton("Sign in")
        sign_up_button.setObjectName("signinbutton")
        sign_up_button.clicked.connect(self.sign_up)
        layout.addWidget(sign_up_button)
        layout.addSpacing(20)

        # Or divider
        or_layout = QHBoxLayout()
        left_line = QFrame()
        left_line.setFrameShape(QFrame.Shape.HLine)
        right_line = QFrame()
        right_line.setFrameShape(QFrame.Shape.HLine)
        or_label = QLabel("or")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        or_layout.addWidget(left_line)
        or_layout.addWidget(or_label)
        or_layout.addWidget(right_line)
        
        layout.addLayout(or_layout)
        layout.addSpacing(20)

        # Google sign up button
        google_button = self.create_google_button()
        layout.addWidget(google_button)

        # Add this line after your Google button
        apple_button = self.create_apple_button()
        layout.addWidget(apple_button)

        # Login link
        login_text = 'Don\'t have an account? <a href="sign_up.py" style="color: #2196F3; text-decoration: none;">Sign Up now</a>'
        login_link = ClickableLabel(login_text)
        login_link.setObjectName("loginLink")
        login_link.setTextFormat(Qt.TextFormat.RichText)
        login_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_link.clicked.connect(self.open_signup_page)
        layout.addWidget(login_link)
        layout.addStretch()


    def open_signup_page(self):
            signup_widget = SignUpWidget(self.stacked_widget)
            self.stacked_widget.addWidget(signup_widget)
            self.stacked_widget.setCurrentWidget(signup_widget)

    def create_google_button(self):
        google_button = QPushButton("Google")
        google_button.setIcon(QIcon("google.png"))
        google_button.setIconSize(QSize(18, 18))
        google_button.setFont(QFont("Arial", 10))
        google_button.setObjectName("googlesign")
        
        # Create a horizontal layout to position icon and text
        button_layout = QHBoxLayout(google_button)
        button_layout.setContentsMargins(10, 0, 10, 0)
        button_layout.setSpacing(10)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.setObjectName("button12")

        
        # Move the icon to the left
        google_button.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        return google_button
    def create_apple_button(self):
        apple_button = QPushButton("Apple")
        apple_button.setIcon(QIcon("apple.png"))
        apple_button.setIconSize(QSize(18, 18))
        apple_button.setFont(QFont("Arial", 10))
        apple_button.setObjectName("applebutton")
        
        # Create a horizontal layout to position icon and text
        button_layout = QHBoxLayout(apple_button)
        button_layout.setContentsMargins(10, 0, 10, 0)
        button_layout.setSpacing(10)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Move the icon to the left
        apple_button.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        return apple_button
    
    def create_styled_input(self, placeholder, is_password=False):
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        if is_password:
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
        return input_field

    def show_password(self):
        self.password.setEchoMode(QLineEdit.EchoMode.Normal)
        self.password_toggle.setIcon(QIcon("eye.png"))

    def hide_password(self):
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_toggle.setIcon(QIcon("hide.png"))

    def forgot_password_clicked(self):
        # Implement forgot password functionality
        print("Forgot password clicked")

    def sign_up(self):
        email = self.email.text()
        password = self.password.text()
        QMessageBox.information(self, 'Sign Up', f'Signed up with:\nEmail: {email}')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_layout()

    def update_layout(self):
        width = self.width()
        self.right_panel.setFixedWidth(int(width * 0.8))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    stacked_widget = QStackedWidget()
    ex = SplitScreen(stacked_widget)
    stacked_widget.addWidget(ex)
    stacked_widget.setGeometry(100, 100, 1000, 600)
    stacked_widget.setWindowTitle('Workout Assistant - Home')
    stacked_widget.show()
    sys.exit(app.exec())