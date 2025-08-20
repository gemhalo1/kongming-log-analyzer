import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QDateTimeEdit,
    QHeaderView, QStatusBar, QMessageBox, QSizePolicy, QCheckBox
)
from PyQt6.QtGui import QFont, QIntValidator, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, QDateTime, Qt
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Import existing kongming modules
# Ensure these imports are correct based on the actual file structure and class names
try:
    from kongming.elk import KongmingELKServer, KongmingEnvironmentType
    from kongming.model import DialogLogFilter, DialogRound, ID_TYPE, NLPRound, LLMRound, Location, NLPIntent, NLPUtterance, NLPError, OssFile
    from kongming.utils import calculate_time_difference, convert_timestamp
except ImportError as e:
    print(f"Error importing kongming modules: {e}")
    print("Please ensure your PYTHONPATH is correctly set or that you are running from the project root.")
    sys.exit(1)

class ImageFetcher(QThread):
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=10) # Add timeout
            response.raise_for_status()
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            if pixmap.isNull():
                self.error.emit(f"Failed to load image data from {self.url}")
            else:
                self.finished.emit(pixmap)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Network error fetching image from {self.url}: {e}")
        except Exception as e:
            self.error.emit(f"An unexpected error occurred fetching image from {self.url}: {e}")

class ImagePreviewPopup(QWidget):
    def __init__(self, pixmap):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint) # Make it a dialog
        self.setWindowModality(Qt.WindowModality.ApplicationModal) # Make it modal
        
        main_layout = QVBoxLayout()
        
        # Image Label
        label = QLabel()
        label.setPixmap(pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)) # Scale image
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(label)

        # Close Button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        main_layout.addWidget(close_button)

        self.setLayout(main_layout)

class QueryWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, server_config: Dict[str, str], filter_config: Dict[str, Any], query_size: int):
        super().__init__()
        self.server_config = server_config
        self.filter_config = filter_config
        self.query_size = query_size

    def run(self):
        try:
            self.progress.emit("Connecting to ELK server...")
            elk_server = KongmingELKServer(
                server=self.server_config["server"],
                username=self.server_config["username"],
                password=self.server_config["password"],
                env=self.server_config["env"]
            )

            self.progress.emit("Building query filter...")
            dialog_filter = DialogLogFilter(
                timestamp_begin=self.filter_config.get("timestamp_begin"),
                timestamp_end=self.filter_config.get("timestamp_end"),
                glass_product=self.filter_config.get("glass_product"),
                id_type=self.filter_config.get("id_type"),
                id_value=self.filter_config.get("id_value"),
                phrase=self.filter_config.get("phrase")
            )

            self.progress.emit("Executing query... This may take a while.")
            # Assuming query_dialogs returns (records, rounds)
            records, rounds = elk_server.query_dialogs(dialog_filter, size=self.query_size, pagesize=1000) # Use provided size
            self.finished.emit(rounds)
            self.progress.emit(f"Query finished. Found {len(rounds)} dialog rounds.")
        except Exception as e:
            self.error.emit(f"Query failed: {str(e)}")
            self.progress.emit("Query failed.")

class LogAnalyzerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kongming Log Analyzer")
        self.setGeometry(100, 100, 1200, 800) # Increased window size

        self.init_ui()
        self.query_worker = None
        self.image_preview_popup = None

    def init_ui(self):
        main_layout = QVBoxLayout()

        # --- Configuration Section ---
        config_group_layout = QVBoxLayout()
        config_group_layout.addWidget(QLabel("<h3>ELK Server Configuration</h3>"))

        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Server URL:"))
        self.server_url_input = QLineEdit("https://elk.xjsdtech.com")
        form_layout.addWidget(self.server_url_input)

        form_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit("ai")
        form_layout.addWidget(self.username_input)

        form_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit("ai@123456")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.password_input)

        form_layout.addWidget(QLabel("Environment:"))
        self.env_combo = QComboBox()
        self.env_combo.addItems(["uat", "prod", "fat"])
        self.env_combo.setCurrentText("uat")
        form_layout.addWidget(self.env_combo)
        config_group_layout.addLayout(form_layout)
        main_layout.addLayout(config_group_layout)

        # --- Query Conditions Section ---
        query_group_layout = QVBoxLayout()
        query_group_layout.addWidget(QLabel("<h3>Query Conditions</h3>"))

        # Combined Time, Phrase and Glass Product
        combined_query_layout = QHBoxLayout()

        # Start Time
        combined_query_layout.addWidget(QLabel("Start Time:"))
        self.start_time_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(-1))
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        combined_query_layout.addWidget(self.start_time_edit)
        self.enable_start_time_checkbox = QCheckBox()
        self.enable_start_time_checkbox.setChecked(True)
        self.enable_start_time_checkbox.toggled.connect(self.start_time_edit.setEnabled)
        combined_query_layout.addWidget(self.enable_start_time_checkbox)

        # End Time
        combined_query_layout.addWidget(QLabel("End Time:"))
        self.end_time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        combined_query_layout.addWidget(self.end_time_edit)
        self.enable_end_time_checkbox = QCheckBox()
        self.enable_end_time_checkbox.setChecked(True)
        self.enable_end_time_checkbox.toggled.connect(self.end_time_edit.setEnabled)
        combined_query_layout.addWidget(self.enable_end_time_checkbox)

        # Phrase
        combined_query_layout.addWidget(QLabel("Phrase:"))
        self.phrase_input = QLineEdit()
        combined_query_layout.addWidget(self.phrase_input)

        # Glass Product
        combined_query_layout.addWidget(QLabel("Glass Product:"))
        self.glass_product_combo = QComboBox()
        self.glass_product_combo.addItems(["", "1001", "1002", "1003", "1004", "1005"])
        combined_query_layout.addWidget(self.glass_product_combo)

        query_group_layout.addLayout(combined_query_layout)

        # ID Type and Value
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("ID Type:"))
        self.id_type_combo = QComboBox()
        self.id_type_combo.addItems(["", "deviceId", "glassDeviceId", "iotDeviceId", "xjAccountId", "accountId"])
        id_layout.addWidget(self.id_type_combo)

        id_layout.addWidget(QLabel("ID Value:"))
        self.id_value_input = QLineEdit()
        id_layout.addWidget(self.id_value_input)

        id_layout.addWidget(QLabel("Query Size:"))
        self.query_size_input = QLineEdit("100") # Default size
        self.query_size_input.setValidator(QIntValidator()) # Only allow integers
        id_layout.addWidget(self.query_size_input)
        query_group_layout.addLayout(id_layout)

        # Search Button
        self.search_button = QPushButton("Search Logs")
        self.search_button.clicked.connect(self.start_query)
        query_group_layout.addWidget(self.search_button)
        main_layout.addLayout(query_group_layout)

        # --- Results Section ---
        results_group_layout = QVBoxLayout()
        results_group_layout.addWidget(QLabel("<h3>Query Results</h3>"))

        self.table_widget = QTableWidget()
        self.setup_table_headers()
        self.table_widget.cellDoubleClicked.connect(self.handle_cell_double_clicked)
        results_group_layout.addWidget(self.table_widget)
        main_layout.addLayout(results_group_layout)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

    def setup_table_headers(self):
        # Headers based on kongming/excel.py's titles
        headers = [
            "时间戳", "trace_id", "眼镜类型", "位置", "originType", "functionType",
            "locale", "时区", "语种", "首轮", "NLU查询", "NLU意图", "NLU回答",
            "NLU Error", "NLU耗时", "LLM查询", "LLM意图", "LLM场景", "图像文件",
            "角色扮演", "深度思考", "深度搜索", "视觉辅助", "清上下文", "LLM回答",
            "LLM思考", "LLM搜索数据", "LLM状态", "LLM耗时", "deviceId",
            "glassDeviceId", "iotDeviceId", "accountId", "xjAccountId",
            "sessionId", "msgId",
        ]
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_widget.verticalHeader().setVisible(True) # Show row numbers
        self.table_widget.setFont(QFont("Courier New", 8)) # Set smaller monospace font

    def start_query(self):
        if self.query_worker and self.query_worker.isRunning():
            QMessageBox.warning(self, "Query in Progress", "A query is already running. Please wait or cancel the current query.")
            return

        server_config = {
            "server": self.server_url_input.text(),
            "username": self.username_input.text(),
            "password": self.password_input.text(),
            "env": self.env_combo.currentText()
        }

        filter_config = {
            "timestamp_begin": self.start_time_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss.zzzZ") if self.enable_start_time_checkbox.isChecked() else None,
            "timestamp_end": self.end_time_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss.zzzZ") if self.enable_end_time_checkbox.isChecked() else None,
            "glass_product": self.glass_product_combo.currentText() if self.glass_product_combo.currentText() else None,
            "id_type": self.id_type_combo.currentText() if self.id_type_combo.currentText() else None,
            "id_value": self.id_value_input.text() if self.id_value_input.text() else None,
            "phrase": self.phrase_input.text() if self.phrase_input.text() else None
        }

        try:
            query_size = int(self.query_size_input.text())
            if query_size <= 0:
                raise ValueError("Query size must be a positive integer.")
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Input", f"Invalid Query Size: {e}")
            return

        self.status_bar.showMessage("Starting query...")
        self.search_button.setEnabled(False) # Disable button during query

        self.query_worker = QueryWorker(server_config, filter_config, query_size)
        self.query_worker.finished.connect(self.display_results)
        self.query_worker.error.connect(self.show_error)
        self.query_worker.progress.connect(self.status_bar.showMessage)
        self.query_worker.start()

    def display_results(self, rounds: List[DialogRound]):
        self.table_widget.setRowCount(len(rounds))
        for row_idx, round in enumerate(rounds):
            # Populate table based on the headers defined in setup_table_headers
            # This mapping needs to be careful and match the order of headers
            # and the logic from kongming/excel.py
            col_idx = 0

            if round is None:
                continue

            # Helper to create non-editable item
            def create_item(text, tooltip_text=""):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(tooltip_text)
                return item

            # General
            self.table_widget.setItem(row_idx, col_idx, create_item(round.nlp_round.request_timestamp if round.nlp_round and round.nlp_round.request_timestamp else ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.traceId or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(str(int(round.glassProduct)) if round.glassProduct else ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(str(round.location) if round.location else ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(str(round.originType) if round.originType is not None else ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(str(round.functionType) if round.functionType is not None else ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.local or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.timeZone or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.nluLanguage or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(str(round.sessionFirstFlag) if round.sessionFirstFlag is not None else ""))
            col_idx += 1

            # NLU Round
            if round.nlp_round:
                nlu_query_text = round.nlp_round.query if round.nlp_round.query != "CLEAN_CONTEXT_MAGIC_STRING" else "<清除上下文>"
                self.table_widget.setItem(row_idx, col_idx, create_item(nlu_query_text, nlu_query_text))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.nlp_round.intent or "")))
                col_idx += 1
                nlu_utterance_text = str(round.nlp_round.utterance) if round.nlp_round.utterance else ""
                self.table_widget.setItem(row_idx, col_idx, create_item(nlu_utterance_text, nlu_utterance_text))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.nlp_round.error) if round.nlp_round.error else ""))
                col_idx += 1
                nlu_latency = calculate_time_difference(round.nlp_round.request_timestamp, round.nlp_round.response_timestamp) if round.nlp_round.response_timestamp else ""
                self.table_widget.setItem(row_idx, col_idx, create_item(str(nlu_latency)))
                col_idx += 1
            else:
                col_idx += 5 # Skip NLU columns if no nlp_round

            # LLM Round
            if round.llm_round:
                llm_query_text = round.llm_round.query or ""
                self.table_widget.setItem(row_idx, col_idx, create_item(llm_query_text, llm_query_text))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(round.llm_round.intent_name or ""))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.channel_type) if round.llm_round.channel_type is not None else ""))
                col_idx += 1
                files_text = "\n".join([file.ossUrl for file in round.llm_round.files]) if round.llm_round.files else ""
                self.table_widget.setItem(row_idx, col_idx, create_item(files_text, files_text))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.play_status) if round.llm_round.play_status is not None else ""))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.use_deepseek) if round.llm_round.use_deepseek is not None else ""))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.use_search) if round.llm_round.use_search is not None else ""))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.visual_aids_status) if round.llm_round.visual_aids_status is not None else ""))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.clean_context) if round.llm_round.clean_context is not None else ""))
                col_idx += 1
                llm_answer_text = round.llm_round.answer or ""
                self.table_widget.setItem(row_idx, col_idx, create_item(llm_answer_text, llm_answer_text))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(round.llm_round.reason or ""))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.thoughts_data) if round.llm_round.thoughts_data else ""))
                col_idx += 1
                self.table_widget.setItem(row_idx, col_idx, create_item(str(round.llm_round.base_status) if round.llm_round.base_status is not None else ""))
                col_idx += 1
                llm_latency = calculate_time_difference(round.llm_round.request_timestamp, round.llm_round.response_timestamp) if round.llm_round.response_timestamp else ""
                self.table_widget.setItem(row_idx, col_idx, create_item(str(llm_latency)))
                col_idx += 1
            else:
                col_idx += 15 # Skip LLM columns if no llm_round

            # IDs
            self.table_widget.setItem(row_idx, col_idx, create_item(round.deviceId or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.glassDeviceId or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.iotDeviceId or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.accountId or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.xjAccountId or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.sessionId or ""))
            col_idx += 1
            self.table_widget.setItem(row_idx, col_idx, create_item(round.msgId or ""))
            col_idx += 1

        self.table_widget.resizeColumnsToContents()
        # Set fixed width for specific columns after resizeColumnsToContents
        fixed_width_columns = {
            "NLU查询": 250,
            "NLU回答": 250,
            "LLM查询": 250,
            "LLM回答": 250,
            "图像文件": 250,
            "LLM思考": 250,
            "LLM搜索数据": 250,
        }
        headers = [self.table_widget.horizontalHeaderItem(i).text() for i in range(self.table_widget.columnCount())]
        for col_name, width in fixed_width_columns.items():
            try:
                col_idx = headers.index(col_name)
                self.table_widget.setColumnWidth(col_idx, width)
            except ValueError:
                pass # Column not found, ignore

        self.search_button.setEnabled(True) # Re-enable button

    def handle_cell_double_clicked(self, row, column):
        if self.table_widget.horizontalHeaderItem(column).text() == "图像文件":
            item = self.table_widget.item(row, column)
            if item and item.toolTip():
                self.image_fetcher = ImageFetcher(item.toolTip())
                self.image_fetcher.finished.connect(self.show_image_preview)
                self.image_fetcher.error.connect(self.show_image_fetch_error)
                self.image_fetcher.start()

    def show_image_preview(self, pixmap):
        if not pixmap.isNull():
            self.image_preview_popup = ImagePreviewPopup(pixmap)
            self.image_preview_popup.exec() # Use exec() for modal dialog

    def show_image_fetch_error(self, message):
        QMessageBox.critical(self, "Image Fetch Error", message)

    def show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
        self.status_bar.showMessage("Error: " + message)
        self.search_button.setEnabled(True) # Re-enable button

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LogAnalyzerApp()
    window.show()
    sys.exit(app.exec())
