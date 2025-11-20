"""
공통 스타일 정의 - 모든 모듈에서 사용
"""
import sys
import os

def resource_path(relative_path: str) -> str:
    """PyInstaller 빌드 환경과 개발 환경 모두에서 assets 경로를 올바르게 찾는다."""
    if hasattr(sys, "_MEIPASS"):
        base = os.path.join(sys._MEIPASS, "assets")
    else:
        base = os.path.join(os.path.abspath("."), "assets")
    return os.path.join(base, relative_path)

class Style:
    """통일된 스타일 상수 - 세련된 전문가 스타일"""
    BG_MAIN = "#f5f5f5"
    BG_CARD = "#ffffff"
    TEXT_PRIMARY = "#1a1a1a"
    TEXT_SECONDARY = "#666666"
    ACCENT = "#1a1a1a"
    ACCENT_HOVER = "#333333"
    SUCCESS = "#4CAF50"
    SUCCESS_HOVER = "#45a049"
    WARNING = "#FF9800"
    ERROR = "#f44336"
    ERROR_HOVER = "#da190b"

    # 버튼 스타일 템플릿
    @staticmethod
    def primary_button():
        return f"""
            QPushButton {{
                background-color: {Style.ACCENT};
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton:hover:enabled {{
                background-color: {Style.ACCENT_HOVER};
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
        """

    @staticmethod
    def success_button():
        return f"""
            QPushButton {{
                background-color: {Style.SUCCESS};
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton:hover:enabled {{
                background-color: {Style.SUCCESS_HOVER};
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
        """

    @staticmethod
    def error_button():
        return f"""
            QPushButton {{
                background-color: {Style.ERROR};
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton:hover:enabled {{
                background-color: {Style.ERROR_HOVER};
            }}
            QPushButton:disabled {{
                background-color: #E6B0AA;
                color: #888888;
            }}
        """

    @staticmethod
    def secondary_button():
        return f"""
            QPushButton {{
                background-color: {Style.BG_CARD};
                color: {Style.TEXT_PRIMARY};
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: #e0e0e0;
            }}
        """

    @staticmethod
    def small_button():
        return f"""
            QPushButton {{
                background-color: {Style.ACCENT};
                color: white;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover:enabled {{
                background-color: {Style.ACCENT_HOVER};
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
            }}
        """

    @staticmethod
    def card_style():
        return """
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 16px;
            }
        """

    @staticmethod
    def main_window():
        return f"""
            QMainWindow {{
                background-color: {Style.BG_MAIN};
            }}
        """

    @staticmethod
    def progress_bar():
        return f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #e8edf3;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {Style.ACCENT};
                border-radius: 4px;
            }}
        """

    @staticmethod
    def checkbox():
        return f"""
            QCheckBox {{
                font-size: 13px;
                color: {Style.TEXT_PRIMARY};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #7f8c8d;
                background: #ffffff;
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid #3498db;
            }}
            QCheckBox::indicator:checked {{
                background-color: #1a1a1a;
                border: 2px solid #1a1a1a;
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: #3498db;
                border: 2px solid #3498db;
            }}
        """

    @staticmethod
    def combobox():
        return f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #dde4ed;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                color: {Style.TEXT_PRIMARY};
            }}
            QComboBox:hover {{
                border: 1px solid {Style.ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """

    @staticmethod
    def lineedit():
        return f"""
            QLineEdit {{
                background-color: white;
                border: 1px solid #dde4ed;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                color: {Style.TEXT_PRIMARY};
            }}
            QLineEdit:hover {{
                border: 1px solid {Style.ACCENT};
            }}
            QLineEdit:focus {{
                border: 1px solid {Style.ACCENT};
            }}
        """

    @staticmethod
    def radio_button():
        return f"""
            QRadioButton {{
                font-size: 13px;
                color: {Style.TEXT_PRIMARY};
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #7f8c8d;
                background: #ffffff;
            }}
            QRadioButton::indicator:hover {{
                border: 2px solid #3498db;
            }}
            QRadioButton::indicator:checked {{
                background-color: #1a1a1a;
                border: 2px solid #1a1a1a;
            }}
            QRadioButton::indicator:checked:hover {{
                background-color: #3498db;
                border: 2px solid #3498db;
            }}
        """

    @staticmethod
    def spinbox():
        return f"""
            QDoubleSpinBox, QSpinBox {{
                background-color: #ffffff;
                border: 1px solid #dde4ed;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                color: {Style.TEXT_PRIMARY};
                font-weight: 500;
            }}
            QDoubleSpinBox:hover, QSpinBox:hover {{
                border: 1px solid {Style.ACCENT};
                background-color: #ffffff;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus {{
                border: 1px solid {Style.ACCENT};
                background-color: #ffffff;
            }}
        """

    @staticmethod
    def datetimeedit():
        return f"""
            QDateTimeEdit {{
                background-color: white;
                border: 1px solid #dde4ed;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                color: {Style.TEXT_PRIMARY};
            }}
            QDateTimeEdit:hover {{
                border: 1px solid {Style.ACCENT};
            }}
            QDateTimeEdit:focus {{
                border: 1px solid {Style.ACCENT};
            }}
        """

    @staticmethod
    def scrollbar():
        """스크롤바 스타일 - 가시성 향상"""
        return f"""
            QScrollBar:vertical {{
                border: none;
                background: #e8edf3;
                width: 14px;
                border-radius: 7px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {Style.ACCENT};
                min-height: 30px;
                border-radius: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Style.ACCENT_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """
