import sys
import requests
import os
import configparser
import base64
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QDateTimeEdit,
    QHeaderView, QStatusBar, QMessageBox, QSizePolicy, QCheckBox, QStyle,
    QTableView # Added for QStandardItemModel
)
from PyQt6.QtGui import QFont, QIntValidator, QPixmap, QIcon, QStandardItem, QStandardItemModel # Added QStandardItem, QStandardItemModel
from PyQt6.QtCore import QThread, pyqtSignal, QDateTime, Qt, QSortFilterProxyModel, QPoint, QModelIndex, QRect # Added QSortFilterProxyModel, QPoint, QModelIndex, QRect
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

from PyQt6.QtWidgets import QDialog, QMenu
from PyQt6.QtWebEngineWidgets import QWebEngineView

def create_standard_item(text, tooltip=None):
    """Create a QStandardItem with text and optional tooltip"""
    item = QStandardItem(str(text))
    if tooltip:
        # Format tooltip with line breaks for long text
        tooltip_text = str(tooltip)
        if len(tooltip_text) > 80:
            # Insert line breaks every 80 characters at word boundaries
            words = tooltip_text.split(' ')
            lines = []
            current_line = ''
            for word in words:
                if len(current_line + ' ' + word) <= 80:
                    current_line += (' ' + word) if current_line else word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            tooltip_text = '\n'.join(lines)
        item.setToolTip(tooltip_text)
    return item

def create_item(text, tooltip=None):
    """Alias for create_standard_item for backward compatibility"""
    return create_standard_item(text, tooltip)

class ImagePreviewPopup(QDialog):
    # Class variable to remember dialog size
    _saved_size = None
    
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Image Preview")
        
        self.original_pixmap = pixmap
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Image Label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        main_layout.addWidget(self.image_label)

        self.setLayout(main_layout)
        
        # Set initial size
        if ImagePreviewPopup._saved_size:
            self.resize(ImagePreviewPopup._saved_size)
        else:
            self.resize(600, 500)
        
        # Update image to fit current size
        self.update_image_size()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update image when dialog is resized
        self.update_image_size()
        # Save the new size
        ImagePreviewPopup._saved_size = self.size()
    
    def update_image_size(self):
        # Get available space for image (subtract margins)
        available_size = self.image_label.size()
        if available_size.width() > 0 and available_size.height() > 0:
            # Scale pixmap to fit available space while keeping aspect ratio
            scaled_pixmap = self.original_pixmap.scaled(
                available_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

class MapDialog(QDialog):
    def __init__(self, location_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Location Map")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Parse coordinates from location text (assuming format like "lat,lng")
        try:
            coords = location_text.split(',')
            if len(coords) == 2:
                lat = float(coords[1].strip())
                lng = float(coords[0].strip())
            else:
                lat, lng = 39.9042, 116.4074  # Default to Beijing
        except:
            lat, lng = 39.9042, 116.4074  # Default to Beijing
        
        # Create WebView
        web_view = QWebEngineView()

        # HTML content with Amap (高德地图)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Location Map</title>
            <script src="https://webapi.amap.com/maps?v=1.4.15&key=b4eb7a9939ad6c7f2831079165ef51e8"></script>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                html, body {{ width: 100%; height: 100%; overflow: hidden; }}
                #mapContainer {{ width: 100%; height: 100%; }}
            </style>
        </head>
        <body>
            <div id="mapContainer"></div>
            <script>
                var map = new AMap.Map('mapContainer', {{
                    zoom: 15,
                    center: [{lng}, {lat}],
                    resizeEnable: true
                }});
                
                var marker = new AMap.Marker({{
                    position: [{lng}, {lat}],
                    title: 'Location: {location_text}'
                }});
                
                map.add(marker);
                
                // Auto resize map when window resizes
                window.addEventListener('resize', function() {{
                    map.getSize();
                }});
            </script>
        </body>
        </html>
        """
        
        web_view.setHtml(html_content)
        layout.addWidget(web_view)
        
        self.setLayout(layout)

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

class LogFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = {} # {column_index: filter_text}

    def setFilterByColumn(self, column_index, filter_text):
        if filter_text:
            self._filters[column_index] = filter_text
        else:
            self._filters.pop(column_index, None)
        self.invalidateFilter() # Re-apply filters

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filters:
            return True # No filters applied

        for column_index, filter_text in self._filters.items():
            index = self.sourceModel().index(source_row, column_index, source_parent)
            if index.isValid():
                data = self.sourceModel().data(index)
                if str(data) != filter_text:  # Exact match instead of substring
                    return False # Mismatch in this column
        return True # All filters passed

# Removed FilterHeaderView class as it's no longer needed

class LogAnalyzerApp(QWidget):
    SETTINGS_FILE = ".kongminglog.ini"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kongming Log Analyzer")
        self.setGeometry(100, 100, 1200, 800) # Increased window size

        self.init_ui()
        self.query_worker = None
        self.image_preview_popup = None
        self.load_settings() # Call load_settings after init_ui

    def load_settings(self):
        config = configparser.ConfigParser()
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.SETTINGS_FILE)
        
        if os.path.exists(settings_path):
            config.read(settings_path)

            # Load Window Geometry
            if 'Window' in config:
                try:
                    x = config.getint('Window', 'x', fallback=100)
                    y = config.getint('Window', 'y', fallback=100)
                    width = config.getint('Window', 'width', fallback=1200)
                    height = config.getint('Window', 'height', fallback=800)
                    self.setGeometry(x, y, width, height)
                except ValueError:
                    pass # Use default if parsing fails

            # Load ELK Server Configuration
            if 'ELK_Config' in config:
                self.server_url_input.setText(config.get('ELK_Config', 'server_url', fallback="https://elk.xjsdtech.com"))
                self.username_input.setText(config.get('ELK_Config', 'username', fallback="ai"))
                self.password_input.setText(config.get('ELK_Config', 'password', fallback="ai@123456"))
                self.env_combo.setCurrentText(config.get('ELK_Config', 'environment', fallback="uat"))

            # Load Query Conditions
            if 'Query_Conditions' in config:
                # QDateTimeEdit
                start_time_str = config.get('Query_Conditions', 'start_time', fallback="")
                if start_time_str:
                    self.start_time_edit.setDateTime(QDateTime.fromString(start_time_str, "yyyy-MM-dd HH:mm:ss"))
                
                end_time_str = config.get('Query_Conditions', 'end_time', fallback="")
                if end_time_str:
                    self.end_time_edit.setDateTime(QDateTime.fromString(end_time_str, "yyyy-MM-dd HH:mm:ss"))

                # QCheckBox
                self.enable_start_time_checkbox.setChecked(config.getboolean('Query_Conditions', 'enable_start_time', fallback=True))
                self.enable_end_time_checkbox.setChecked(config.getboolean('Query_Conditions', 'enable_end_time', fallback=True))

                # QLineEdit
                self.phrase_input.setText(config.get('Query_Conditions', 'phrase', fallback=""))
                self.id_value_input.setText(config.get('Query_Conditions', 'id_value', fallback=""))
                self.query_size_input.setText(config.get('Query_Conditions', 'query_size', fallback="100"))

                # QComboBox
                self.glass_product_combo.setCurrentText(config.get('Query_Conditions', 'glass_product', fallback=""))
                self.id_type_combo.setCurrentText(config.get('Query_Conditions', 'id_type', fallback=""))

            # Load Table Header State
            if 'Table' in config:
                try:
                    header_state_str = config.get('Table', 'header_state', fallback="")
                    if header_state_str:
                        header_state_bytes = base64.b64decode(header_state_str)
                        self.table_widget.horizontalHeader().restoreState(header_state_bytes)
                except Exception:
                    pass # Ignore if header state cannot be restored

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
        self.enable_start_time_checkbox = QCheckBox()
        self.enable_start_time_checkbox.setChecked(True)
        combined_query_layout.addWidget(self.enable_start_time_checkbox)

        combined_query_layout.addWidget(QLabel("开始时间:"))
        self.start_time_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(-1))
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        combined_query_layout.addWidget(self.start_time_edit)

        self.enable_start_time_checkbox.toggled.connect(self.start_time_edit.setEnabled)

        # End Time
        self.enable_end_time_checkbox = QCheckBox()
        self.enable_end_time_checkbox.setChecked(True)
        combined_query_layout.addWidget(self.enable_end_time_checkbox)

        combined_query_layout.addWidget(QLabel("结束时间:"))
        self.end_time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        combined_query_layout.addWidget(self.end_time_edit)

        self.enable_end_time_checkbox.toggled.connect(self.end_time_edit.setEnabled)

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

        # Search and Filter Buttons
        button_layout = QHBoxLayout()
        self.search_button = QPushButton("Search Logs")
        self.search_button.clicked.connect(self.start_query)
        button_layout.addWidget(self.search_button)
        
        self.filter_button = QPushButton("Filter Results")
        self.filter_button.clicked.connect(self.show_filter_dialog)
        button_layout.addWidget(self.filter_button)
        
        self.clear_filter_button = QPushButton("Clear Filter")
        self.clear_filter_button.clicked.connect(self.clear_all_filters)
        button_layout.addWidget(self.clear_filter_button)
        
        query_group_layout.addLayout(button_layout)
        main_layout.addLayout(query_group_layout)

        # --- Results Section ---
        results_group_layout = QVBoxLayout()
        results_group_layout.addWidget(QLabel("<h3>Query Results</h3>"))

        self.data_model = QStandardItemModel()
        self.proxy_model = LogFilterProxyModel() # Use custom proxy model
        self.proxy_model.setSourceModel(self.data_model)
        
        self.table_widget = QTableView() # Change to QTableView
        self.table_widget.setModel(self.proxy_model) # Set proxy model to table
        self.table_widget.setEditTriggers(QTableView.EditTrigger.NoEditTriggers) # Disable editing
        self.table_widget.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems) # Allow item selection for copying
        self.table_widget.setWordWrap(False) # Disable word wrap to keep single line display

        self.setup_table_headers() # This will now set headers on data_model
        self.table_widget.doubleClicked.connect(self.handle_cell_double_clicked)
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
            "NLU Error", "NLU耗时", "LLM查询", "LLM意图", "LLM场景", "照片",
            "角色扮演", "深度思考", "深度搜索", "视觉辅助", "清上下文", "LLM回答",
            "LLM思考", "LLM搜索数据", "LLM状态", "LLM耗时", "deviceId",
            "glassDeviceId", "iotDeviceId", "accountId", "xjAccountId",
            "sessionId", "msgId",
        ]
        self.data_model.setColumnCount(len(headers))
        self.data_model.setHorizontalHeaderLabels(headers)
        # The QTableWidget will get its header from the proxy model, which gets it from the data model
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive) # This will be handled by the view
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
            "timestamp_begin": self.start_time_edit.dateTime().toUTC().toString("yyyy-MM-ddTHH:mm:ss.zzzZ") if self.enable_start_time_checkbox.isChecked() else None,
            "timestamp_end": self.end_time_edit.dateTime().toUTC().toString("yyyy-MM-ddTHH:mm:ss.zzzZ") if self.enable_end_time_checkbox.isChecked() else None,
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
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor) # Set busy cursor

        self.query_worker = QueryWorker(server_config, filter_config, query_size)
        self.query_worker.finished.connect(self.display_results)
        self.query_worker.error.connect(self.show_error)
        self.query_worker.progress.connect(self.status_bar.showMessage)
        self.query_worker.start()

    def display_results(self, rounds: List[DialogRound]):
        # Save current column widths before clearing data
        column_widths = []
        for i in range(self.data_model.columnCount()):
            column_widths.append(self.table_widget.horizontalHeader().sectionSize(i))
        
        # Clear existing data and reset column count
        self.data_model.clear()
        self.setup_table_headers()  # Reset headers
        self.data_model.setRowCount(len(rounds)) # Set row count on the data model
        print(f"Initial column count: {self.data_model.columnCount()}")  # Debug
        for row_idx, round in enumerate(rounds):
            # Populate table based on the headers defined in setup_table_headers
            # This mapping needs to be careful and match the order of headers
            # and the logic from kongming/excel.py
            col_idx = 0

            if round is None:
                continue

            

            # General
            timestamp_str = round.nlp_round.request_timestamp if round.nlp_round and round.nlp_round.request_timestamp else ""
            if timestamp_str:
                # Assuming timestamp_str is in ISO 8601 format (e.g., "2025-08-20T12:34:56.789Z" or with offset)
                # QDateTime.fromString can parse ISO 8601 directly
                dt = QDateTime.fromString(timestamp_str, Qt.DateFormat.ISODate)
                if dt.isValid():
                    # Convert to local time
                    local_dt = dt.toLocalTime()
                    display_timestamp = local_dt.toString("yyyy-MM-dd HH:mm:ss")
                else:
                    display_timestamp = timestamp_str # Fallback if parsing fails
            else:
                display_timestamp = ""
            self.data_model.setItem(row_idx, col_idx, create_item(display_timestamp))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(str(round.traceId) or ""))

            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(str(int(round.glassProduct)) if round.glassProduct else ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(str(round.location) if round.location else ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(str(round.originType) if round.originType is not None else ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(str(round.functionType) if round.functionType is not None else ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.local or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.timeZone or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.nluLanguage or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(str(round.sessionFirstFlag) if round.sessionFirstFlag is not None else ""))
            col_idx += 1

            # NLU Round
            if round.nlp_round:
                nlu_query_text = round.nlp_round.query if round.nlp_round.query != "CLEAN_CONTEXT_MAGIC_STRING" else "<清除上下文>"
                self.data_model.setItem(row_idx, col_idx, create_item(nlu_query_text, nlu_query_text))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.nlp_round.intent or "")))
                col_idx += 1
                nlu_utterance_text = str(round.nlp_round.utterance) if round.nlp_round.utterance else ""
                self.data_model.setItem(row_idx, col_idx, create_item(nlu_utterance_text, nlu_utterance_text))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.nlp_round.error) if round.nlp_round.error else ""))
                col_idx += 1
                nlu_latency = calculate_time_difference(round.nlp_round.request_timestamp, round.nlp_round.response_timestamp) if round.nlp_round.response_timestamp else ""
                self.data_model.setItem(row_idx, col_idx, create_item(str(nlu_latency)))
                col_idx += 1
            else:
                # Fill empty cells for NLU columns
                for _ in range(5):
                    self.data_model.setItem(row_idx, col_idx, create_item(""))
                    col_idx += 1

            # LLM Round
            if round.llm_round:
                llm_query_text = round.llm_round.query or ""
                self.data_model.setItem(row_idx, col_idx, create_item(llm_query_text, llm_query_text))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(round.llm_round.intent_name or ""))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.channel_type) if round.llm_round.channel_type is not None else ""))
                col_idx += 1
                files_text = "\n".join([file.ossUrl for file in round.llm_round.files]) if round.llm_round.files else ""
                if files_text:
                    item = create_standard_item("", files_text) # Display empty text, tooltip is URL
                    item.setIcon(QApplication.instance().style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.data_model.setItem(row_idx, col_idx, item)
                else:
                    item = create_standard_item("")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.data_model.setItem(row_idx, col_idx, item)
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.play_status) if round.llm_round.play_status is not None else ""))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.use_deepseek) if round.llm_round.use_deepseek is not None else ""))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.use_search) if round.llm_round.use_search is not None else ""))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.visual_aids_status) if round.llm_round.visual_aids_status is not None else ""))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.clean_context) if round.llm_round.clean_context is not None else ""))
                col_idx += 1
                llm_answer_text = round.llm_round.answer or ""
                self.data_model.setItem(row_idx, col_idx, create_item(llm_answer_text, llm_answer_text))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(round.llm_round.reason or ""))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.thoughts_data) if round.llm_round.thoughts_data else ""))
                col_idx += 1
                self.data_model.setItem(row_idx, col_idx, create_item(str(round.llm_round.base_status) if round.llm_round.base_status is not None else ""))
                col_idx += 1
                llm_latency = calculate_time_difference(round.llm_round.request_timestamp, round.llm_round.response_timestamp) if round.llm_round.response_timestamp else ""
                self.data_model.setItem(row_idx, col_idx, create_item(str(llm_latency)))
                col_idx += 1
            else:
                # Fill empty cells for LLM columns
                for _ in range(14):
                    self.data_model.setItem(row_idx, col_idx, create_item(""))
                    col_idx += 1

            # IDs
            self.data_model.setItem(row_idx, col_idx, create_item(round.deviceId or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.glassDeviceId or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.iotDeviceId or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.accountId or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.xjAccountId or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.sessionId or ""))
            col_idx += 1
            self.data_model.setItem(row_idx, col_idx, create_item(round.msgId or ""))

        # Ensure column count matches expected
        expected_columns = 36
        if self.data_model.columnCount() > expected_columns:
            print(f"Warning: Model has {self.data_model.columnCount()} columns, expected {expected_columns}")
            self.data_model.setColumnCount(expected_columns)
            self.setup_table_headers()  # Reset headers again

        # Restore saved column widths
        for i, width in enumerate(column_widths):
            if i < self.data_model.columnCount():
                self.table_widget.horizontalHeader().resizeSection(i, width)
        
        self.search_button.setEnabled(True) # Re-enable button
        QApplication.restoreOverrideCursor() # Restore normal cursor

    def handle_cell_double_clicked(self, index: QModelIndex):
        # Get the item from the proxy model
        proxy_index = index
        # Map the proxy index to the source model index to get the actual QStandardItem
        source_index = self.proxy_model.mapToSource(proxy_index)
        item = self.data_model.itemFromIndex(source_index)

        # Get header text from the proxy model's header
        header_text = self.proxy_model.headerData(proxy_index.column(), Qt.Orientation.Horizontal)
        if header_text == "照片":
            if item and item.toolTip():
                self.image_fetcher = ImageFetcher(item.toolTip())
                self.image_fetcher.finished.connect(self.show_image_preview)
                self.image_fetcher.error.connect(self.show_image_fetch_error)
                self.image_fetcher.start()
        elif header_text == "位置":
            if item and item.text().strip():
                self.show_map_dialog(item.text())
    
    def show_map_dialog(self, location_text):
        map_dialog = MapDialog(location_text, self)
        map_dialog.exec()

    def show_filter_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QTableWidget, QTableWidgetItem
        from collections import Counter
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Filter Results")
        dialog.resize(700, 500)
        
        main_layout = QVBoxLayout()
        content_layout = QHBoxLayout()
        
        # Left side - Column selection
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Columns:"))
        column_list = QListWidget()
        column_list.setFixedWidth(200)
        
        headers = []
        for i in range(self.data_model.columnCount()):
            header_item = self.data_model.horizontalHeaderItem(i)
            if header_item:
                headers.append(header_item.text())
                column_list.addItem(QListWidgetItem(header_item.text()))
        
        left_layout.addWidget(column_list)
        content_layout.addLayout(left_layout)
        
        # Right side - Value table with counts
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Values:"))
        value_table = QTableWidget()
        value_table.setColumnCount(2)
        value_table.setHorizontalHeaderLabels(["Value", "Count"])
        value_table.setFont(QFont("Courier New", 9))  # Set monospace font
        value_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Set column resize modes
        header = value_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Value column stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Count column minimal
        
        right_layout.addWidget(value_table)
        content_layout.addLayout(right_layout)
        
        main_layout.addLayout(content_layout)
        
        # Update values when column selection changes
        def update_values():
            value_table.setRowCount(0)
            current_item = column_list.currentItem()
            if current_item:
                column_index = column_list.row(current_item)
                values = []
                for row in range(self.data_model.rowCount()):
                    item = self.data_model.item(row, column_index)
                    if item and item.text().strip():
                        values.append(item.text())
                
                # Count occurrences
                value_counts = Counter(values)
                
                # Populate table
                value_table.setRowCount(len(value_counts))
                for i, (value, count) in enumerate(sorted(value_counts.items())):
                    value_table.setItem(i, 0, QTableWidgetItem(value))
                    count_item = QTableWidgetItem(str(count))
                    count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    value_table.setItem(i, 1, count_item)
                
                # Select current filter value if exists
                if column_index in self.proxy_model._filters:
                    current_filter = self.proxy_model._filters[column_index]
                    for i in range(value_table.rowCount()):
                        if value_table.item(i, 0).text() == current_filter:
                            value_table.selectRow(i)
                            break
        
        column_list.currentItemChanged.connect(lambda: update_values())
        
        # Set initial selection if there's an active filter
        if self.proxy_model._filters:
            first_filter_column = next(iter(self.proxy_model._filters.keys()))
            column_list.setCurrentRow(first_filter_column)
        else:
            column_list.setCurrentRow(0)
        update_values()
        
        # Buttons
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply Filter")
        cancel_button = QPushButton("Cancel")
        
        def apply_filter():
            current_column = column_list.currentItem()
            current_row = value_table.currentRow()
            if current_column and current_row >= 0:
                column_index = column_list.row(current_column)
                value_item = value_table.item(current_row, 0)
                if value_item:
                    self.apply_filter(column_index, value_item.text())
            dialog.accept()
        
        apply_button.clicked.connect(apply_filter)
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)
        
        dialog.setLayout(main_layout)
        dialog.exec()
    
    def clear_all_filters(self):
        self.proxy_model._filters.clear()
        self.proxy_model.invalidateFilter()

    def apply_filter(self, column_index, filter_text):
        # Clear all existing filters before applying new one
        self.proxy_model._filters.clear()
        self.proxy_model.setFilterByColumn(column_index, filter_text)

    def show_image_preview(self, pixmap):
        if not pixmap.isNull():
            self.image_preview_popup = ImagePreviewPopup(pixmap, self)
            self.image_preview_popup.exec() # Use exec() for modal dialog (PyQt6)

    def show_image_fetch_error(self, message):
        QMessageBox.critical(self, "Image Fetch Error", message)

    def show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
        self.status_bar.showMessage("Error: " + message)
        self.search_button.setEnabled(True) # Re-enable button
        QApplication.restoreOverrideCursor() # Restore normal cursor

    def save_settings(self):
        config = configparser.ConfigParser()

        # Save Window Geometry
        geom = self.geometry()
        config['Window'] = {
            'x': str(geom.x()),
            'y': str(geom.y()),
            'width': str(geom.width()),
            'height': str(geom.height())
        }

        # Save ELK Server Configuration
        config['ELK_Config'] = {
            'server_url': self.server_url_input.text(),
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'environment': self.env_combo.currentText()
        }

        # Save Query Conditions
        config['Query_Conditions'] = {
            'start_time': self.start_time_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            'enable_start_time': str(self.enable_start_time_checkbox.isChecked()),
            'end_time': self.end_time_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            'enable_end_time': str(self.enable_end_time_checkbox.isChecked()),
            'phrase': self.phrase_input.text(),
            'glass_product': self.glass_product_combo.currentText(),
            'id_type': self.id_type_combo.currentText(),
            'id_value': self.id_value_input.text(),
            'query_size': self.query_size_input.text()
        }

        # Save Table Header State
        header_state = self.table_widget.horizontalHeader().saveState()
        config['Table'] = {
            'header_state': header_state.toBase64().data().decode('utf-8')
        }

        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.SETTINGS_FILE)
        with open(settings_path, 'w') as configfile:
            config.write(configfile)

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LogAnalyzerApp()
    window.show()
    sys.exit(app.exec())
