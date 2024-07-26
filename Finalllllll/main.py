import sys
from PyQt6.QtWidgets import QApplication
from login import LoginPage
from back2back import Dashboard  # Assuming your dashboard class is in a file named dashboard.py

class MainApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.login_page = LoginPage()
        self.dashboard = None

    def run(self):
        self.login_page.login_successful.connect(self.show_dashboard)
        self.login_page.show()
        sys.exit(self.app.exec())

    def show_dashboard(self, username):
        self.login_page.hide()
        self.dashboard = Dashboard()
        self.dashboard.show()
        # You can pass the username to the dashboard if needed
        # self.dashboard.set_user(username)

if __name__ == "__main__":
    main_app = MainApplication()
    main_app.run()