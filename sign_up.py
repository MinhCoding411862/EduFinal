from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QStackedWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

class SignUpWidget(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.load_stylesheets()
        self.initUI()

    def load_stylesheets(self):
        with open("signuplight.qss", "r") as f:
            self.light_style = f.read()
        with open("signupstyle.qss", "r") as f:
            self.dark_style = f.read()
        self.setStyleSheet(self.light_style)  # Default to light style

    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left side (form)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(50, 50, 50, 50)
        form_layout.setSpacing(20)

        # Logo
        logo_label = QLabel("HaminG")
        logo_label.setObjectName("logo")
        form_layout.addWidget(logo_label)

        form_layout.addStretch(1)

        # Title
        title = QLabel("Create an account")
        title.setObjectName("title")
        form_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Let's get started with your 30 day free trial.")
        subtitle.setObjectName("subtitle")
        form_layout.addWidget(subtitle)

        # Form fields
        self.name_input = self.create_input("Name")
        self.email_input = self.create_input("Email")
        self.password_input = self.create_input("Password", is_password=True)
        
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.password_input)

        # Sign up button
        signup_button = QPushButton("Create account")
        signup_button.setObjectName("signUpButton")
        signup_button.clicked.connect(self.sign_up)
        form_layout.addWidget(signup_button)

        # Social sign-up buttons
        google_button = self.create_social_button("Sign up with Google")
        form_layout.addWidget(google_button)
        
        twitter_button = self.create_social_button("Sign in with Twitter")
        form_layout.addWidget(twitter_button)

        form_layout.addStretch(1)

        # Login link
        login_link = QPushButton("Already have an account? Log in")
        login_link.setObjectName("loginLink")
        login_link.clicked.connect(self.go_back_to_login)
        form_layout.addWidget(login_link)

        main_layout.addWidget(form_widget, 1)

        # Right side (image)
        image_label = QLabel()
        pixmap = QPixmap("ath.jpg")
        image_label.setPixmap(pixmap.scaled(600, 800, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        image_label.setScaledContents(True)
        main_layout.addWidget(image_label, 1)

    def create_input(self, placeholder, is_password=False):
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        if is_password:
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
        return input_field

    def create_social_button(self, text):
        button = QPushButton(text)
        button.setObjectName("socialButton")
        return button

    def sign_up(self):
        # Implement sign up logic here
        pass

    def go_back_to_login(self):
        self.stacked_widget.setCurrentIndex(0)  # Assuming the login page is at index 0

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    stacked_widget = QStackedWidget()
    widget = SignUpWidget(stacked_widget)
    stacked_widget.addWidget(widget)
    stacked_widget.setFixedSize(1000, 800)  # Set a fixed size for the window
    stacked_widget.show()
    sys.exit(app.exec())