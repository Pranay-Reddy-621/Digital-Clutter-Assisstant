import subprocess
import sys
import json
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QCheckBox, 
                             QStackedWidget, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTextEdit, QMessageBox, QFrame,
                             QScrollArea, QDialog, QFormLayout, QLineEdit,
                             QComboBox, QInputDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QFileSystemWatcher, QTimer, QPropertyAnimation, QEasingCurve
from file_sorter import FileSorter
from rule_creation import create_rule_from_natural_language
import atexit
from file_crypto import encrypt_file, decrypt_file
from compress_extract import compress_file, extract_file
from monitoring import load_processed_files

class RuleEditorDialog(QDialog):
    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self.setWindowTitle("Digital Declutter Assistant")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.condition_edit = QLineEdit()
        if rule:
            self.condition_edit.setText(rule.get("condition", ""))
        form.addRow("Condition:", self.condition_edit)
        
        self.action_type = QComboBox()
        self.action_type.addItems(["move", "copy", "delete"])
        if rule and "action" in rule:
            self.action_type.setCurrentText(rule["action"].get("type", "move"))
        form.addRow("Action Type:", self.action_type)
        
        self.target_path = QLineEdit()
        if rule and "action" in rule and "target_path" in rule["action"]:
            self.target_path.setText(rule["action"]["target_path"])
        form.addRow("Target Path:", self.target_path)
        
        self.time_value = QLineEdit()
        if rule and "action" in rule and "time" in rule["action"]:
            self.time_value.setText(rule["action"]["time"])
        form.addRow("Time (for delete):", self.time_value)
        
        layout.addLayout(form)
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color: #8a2be2; color: white; padding: 8px;")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #d3d3d3; padding: 8px;")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
    def get_rule_data(self):
        rule = {
            "condition": self.condition_edit.text(),
            "action": {
                "type": self.action_type.currentText()
            }
        }
        
        if self.action_type.currentText() in ["move", "copy"]:
            rule["action"]["target_path"] = self.target_path.text()
        
        if self.action_type.currentText() == "delete" and self.time_value.text():
            rule["action"]["time"] = self.time_value.text()
            
        return rule

class RuleCardWidget(QFrame):
    def __init__(self, rule_num, rule_text, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px;")
        
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        
        rule_label = QLabel(f"Rule {rule_num}")
        rule_label.setStyleSheet("background-color: #8a2be2; color: white; border-radius: 10px; padding: 5px;")
        header.addWidget(rule_label)
        
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("background-color: white; border: none;")
        header.addWidget(edit_btn)
        
        header.addStretch()
        layout.addLayout(header)
        
        text = QLabel(rule_text)
        text.setWordWrap(True)
        layout.addWidget(text)

class DigitalDeclutterAssistant(QMainWindow):
    def __init__(self):
        super().__init__()

        self.monitoring_process = None

        self.setWindowTitle("Digital Declutter Assistant")
        self.setMinimumSize(1000, 700)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QWidget()
        sidebar.setStyleSheet("background-color: #4b0082;")
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        
        self.rules_btn = QPushButton("Rules")
        self.sort_btn = QPushButton("Sort")
        self.delete_btn = QPushButton("Delete")
        self.crypt_btn = QPushButton("Crypt")
        self.zip_btn = QPushButton("Zip")

        # Style sidebar buttons
        button_style = """
            QPushButton {
                color: white;
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 20px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6a0dad;
            }
        """
        self.rules_btn.setStyleSheet(button_style)
        self.sort_btn.setStyleSheet(button_style)
        self.delete_btn.setStyleSheet(button_style)
        self.crypt_btn.setStyleSheet(button_style)
        self.zip_btn.setStyleSheet(button_style)


        sidebar_layout.addWidget(self.rules_btn)
        sidebar_layout.addWidget(self.sort_btn)
        sidebar_layout.addWidget(self.delete_btn)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.crypt_btn)
        sidebar_layout.addWidget(self.zip_btn)


        # Content area
        content_area = QWidget()
        content_area.setStyleSheet("background-color: #4b0082;")
        content_layout = QVBoxLayout(content_area)
        
        # Stacked widget for different views
        self.stacked_widget = QStackedWidget()
        
        # Create views
        self.rules_view = self.create_rules_view()
        self.sort_view = self.create_sort_view()
        self.delete_view = self.create_delete_view()
        self.crypt_view = self.create_crypt_view()
        self.zip_view = self.create_zip_view()

        self.stacked_widget.addWidget(self.rules_view)
        self.stacked_widget.addWidget(self.sort_view)
        self.stacked_widget.addWidget(self.delete_view)
        self.stacked_widget.addWidget(self.crypt_view)
        self.stacked_widget.addWidget(self.zip_view)


        content_layout.addWidget(self.stacked_widget)
        
        # Connect sidebar buttons
        self.rules_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.sort_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.delete_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.crypt_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        self.zip_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(4))


        # Add widgets to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area)
        
        # SETUP Watchers
        self.setCentralWidget(main_widget)
        self.watcher = QFileSystemWatcher()
        self.watcher.addPaths([
            "pending_actions.json", 
            "files_to_be_deleted.txt",
            "encrypt_actions.json",
            "decrypt_actions.json",
            "compress_actions.json",
            "extract_actions.json"
        ])

        self.watcher.fileChanged.connect(self.handle_file_change)
        
        # Debounce timer
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.reload_views)
        self.changed_files = set()
        
        # Load rules
        self.load_rules()
        self.load_files_to_sort()
        self.load_files_to_delete()

        
    def handle_file_change(self, path):
        """Handle file change events with debouncing"""
        self.changed_files.add(path)
        self.debounce_timer.start(500)  # 500ms delay

    def reload_views(self):
        """Update relevant views after file changes"""
        for path in self.changed_files:
            if "pending_actions.json" in path:
                self.load_files_to_sort()
            elif "files_to_be_deleted.txt" in path:
                self.load_files_to_delete()
            elif "encrypt_actions.json" in path or "decrypt_actions.json" in path:
                self.load_crypto_actions()
            elif "compress_actions.json" in path or "extract_actions.json" in path:
                self.load_zip_actions()
        self.changed_files.clear()



    def delete_selected_actions(self):
        """Remove selected pending actions from the list"""
        try:
            with open('pending_actions.json', 'r') as f:
                pending = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        # Get indices of checked rows
        rows_to_delete = []
        for row in range(self.sort_table.rowCount()):
            if self.sort_table.cellWidget(row, 0).isChecked():
                rows_to_delete.append(row)

        # Remove in reverse order to preserve indices
        new_pending = [
            action for idx, action in enumerate(pending)
            if idx not in rows_to_delete
        ]

        # Save updated list
        with open('pending_actions.json', 'w') as f:
            json.dump(new_pending, f, indent=2)
        
        # Refresh view
        self.load_files_to_sort()
    def toggle_json_rules(self):
        """Animate show/hide of the technical rules JSON panel."""
        if self.json_toggle_btn.isChecked():
            self.json_toggle_btn.setText("▲ Hide technical rules")
            self.json_anim.setStartValue(self.json_frame.maximumHeight())
            self.json_anim.setEndValue(self.json_expanded_height)
        else:
            self.json_toggle_btn.setText("▼ Show technical rules")
            self.json_anim.setStartValue(self.json_frame.maximumHeight())
            self.json_anim.setEndValue(self.json_collapsed_height)
        self.json_anim.start()


    def create_rules_view(self):
        """Create the main page"""
        view = QWidget()
        layout = QVBoxLayout(view)

        title = QLabel("Rules")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #4b0082; border: none;")

        rules_container = QWidget()
        self.rules_layout = QHBoxLayout(rules_container)

        # --- Animated Collapsible JSON rules section ---
        self.json_toggle_btn = QPushButton("▼ Show technical rules")
        self.json_toggle_btn.setCheckable(True)
        self.json_toggle_btn.setChecked(False)
        self.json_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #8a2be2; 
                color: white; 
                border-radius: 8px; 
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #6a0dad;
            }
        """)
        self.json_toggle_btn.clicked.connect(self.toggle_json_rules)

        self.json_frame = QFrame()
        self.json_frame.setStyleSheet("background-color: white; border-radius: 10px;")
        self.json_layout = QVBoxLayout(self.json_frame)
        self.rules_json = QTextEdit()
        self.rules_json.setReadOnly(True)
        self.rules_json.setStyleSheet("font-family: monospace;")
        self.json_layout.addWidget(self.rules_json)
        self.json_frame.setMaximumHeight(0)  # Start hidden

        # Animation setup
        self.json_anim = QPropertyAnimation(self.json_frame, b"maximumHeight")
        self.json_anim.setDuration(350)
        self.json_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.json_collapsed_height = 0
        self.json_expanded_height = 800  # Adjust as needed

        # Left: vertical layout for toggle and JSON
        left_col = QVBoxLayout()
        left_col.addWidget(self.json_toggle_btn)
        left_col.addWidget(self.json_frame)
        left_col.addStretch()
        self.rules_layout.addLayout(left_col, 1)

        # --- Rule cards (center/right) ---
        cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(cards_widget)
        self.cards_layout.setAlignment(Qt.AlignTop)
        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setWidget(cards_widget)
        cards_scroll.setStyleSheet("background-color: #4b0082; border: none;")
        self.rules_layout.addWidget(cards_scroll, 2)

        scroll_area.setWidget(rules_container)
        layout.addWidget(scroll_area, 1)

        # Buttons
        buttons_layout = QHBoxLayout()
        add_rule_btn = QPushButton("Add new rules")
        add_rule_btn.setStyleSheet("background-color: #8a2be2; color: white; padding: 10px; border-radius: 5px;")
        add_rule_btn.clicked.connect(self.add_rule)
        delete_rule_btn = QPushButton("Delete Rule")
        delete_rule_btn.setStyleSheet("background-color: #8a2be2; color: white; padding: 10px; border-radius: 5px;")
        delete_rule_btn.clicked.connect(self.delete_rule)
        buttons_layout.addWidget(add_rule_btn)
        buttons_layout.addWidget(delete_rule_btn)
        layout.addLayout(buttons_layout)

        return view

    
    def create_sort_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        
        # Headers
        headers_layout = QHBoxLayout()
        
        old_header = QLabel("Old")
        old_header.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        old_header.setAlignment(Qt.AlignCenter)
        
        new_header = QLabel("New")
        new_header.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        new_header.setAlignment(Qt.AlignCenter)
        
        headers_layout.addSpacing(40)  # For checkbox column
        headers_layout.addSpacing(40)  # For icon column
        headers_layout.addSpacing(120) # For filename column
        headers_layout.addWidget(old_header, 1)
        headers_layout.addWidget(new_header, 1)
        
        layout.addLayout(headers_layout)
        
        # File list
        self.sort_table = QTableWidget()
        self.sort_table.setColumnCount(5)
        self.sort_table.setHorizontalHeaderLabels(["", "", "File", "Old Path", "New Path"])
        self.sort_table.horizontalHeader().setVisible(False)
        self.sort_table.verticalHeader().setVisible(False)
        self.sort_table.setShowGrid(False)
        self.sort_table.setStyleSheet("background-color: #4b0082; color: white; border: none;")
        
        # Set column widths
        self.sort_table.setColumnWidth(0, 40)  # Checkbox
        self.sort_table.setColumnWidth(1, 40)  # Icon
        self.sort_table.setColumnWidth(2, 120) # Filename
        self.sort_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.sort_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        
        layout.addWidget(self.sort_table, 1)
        
        # Accept button
        accept_layout = QHBoxLayout()
        accept_layout.addStretch()
        
        accept_btn = QPushButton("Accept")
        accept_btn.setStyleSheet("background-color: white; color: #4b0082; padding: 10px 20px; border-radius: 15px; font-weight: bold;")
        accept_btn.clicked.connect(self.accept_sort)
        
        accept_layout.addWidget(accept_btn)
        layout.addLayout(accept_layout)

        # Update accept button layout
        accept_layout = QHBoxLayout()
        
        # Add delete button
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #ff4444; color: white; padding: 10px 20px; border-radius: 15px; font-weight: bold;")
        delete_btn.clicked.connect(self.delete_selected_actions)
        
        accept_layout.addWidget(delete_btn)
        accept_layout.addStretch()
        accept_layout.addWidget(accept_btn)
        layout.addLayout(accept_layout)
        
        
        return view
    
    def create_delete_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        
        # Time Left header
        time_left = QLabel("Time Left")
        time_left.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        time_left.setAlignment(Qt.AlignCenter)
        layout.addWidget(time_left)
        
        # File list
        self.delete_table = QTableWidget()
        self.delete_table.setColumnCount(4)
        self.delete_table.setHorizontalHeaderLabels(["", "", "File", "Time Left"])
        self.delete_table.horizontalHeader().setVisible(False)
        self.delete_table.verticalHeader().setVisible(False)
        self.delete_table.setShowGrid(False)
        self.delete_table.setStyleSheet("background-color: #4b0082; color: white; border: none;")
        
        # Set column widths
        self.delete_table.setColumnWidth(0, 40)  # Checkbox
        self.delete_table.setColumnWidth(1, 40)  # Icon
        self.delete_table.setColumnWidth(2, 150) # Filename
        self.delete_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        layout.addWidget(self.delete_table, 1)
        
        return view
    
    def create_crypt_view(self):
        """Creating the crypt view"""
        view = QWidget()
        layout = QVBoxLayout(view)
        
        # Header
        title = QLabel("Crypt Operations")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # File table
        self.crypt_table = QTableWidget()
        self.crypt_table.setColumnCount(3)
        self.crypt_table.setHorizontalHeaderLabels(["", "File Name", "Action"])
        self.crypt_table.horizontalHeader().setVisible(False)
        self.crypt_table.verticalHeader().setVisible(False)
        self.crypt_table.setShowGrid(False)
        self.crypt_table.setStyleSheet("background-color: #4b0082; color: white; border: none;")
        
        # Column sizing
        self.crypt_table.setColumnWidth(0, 40)  # Checkbox
        self.crypt_table.setColumnWidth(1, 300) # Filename
        self.crypt_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        layout.addWidget(self.crypt_table, 1)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        # Delete button
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #ff4444; color: white; padding: 10px 20px; border-radius: 15px; font-weight: bold;")
        delete_btn.clicked.connect(self.delete_selected_crypto)
        
        # Accept buttons
        encrypt_btn = QPushButton("Accept")
        encrypt_btn.setStyleSheet("background-color: white; color: #4b0082; padding: 10px 20px; border-radius: 15px; font-weight: bold;")
        encrypt_btn.clicked.connect(self.process_encrypt_actions)
        
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(encrypt_btn)
        
        layout.addLayout(buttons_layout)
        
        # Load initial data
        self.load_crypto_actions()
        
        return view


    def create_zip_view(self):
        """Zip Files tab"""
        view = QWidget()
        layout = QVBoxLayout(view)
        
        title = QLabel("Zip Operations")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # File table
        self.zip_table = QTableWidget()
        self.zip_table.setColumnCount(4)
        self.zip_table.setHorizontalHeaderLabels(["", "File Name", "Current Location", "Destination"])
        self.zip_table.horizontalHeader().setVisible(False)
        self.zip_table.verticalHeader().setVisible(False)
        self.zip_table.setShowGrid(False)
        self.zip_table.setStyleSheet("background-color: #4b0082; color: white; border: none;")
        
        # Column sizing
        self.zip_table.setColumnWidth(0, 40)   # Checkbox
        self.zip_table.setColumnWidth(1, 200)  # Filename
        self.zip_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.zip_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        layout.addWidget(self.zip_table, 1)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        # Delete button
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #ff4444; color: white; padding: 10px 20px; border-radius: 15px; font-weight: bold;")
        delete_btn.clicked.connect(self.delete_selected_zip)
        
        # Accept button
        accept_btn = QPushButton("Accept")
        accept_btn.setStyleSheet("background-color: white; color: #4b0082; padding: 10px 20px; border-radius: 15px; font-weight: bold;")
        accept_btn.clicked.connect(self.handle_zip_actions)
        
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(accept_btn)
        
        layout.addLayout(buttons_layout)
        
        # Load initial data
        self.load_zip_actions()
        
        return view


    def handle_zip_actions(self):
        """Process both compression and extraction actions"""
        # Process compress actions
        self.process_compress_actions()
        
        # Process extract actions
        self.process_extract_actions()

    def update_processed_files(self, new_paths):
        """Add new paths to processed_files.json"""
        try:
            try:
                with open('processed_files.json', 'r') as f:
                    processed = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                processed = []
                
            # Add new paths
            for path in new_paths:
                if path and path not in processed:
                    processed.append(path)
                    
            # Write back to file
            with open('processed_files.json', 'w') as f:
                json.dump(processed, f, indent=2)
            
            load_processed_files()
                
        except Exception as e:
            print(f"[x] Error updating processed files: {str(e)}")

    def load_rules(self):
        # Initialize rules as class attributes
        try:
            with open('sorting_rules.txt', 'r') as f:
                self.tech_rules = json.load(f)  # Technical implementation
        except (FileNotFoundError, json.JSONDecodeError):
            self.tech_rules = []

        try:
            with open('rules.json', 'r') as f:
                self.user_prompts = json.load(f)  # User-facing descriptions
        except (FileNotFoundError, json.JSONDecodeError):
            self.user_prompts = []
        
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create cards from user prompts
        for i, prompt in enumerate(self.user_prompts):
            card = RuleCardWidget(i+1, prompt)
            self.cards_layout.addWidget(card)
        
        self.cards_layout.addStretch()
        
        # Update JSON view
        self.rules_json.setText(json.dumps(self.tech_rules, indent=2))




    def load_files_to_sort(self):
        """Load from pending_actions.json instead of sample data"""
        self.sort_table.setRowCount(0)
        
        try:
            with open('pending_actions.json', 'r') as f:
                pending = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
            
        for i, action in enumerate(pending):
            self.sort_table.insertRow(i)
            
            # Checkbox
            checkbox = QCheckBox()
            self.sort_table.setCellWidget(i, 0, checkbox)
            
            # Icon
            icon_label = QLabel("📄")
            icon_label.setAlignment(Qt.AlignCenter)
            self.sort_table.setCellWidget(i, 1, icon_label)
            
            # Filename
            filename = os.path.basename(action['original_path'])
            filename_item = QTableWidgetItem(filename)
            filename_item.setForeground(Qt.white)
            self.sort_table.setItem(i, 2, filename_item)
            
            # Old path
            old_path_item = QTableWidgetItem(action['original_path'])
            old_path_item.setForeground(Qt.white)
            self.sort_table.setItem(i, 3, old_path_item)
            
            # New path
            new_path_item = QTableWidgetItem(action['target_path'])
            new_path_item.setForeground(Qt.white)
            self.sort_table.setItem(i, 4, new_path_item)
        
    def process_encrypt_actions(self):
        """Process all pending encryption actions"""
        try:
            with open('encrypt_actions.json', 'r') as f:
                actions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.information(self, "Info", "No pending encrypt actions")
            return

        success = 0
        for filepath in actions:
            try:
                encrypt_file(filepath)
                success += 1
            except Exception as e:
                print(f"[x] Failed to encrypt {filepath}: {str(e)}")

        # Clear processed actions
        with open('encrypt_actions.json', 'w') as f:
            json.dump([], f, indent=2)
            
        QMessageBox.information(self, "Complete", 
            f"Encrypted {success}/{len(actions)} files successfully")
        self.load_crypto_actions()

    def process_decrypt_actions(self):
        """Process all pending decryption actions"""
        try:
            with open('decrypt_actions.json', 'r') as f:
                actions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.information(self, "Info", "No pending decrypt actions")
            return

        success = 0
        for filepath in actions:
            try:
                decrypt_file(filepath)
                success += 1
            except Exception as e:
                print(f"[x] Failed to decrypt {filepath}: {str(e)}")

        # Clear processed actions
        with open('decrypt_actions.json', 'w') as f:
            json.dump([], f, indent=2)
            
        QMessageBox.information(self, "Complete", 
            f"Decrypted {success}/{len(actions)} files successfully")
        self.load_crypto_actions()

    def process_compress_actions(self):
        """Process all pending compression actions"""
        try:
            with open('compress_actions.json', 'r') as f:
                actions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.information(self, "Info", "No pending compress actions")
            return

        success = 0
        for filepath in actions:
            try:
                output_dir = os.path.join(os.path.dirname(filepath), "Compressed")
                compress_file(filepath, output_dir)
                success += 1
            except Exception as e:
                print(f"[x] Failed to compress {filepath}: {str(e)}")

        # Clear processed actions
        with open('compress_actions.json', 'w') as f:
            json.dump([], f, indent=2)
            
        QMessageBox.information(self, "Complete", 
            f"Compressed {success}/{len(actions)} files successfully")
        self.load_zip_actions()

    def process_extract_actions(self):
        """Process all pending extraction actions"""
        try:
            with open('extract_actions.json', 'r') as f:
                actions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.information(self, "Info", "No pending extract actions")
            return

        success = 0
        processed_paths = []  # Track new paths
        
        for filepath in actions:
            try:
                output_dir = os.path.join(os.path.dirname(filepath), "Extracted")
                extracted_files = extract_file(filepath, output_dir)  # Should return list of extracted files
                success += 1
                
                # Add extracted files to processed paths
                if isinstance(extracted_files, list):
                    processed_paths.extend(extracted_files)
                elif extracted_files:  # Single path
                    processed_paths.append(extracted_files)
                    
            except Exception as e:
                print(f"[x] Failed to extract {filepath}: {str(e)}")

        # Update processed files list
        self.update_processed_files(processed_paths)
        
        # Clear processed actions
        with open('extract_actions.json', 'w') as f:
            json.dump([], f, indent=2)
            
        QMessageBox.information(self, "Complete", 
            f"Extracted {success}/{len(actions)} files successfully")
        self.load_zip_actions()


    def get_files_to_delete(self,filename='files_to_be_deleted.txt'):
      """Get Scheduled Files that Need to be Deleted"""
      files = []
      now = datetime.now()
      
      try:
          # Check if file exists first
          if not os.path.exists(filename):
              print(f"[!] Schedule file '{filename}' not found")
              return files
              
          # Check if file is empty
          if os.path.getsize(filename) == 0:
              return files

          with open(filename, 'r') as f:
              try:
                  scheduled = json.load(f)
              except json.JSONDecodeError as e:
                  print(f"[x] Invalid JSON in {filename}: {str(e)}")
                  return files

              for filepath, date_str in scheduled.items():
                  try:
                      # Validate path exists before processing
                      if not os.path.exists(filepath):
                          print(f"[!] Scheduled file missing: {filepath}")
                          continue

                      deletion_date = datetime.fromisoformat(date_str)
                      delta = deletion_date - now
                      
                      if delta.total_seconds() > 0:
                          days = delta.days
                          hours, remainder = divmod(delta.seconds, 3600)
                          minutes, _ = divmod(remainder, 60)
                          time_left = f"{days}d {hours}h {minutes}m"
                      else:
                          time_left = "Due now"

                      filename_only = os.path.basename(filepath)
                      files.append({
                          "filename": filename_only,
                          "time_left": time_left,
                          "full_path": filepath
                      })
                      
                  except Exception as e:
                      print(f"[x] Error processing {filepath}: {str(e)}")

      except Exception as e:
          print(f"[!] Critical error reading {filename}: {str(e)}")
          
      return files


    def load_files_to_delete(self):
        # Clear table
        self.delete_table.setRowCount(0)
        
        
        try:
            files = self.get_files_to_delete()
        except Exception as e:
            print(f"Error loading deletion schedule: {str(e)}")
            return
        
        # Add files to table
        for i, file in enumerate(files):
            self.delete_table.insertRow(i)
            
            # Checkbox
            checkbox = QCheckBox()
            self.delete_table.setCellWidget(i, 0, checkbox)
            
            # Icon
            icon_label = QLabel("📄")
            icon_label.setAlignment(Qt.AlignCenter)
            self.delete_table.setCellWidget(i, 1, icon_label)
            
            # Filename
            filename_item = QTableWidgetItem(file["filename"])
            filename_item.setForeground(Qt.white)
            self.delete_table.setItem(i, 2, filename_item)
            
            # Time left
            time_left_item = QTableWidgetItem(file["time_left"])
            time_left_item.setForeground(Qt.white)
            self.delete_table.setItem(i, 3, time_left_item)
    
    def add_rule(self):
        text, ok = QInputDialog.getText(
            self,
            "Create New Rule",
            "Describe your rule in natural language:",
            text=""
        )
        
        if ok and text:
            # Save original prompt to rules.json
            try:
                with open('rules.json', 'r') as f:
                    user_rules = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                user_rules = []
                
            user_rules.append(text)
            
            with open('rules.json', 'w') as f:
                json.dump(user_rules, f, indent=2)
            
            # Generate and save technical rule
            new_rule = create_rule_from_natural_language(text)
            if new_rule:
                with open('sorting_rules.txt', 'r') as f:
                    try:
                        tech_rules = json.load(f)
                    except (FileNotFoundError, json.JSONDecodeError):
                        tech_rules = []
                        
                tech_rules.append(new_rule)
                
                with open('sorting_rules.txt', 'w') as f:
                    json.dump(tech_rules, f, indent=2)
                
                self.load_rules()

    def load_crypto_actions(self):
        """Load pending encryption actions"""
        self.crypt_table.setRowCount(0)
        
        try:
            with open('encrypt_actions.json', 'r') as f:
                encrypt_actions = json.load(f)
            with open('decrypt_actions.json', 'r') as f:
                decrypt_actions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            encrypt_actions = []
            decrypt_actions = []
        
        # Add encrypt actions
        row = 0
        for filepath in encrypt_actions:
            self.crypt_table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            self.crypt_table.setCellWidget(row, 0, checkbox)
            
            # Filename
            filename = os.path.basename(filepath)
            filename_item = QTableWidgetItem(filename)
            filename_item.setForeground(Qt.white)
            self.crypt_table.setItem(row, 1, filename_item)
            
            # Action
            action_item = QTableWidgetItem("Encrypt")
            action_item.setForeground(Qt.white)
            self.crypt_table.setItem(row, 2, action_item)
            
            row += 1
        
        # Add decrypt actions
        for filepath in decrypt_actions:
            self.crypt_table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            self.crypt_table.setCellWidget(row, 0, checkbox)
            
            # Filename
            filename = os.path.basename(filepath)
            filename_item = QTableWidgetItem(filename)
            filename_item.setForeground(Qt.white)
            self.crypt_table.setItem(row, 1, filename_item)
            
            # Action
            action_item = QTableWidgetItem("Decrypt")
            action_item.setForeground(Qt.white)
            self.crypt_table.setItem(row, 2, action_item)
            
            row += 1

    def load_zip_actions(self):
        """Load pending compression/extraction actions"""
        self.zip_table.setRowCount(0)
        
        try:
            with open('compress_actions.json', 'r') as f:
                compress_actions = json.load(f)
            with open('extract_actions.json', 'r') as f:
                extract_actions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            compress_actions = []
            extract_actions = []
        
        # Add compress actions
        row = 0
        for filepath in compress_actions:
            self.zip_table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            self.zip_table.setCellWidget(row, 0, checkbox)
            
            # Filename
            filename = os.path.basename(filepath)
            filename_item = QTableWidgetItem(filename)
            filename_item.setForeground(Qt.white)
            self.zip_table.setItem(row, 1, filename_item)
            
            # Current location
            current_dir = os.path.dirname(filepath)
            current_item = QTableWidgetItem(current_dir)
            current_item.setForeground(Qt.white)
            self.zip_table.setItem(row, 2, current_item)
            
            # Destination
            dest_dir = os.path.join(os.path.dirname(filepath), "Compressed")
            dest_item = QTableWidgetItem(dest_dir)
            dest_item.setForeground(Qt.white)
            self.zip_table.setItem(row, 3, dest_item)
            
            row += 1
        
        # Add extract actions
        for filepath in extract_actions:
            self.zip_table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            self.zip_table.setCellWidget(row, 0, checkbox)
            
            # Filename
            filename = os.path.basename(filepath)
            filename_item = QTableWidgetItem(filename)
            filename_item.setForeground(Qt.white)
            self.zip_table.setItem(row, 1, filename_item)
            
            # Current location
            current_dir = os.path.dirname(filepath)
            current_item = QTableWidgetItem(current_dir)
            current_item.setForeground(Qt.white)
            self.zip_table.setItem(row, 2, current_item)
            
            # Destination
            dest_dir = os.path.join(os.path.dirname(filepath), "Extracted")
            dest_item = QTableWidgetItem(dest_dir)
            dest_item.setForeground(Qt.white)
            self.zip_table.setItem(row, 3, dest_item)
            
            row += 1

    def delete_rule(self):
        """Delete the last rule from both technical and user rules"""
        try:
            if self.tech_rules:
                self.tech_rules.pop()
                
            if self.user_prompts:
                self.user_prompts.pop()
                
            # Save both files
            with open('sorting_rules.txt', 'w') as f:
                json.dump(self.tech_rules, f, indent=2)
                
            with open('rules.json', 'w') as f:
                json.dump(self.user_prompts, f, indent=2)
                
            self.load_rules()  # Refresh UI
            
        except IndexError:
            QMessageBox.warning(self, "Warning", "No rules to delete!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete rule: {str(e)}")

    def delete_selected_crypto(self):
        """Remove selected crypto actions"""
        # Get indices of checked rows for encrypt
        encrypt_indices = []
        decrypt_indices = []
        
        encrypt_count = 0
        decrypt_count = 0
        
        # Get encrypt actions first
        try:
            with open('encrypt_actions.json', 'r') as f:
                encrypt_actions = json.load(f)
            encrypt_count = len(encrypt_actions)
        except (FileNotFoundError, json.JSONDecodeError):
            encrypt_actions = []
        
        # Get decrypt actions
        try:
            with open('decrypt_actions.json', 'r') as f:
                decrypt_actions = json.load(f)
            decrypt_count = len(decrypt_actions)
        except (FileNotFoundError, json.JSONDecodeError):
            decrypt_actions = []
        
        # Check which rows are selected
        for row in range(self.crypt_table.rowCount()):
            if self.crypt_table.cellWidget(row, 0).isChecked():
                # Determine if it's encrypt or decrypt
                if row < encrypt_count:
                    encrypt_indices.append(row)
                else:
                    decrypt_indices.append(row - encrypt_count)
        
        # Remove from encrypt actions
        new_encrypt = [
            action for idx, action in enumerate(encrypt_actions)
            if idx not in encrypt_indices
        ]
        
        # Remove from decrypt actions
        new_decrypt = [
            action for idx, action in enumerate(decrypt_actions)
            if idx not in decrypt_indices
        ]
        
        # Save updated lists
        with open('encrypt_actions.json', 'w') as f:
            json.dump(new_encrypt, f, indent=2)
        
        with open('decrypt_actions.json', 'w') as f:
            json.dump(new_decrypt, f, indent=2)
        
        # Refresh view
        self.load_crypto_actions()

    def delete_selected_zip(self):
        """Remove selected zip actions"""
        # Similar implementation to delete_selected_crypto
        # but for compress_actions.json and extract_actions.json
        compress_indices = []
        extract_indices = []
        
        compress_count = 0
        extract_count = 0
        
        try:
            with open('compress_actions.json', 'r') as f:
                compress_actions = json.load(f)
            compress_count = len(compress_actions)
        except (FileNotFoundError, json.JSONDecodeError):
            compress_actions = []
        
        try:
            with open('extract_actions.json', 'r') as f:
                extract_actions = json.load(f)
            extract_count = len(extract_actions)
        except (FileNotFoundError, json.JSONDecodeError):
            extract_actions = []
        
        for row in range(self.zip_table.rowCount()):
            if self.zip_table.cellWidget(row, 0).isChecked():
                if row < compress_count:
                    compress_indices.append(row)
                else:
                    extract_indices.append(row - compress_count)
        
        new_compress = [
            action for idx, action in enumerate(compress_actions)
            if idx not in compress_indices
        ]
        
        new_extract = [
            action for idx, action in enumerate(extract_actions)
            if idx not in extract_indices
        ]
        
        with open('compress_actions.json', 'w') as f:
            json.dump(new_compress, f, indent=2)
        
        with open('extract_actions.json', 'w') as f:
            json.dump(new_extract, f, indent=2)
        
        self.load_zip_actions()

    def save_rules(self):
        try:
            with open('sorting_rules.txt', 'w') as f:
                json.dump(self.rules, f, indent=2)
            self.load_rules()  # Add this line to refresh GUI after save
            print("Rules saved successfully")
        except Exception as e:
            print(f"Error saving rules: {str(e)}")

    
    def accept_sort(self):
      """Execute all pending moves/copies after user confirmation"""
      try:
          with open('pending_actions.json', 'r') as f:
              pending = json.load(f)
      except (FileNotFoundError, json.JSONDecodeError):
          return
      
      sorter = FileSorter()
      failed_actions = []

      for action in pending:
          try:
              if action['type'] == 'move':
                  sorter.move_file(action['original_path'], action['target_path'])
              elif action['type'] == 'copy':
                  sorter.copy_file(action['original_path'], action['target_path'])
          except Exception as e:
              failed_actions.append(action)
              print(f"[x] Failed to {action['type']} {action['original_path']}: {str(e)}")
      
      # Clear processed actions
      with open('pending_actions.json', 'w') as f:
          json.dump(failed_actions, f, indent=2)
      
      self.load_files_to_sort()

def start_monitoring_process():
    """Start monitoring.py in the background with error handling"""
    try:
        script_path = os.path.join(os.path.dirname(__file__), "monitoring.py")
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"monitoring.py not found at {script_path}")
            
        proc = subprocess.Popen(
            [sys.executable, script_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP  # Windows only
        )
        print("[✓] Background monitoring started")
        return proc
    
    except Exception as e:
        print(f"[x] Failed to start monitoring: {str(e)}")
        return None


def kill_monitoring(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=3)
        print("[✓] Terminated monitoring process")


if __name__ == "__main__":
    monitor_prc = start_monitoring_process()
    atexit.register(kill_monitoring, monitor_prc)


    app = QApplication(sys.argv)
    app.setFont(QFont("Old Standard TT", 12))
    window = DigitalDeclutterAssistant()
    window.show()
    sys.exit(app.exec_())