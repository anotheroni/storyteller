from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QWidget, QFileDialog, QMessageBox, QComboBox, QScrollArea, QFormLayout
from src.llm import LLMBackend
import json

class LLMSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storywriter = parent
        self.setWindowTitle("LLM Settings")
        self.layout = QVBoxLayout(self)

        # Scroll area for LLM configurations
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.llmWidget = QWidget()
        self.llmLayout = QVBoxLayout()
        self.llmWidget.setLayout(self.llmLayout)
        self.scrollArea.setWidget(self.llmWidget)

        self.layout.addWidget(self.scrollArea)

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add LLM")
        add_button.clicked.connect(self.add_llm)
        load_button = QPushButton("Load Config")
        load_button.clicked.connect(self.load_config)
        save_button = QPushButton("Save Config")
        save_button.clicked.connect(self.save_config)
        button_layout.addWidget(add_button)
        button_layout.addWidget(load_button)
        button_layout.addWidget(save_button)

        self.layout.addLayout(button_layout)

        # Load existing LLMs
        self.llm_widgets = []
        for llm in self.storywriter.llm_manager.llms:
            self.add_llm_widget(llm)

    def add_llm_widget(self, llm=None):
        widget = QWidget()
        form_layout = QFormLayout()
        widget.setLayout(form_layout)

        name_edit = QLineEdit()
        address_edit = QLineEdit()
        system_prompt_edit = QLineEdit()
        type_combo = QComboBox()
        type_combo.addItems(['Kobold', 'OpenAI'])
        test_button = QPushButton("Test Connection")
        status_label = QLabel("Not tested")

        if llm:
            name_edit.setText(llm.name)
            address_edit.setText(llm.address)
            system_prompt_edit.setText(llm.system_prompt)
            type_combo.setCurrentText(llm.type)

        form_layout.addRow("Name:", name_edit)
        form_layout.addRow("Type:", type_combo)
        form_layout.addRow("Address/API Key:", address_edit)
        form_layout.addRow("System Prompt:", system_prompt_edit)
        form_layout.addRow(test_button, status_label)

        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(lambda: self.remove_llm_widget(widget))
        form_layout.addRow(remove_button)

        test_button.clicked.connect(lambda: self.test_connection(address_edit.text(), type_combo.currentText(), status_label))

        self.llmLayout.addWidget(widget)
        self.llm_widgets.append((widget, name_edit, address_edit, system_prompt_edit, type_combo, status_label))

    def add_llm(self):
        self.add_llm_widget()

    def remove_llm_widget(self, widget):
        for i, (w, *_ ) in enumerate(self.llm_widgets):
            if w == widget:
                self.llmLayout.removeWidget(widget)
                widget.deleteLater()
                del self.llm_widgets[i]
                break

    def load_config(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName()
        if not file_path:
            return
        with open(file_path, 'r') as f:
            data = json.load(f)
            self.storywriter.llm_manager.llms = []
            # Clear existing widgets
            for w, *_ in self.llm_widgets:
                self.llmLayout.removeWidget(w)
                w.deleteLater()
            self.llm_widgets = []
            # Add new widgets
            for llm_data in data:
                llm = LLMBackend(llm_data['name'], llm_data['address'], llm_data['system_prompt'], llm_data.get('type', 'Kobold'))
                self.storywriter.llm_manager.llms.append(llm)
                self.add_llm_widget(llm)
                if not llm.test_connection():
                    QMessageBox.warning(self, "LLM Connection Error", f"Failed to connect to LLM {llm.name}")

    def save_config(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName()
        if not file_path:
            return
        data = []
        for _, name_edit, address_edit, system_prompt_edit, type_combo, _ in self.llm_widgets:
            data.append({
                'name': name_edit.text(),
                'address': address_edit.text(),
                'system_prompt': system_prompt_edit.text(),
                'type': type_combo.currentText()
            })
        with open(file_path, 'w') as f:
            json.dump(data, f)

    def test_connection(self, address, llm_type, status_label):
        llm = LLMBackend('Test', address, '', llm_type)
        if llm.test_connection():
            status_label.setText("Connection successful")
        else:
            status_label.setText("Connection failed")

    def accept(self):
        self.storywriter.llm_manager.llms = []
        for _, name_edit, address_edit, system_prompt_edit, type_combo, _ in self.llm_widgets:
            llm = LLMBackend(name_edit.text(), address_edit.text(), system_prompt_edit.text(), type_combo.currentText())
            self.storywriter.llm_manager.llms.append(llm)
        super().accept()

