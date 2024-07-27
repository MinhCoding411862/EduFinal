import sys
import cv2
import os
import mysql.connector
from mysql.connector import Error
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
from home_tab import SplitScreen
from demo1 import VideoProcessor
from workout_plan_widget import WorkoutPlanWidget
from elevenlabs import Voice, VoiceSettings, play
from elevenlabs.client import ElevenLabs


class MistakeTracker:
    def __init__(self):
        self.mistakes_log = {
            'bicep_curl': {'incorrect_form': 0, 'wrong_weight': 0, 'other': 0},
            'squat': {'incorrect_form': 0, 'wrong_depth': 0, 'other': 0}
        }

    def update_mistakes(self, exercise_data):
        self.mistakes_log['bicep_curl']['incorrect_form'] += exercise_data['bicep_curl_feedback'].count('incorrect_form')
        self.mistakes_log['bicep_curl']['wrong_weight'] += exercise_data['bicep_curl_feedback'].count('wrong_weight')
        self.mistakes_log['bicep_curl']['other'] += exercise_data['bicep_curl_feedback'].count('other')
        
        self.mistakes_log['squat']['incorrect_form'] += exercise_data['squat_feedback'].count('incorrect_form')
        self.mistakes_log['squat']['wrong_depth'] += exercise_data['squat_feedback'].count('wrong_depth')
        self.mistakes_log['squat']['other'] += exercise_data['squat_feedback'].count('other')

    def generate_mistakes_report(self):
        report = "Exercise Mistakes Report\n\n"

        for exercise, mistakes in self.mistakes_log.items():
            report += f"{exercise.upper()} MISTAKES:\n"
            for mistake_type, count in mistakes.items():
                report += f"  - {mistake_type.replace('_', ' ').title()}: {count}\n"
            report += "\n"
        
        return report

    def save_mistakes_report(self, filename='mistakes_report.txt'):
        report = self.generate_mistakes_report()
        with open(filename, 'w') as file:
            file.write(report)
        print(f"Report saved to {filename}")
