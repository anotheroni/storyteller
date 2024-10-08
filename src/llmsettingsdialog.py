from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QWidget,
    QFileDialog, QMessageBox, QComboBox, QFormLayout, QCheckBox,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont

import json
import os
from src.llm_base import LLMBase

class LLMSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storywriter = parent
        self.setWindowTitle("LLM Settings")
        self.resize(800, 600)
        self.layout = QVBoxLayout(self)

        # Main layout with splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        # Left pane: List of LLMs
        self.llmListWidget = QListWidget()
        self.llmListWidget.setMinimumWidth(250)
        self.llmListWidget.setMaximumWidth(250)
        self.splitter.addWidget(self.llmListWidget)

        # Right pane: Edit widget
        self.editWidget = QWidget()
        self.editLayout = QFormLayout()
        self.editWidget.setLayout(self.editLayout)
        self.editWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.splitter.addWidget(self.editWidget)

        # Set splitter sizes to 50-50
        self.splitter.setSizes([1, 1])  # Equal sizes
        self.splitter.setStretchFactor(0, 0)  # LLM list (fixed size)
        self.splitter.setStretchFactor(1, 1)  # Right pane (expands)

        # Buttons at the bottom
        button_layout = QHBoxLayout()
        self.add_button = QComboBox()
        self.add_button.addItem("Add LLM")
        self.add_button.addItems(['Kobold', 'OpenAI'])
        self.add_button.currentIndexChanged.connect(self.add_llm)
        load_button = QPushButton("Load Config")
        load_button.clicked.connect(self.load_config)
        save_button = QPushButton("Save Config")
        save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(load_button)
        button_layout.addWidget(save_button)

        self.layout.addLayout(button_layout)

        # Token counting LLM combo box at the bottom
        token_layout = QHBoxLayout()
        self.token_count_llm_combo = QComboBox()
        self.token_count_llm_combo.setToolTip("Select the LLM to use for counting tokens")
        token_layout.addWidget(QLabel("LLM used for counting tokens:"))
        token_layout.addWidget(self.token_count_llm_combo)
        self.layout.addLayout(token_layout)

        # Close button at the bottom
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        self.layout.addWidget(close_button)

        # Data structures
        self.current_llm_data = None  # Currently selected llm_data

        # Populate the list with existing LLMs
        for llm in self.storywriter.llm_manager.llms:
            self.add_llm_item(llm)

        self.update_token_count_llm_combo()

        # Connect selection change in llmListWidget
        self.llmListWidget.currentItemChanged.connect(self.on_llm_selected)

        # Initially, select the first LLM if available
        if self.llmListWidget.count() > 0:
            self.llmListWidget.setCurrentRow(0)

    def add_llm_item(self, llm):
        # Create a QListWidgetItem with the LLM's name and status
        item = QListWidgetItem()
        llm_data = llm.get_config()
        item.setData(Qt.UserRole, llm_data)
        # Set the display text with advanced formatting
        self.update_list_item_text(item, llm_data['name'], "Not tested")
        self.llmListWidget.addItem(item)
        self.update_token_count_llm_combo()

    def update_list_item_text(self, item, name, status):
        # Create a multi-line text with name and status
        item.setText(f"{name}\n{status}")
        # Apply formatting to the item
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        # Set size hint to accommodate two lines
        item.setSizeHint(QSize(item.sizeHint().width(), 40))

    def on_llm_selected(self, current, previous):
        if current:
            llm_data = current.data(Qt.UserRole)
            self.current_llm_data = llm_data
            self.update_edit_widget()
        else:
            # Clear the edit widget
            self.current_llm_data = None
            self.clear_edit_widget()

    def update_edit_widget(self):
        # Clear existing widgets
        self.clear_edit_widget()

        if self.current_llm_data is None:
            return

        llm_data = self.current_llm_data
        llm_type = llm_data['type']

        # Create widgets for editing llm_data
        self.name_edit = QLineEdit(llm_data['name'])
        self.name_edit.textChanged.connect(self.on_name_changed)
        self.editLayout.addRow("Name:", self.name_edit)

        # Display the LLM type (non-editable)
        self.type_label = QLabel(llm_type)
        self.editLayout.addRow("Type:", self.type_label)

        # Address field
        self.address_edit = QLineEdit(llm_data.get('address', ''))
        self.address_edit.textChanged.connect(self.on_address_changed)
        self.editLayout.addRow("Address:", self.address_edit)

        # System prompt field
        self.system_prompt_edit = QLineEdit(llm_data.get('system_prompt', ''))
        self.system_prompt_edit.textChanged.connect(self.on_system_prompt_changed)
        self.editLayout.addRow("System Prompt:", self.system_prompt_edit)

        # Fields specific to OpenAI
        if llm_type == 'OpenAI':
            self.api_key_edit = QLineEdit(llm_data.get('api_key', ''))
            self.api_key_edit.textChanged.connect(self.on_api_key_changed)
            self.editLayout.addRow("API Key:", self.api_key_edit)

            self.use_env_var_checkbox = QCheckBox("Use Environment Variable for API Key")
            self.use_env_var_checkbox.setChecked(llm_data.get('use_env_var', False))
            self.use_env_var_checkbox.stateChanged.connect(self.on_use_env_var_changed)
            self.editLayout.addRow("", self.use_env_var_checkbox)

        # Test connection button and status label
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        self.status_label = QLabel("Not tested")
        self.editLayout.addRow(self.test_button, self.status_label)

        # Remove button
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_current_llm)
        self.editLayout.addRow(self.remove_button)

    def clear_edit_widget(self):
        # Remove all widgets from the edit layout
        while self.editLayout.count():
            item = self.editLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def on_name_changed(self, text):
        if self.current_llm_data:
            self.current_llm_data['name'] = text
            # Update the item in the list
            item = self.llmListWidget.currentItem()
            status = self.status_label.text()
            self.update_list_item_text(item, text, status)
            self.update_token_count_llm_combo()

    def on_address_changed(self, text):
        if self.current_llm_data:
            self.current_llm_data['address'] = text

    def on_system_prompt_changed(self, text):
        if self.current_llm_data:
            self.current_llm_data['system_prompt'] = text

    def on_api_key_changed(self, text):
        if self.current_llm_data:
            self.current_llm_data['api_key'] = text

    def on_use_env_var_changed(self, state):
        if self.current_llm_data:
            self.current_llm_data['use_env_var'] = bool(state)

    def remove_current_llm(self):
        item = self.llmListWidget.currentItem()
        if item:
            self.llmListWidget.takeItem(self.llmListWidget.row(item))
            self.current_llm_data = None
            self.update_token_count_llm_combo()
            # Clear edit widget
            self.update_edit_widget()

    def test_connection(self):
        if self.current_llm_data:
            self.status_label.setText("Testing connection...")
            llm_data = self.current_llm_data
            self.thread = QThread()
            self.worker = TestConnectionWorker(llm_data)
            self.worker.moveToThread(self.thread)

            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self.worker.progress.connect(lambda status: self.status_label.setText(status))
            self.worker.finished.connect(lambda success: self.show_connection_result(success))

            self.thread.start()

    def show_connection_result(self, success):
        if success:
            self.status_label.setText("Connection successful")
        else:
            self.status_label.setText("Connection failed")
        # Update status in llmListWidget
        item = self.llmListWidget.currentItem()
        if item and self.current_llm_data:
            name = self.current_llm_data['name']
            status = self.status_label.text()
            self.update_list_item_text(item, name, status)

    def add_llm(self, index):
        # Skip the first item (placeholder "Add LLM")
        if index == 0:
            return
        llm_type = self.add_button.currentText()
        self.add_button.setCurrentIndex(0)  # Reset to placeholder
        # Create default llm_data
        llm_data = {
            'name': f"New {llm_type} LLM",
            'type': llm_type,
            'address': '',
            'api_key': '',
            'system_prompt': 'You are a helpful assistant.',
            'use_env_var': False,
        }
        # Create a QListWidgetItem
        item = QListWidgetItem()
        item.setData(Qt.UserRole, llm_data)
        self.update_list_item_text(item, llm_data['name'], "Not tested")
        self.llmListWidget.addItem(item)
        # Select the new item
        self.llmListWidget.setCurrentItem(item)
        self.update_token_count_llm_combo()

    def update_token_count_llm_combo(self):
        current_text = self.token_count_llm_combo.currentText()
        self.token_count_llm_combo.clear()
        for index in range(self.llmListWidget.count()):
            item = self.llmListWidget.item(index)
            llm_data = item.data(Qt.UserRole)
            self.token_count_llm_combo.addItem(llm_data['name'])
        # Restore selection if possible
        index = self.token_count_llm_combo.findText(current_text)
        if index >= 0:
            self.token_count_llm_combo.setCurrentIndex(index)

    def load_config(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName()
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "Invalid File", "Please select a valid configuration file.")
            return
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Clear existing LLMs
        self.llmListWidget.clear()
        self.current_llm_data = None
        self.clear_edit_widget()
        # Load LLMs
        for llm_data in data.get('llms', []):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, llm_data)
            self.update_list_item_text(item, llm_data['name'], "Not tested")
            self.llmListWidget.addItem(item)
        self.update_token_count_llm_combo()
        # Set token counting LLM
        token_count_llm_name = data.get('token_count_llm_name', '')
        index = self.token_count_llm_combo.findText(token_count_llm_name)
        if index >= 0:
            self.token_count_llm_combo.setCurrentIndex(index)
        else:
            QMessageBox.warning(self, "Error", f"Token counting LLM '{token_count_llm_name}' not found in the list.")

    def save_config(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName()
        if not file_path:
            return
        data = {}
        llms_data = []
        for index in range(self.llmListWidget.count()):
            item = self.llmListWidget.item(index)
            llm_data = item.data(Qt.UserRole)
            llms_data.append(llm_data)
        data['llms'] = llms_data
        data['token_count_llm_name'] = self.token_count_llm_combo.currentText()
        with open(file_path, 'w') as f:
            json.dump(data, f)

    def accept(self):
        # Update the llm_manager's LLMs
        self.storywriter.llm_manager.llms = []
        for index in range(self.llmListWidget.count()):
            item = self.llmListWidget.item(index)
            llm_data = item.data(Qt.UserRole)
            # Create LLM instance from llm_data
            llm = LLMBase.create_llm(llm_data)
            if llm:
                self.storywriter.llm_manager.llms.append(llm)
        self.storywriter.llm_manager.token_count_llm_name = self.token_count_llm_combo.currentText()
        super().accept()

class TestConnectionWorker(QObject):
    finished = pyqtSignal(bool)
    progress = pyqtSignal(str)

    def __init__(self, llm_data):
        super().__init__()
        self.llm_data = llm_data

    def run(self):
        self.progress.emit("Connecting...")

        try:
            llm_type = self.llm_data['type']
            if llm_type == 'OpenAI':
                from src.llm_openai import LLMOpenAI
                llm = LLMOpenAI(
                    self.llm_data['name'],
                    self.llm_data['address'],
                    self.llm_data['api_key'],
                    self.llm_data['system_prompt'],
                    self.llm_data['use_env_var']
                )
            elif llm_type == 'Kobold':
                from src.llm_kobold import LLMKobold
                llm = LLMKobold(
                    self.llm_data['name'],
                    self.llm_data['address'],
                    self.llm_data['system_prompt']
                )
            # Add other LLM types if needed
            success = llm.test_connection()
        except Exception as e:
            self.progress.emit(f"Connection failed: {str(e)}")
            success = False

        self.progress.emit("Finishing up...")
        self.finished.emit(success)

