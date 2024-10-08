# src/storyobjectdialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTextEdit, QWidget, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import Qt

from src.tokenizedtextedit import TokenizedTextEdit

class StoryObjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storywriter = parent
        self.setWindowTitle("Story Objects")
        self.resize(600, 400)

        self.layout = QHBoxLayout(self)

        # List of objects
        self.object_list = QListWidget()
        self.layout.addWidget(self.object_list)

        # Object details
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout()
        self.details_widget.setLayout(self.details_layout)

        self.name_edit = QLineEdit()
        self.tags_edit = QLineEdit()
        self.short_desc_edit = TokenizedTextEdit(self.storywriter.global_worker)
        self.long_desc_edit = TokenizedTextEdit(self.storywriter.global_worker)

        self.details_layout.addWidget(QLabel("Name:"))
        self.details_layout.addWidget(self.name_edit)
        self.details_layout.addWidget(QLabel("Tags (comma-separated):"))
        self.details_layout.addWidget(self.tags_edit)
        self.details_layout.addWidget(QLabel("Short Description:"))
        self.details_layout.addWidget(self.short_desc_edit)
        self.details_layout.addWidget(QLabel("Long Description:"))
        self.details_layout.addWidget(self.long_desc_edit)

        self.layout.addWidget(self.details_widget)

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_object)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_object)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self.remove_object)
        button_layout.addWidget(add_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(remove_button)

        self.details_layout.addLayout(button_layout)

        # Load existing objects
        self.load_objects()

        # Signals
        self.object_list.currentItemChanged.connect(self.display_object)

    def load_objects(self):
        self.object_list.clear()
        for obj in self.storywriter.story_objects:
            item = QListWidgetItem(obj['name'])
            item.setData(Qt.UserRole, obj)
            self.object_list.addItem(item)

    def add_object(self):
        name = self.name_edit.text()
        if not name:
            QMessageBox.warning(self, "Error", "Name cannot be empty.")
            return
        obj = {
            'name': name,
            'tags': self.tags_edit.text(),
            'short_desc': self.short_desc_edit.toPlainText(),
            'long_desc': self.long_desc_edit.toPlainText()
        }
        self.storywriter.story_objects.append(obj)
        item = QListWidgetItem(obj['name'])
        item.setData(Qt.UserRole, obj)
        self.object_list.addItem(item)
        self.clear_fields()

    def save_object(self):
        current_item = self.object_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "No object selected.")
            return
        obj = current_item.data(Qt.UserRole)
        obj['name'] = self.name_edit.text()
        obj['tags'] = self.tags_edit.text()
        obj['short_desc'] = self.short_desc_edit.toPlainText()
        obj['long_desc'] = self.long_desc_edit.toPlainText()
        current_item.setText(obj['name'])
        self.clear_fields()

    def remove_object(self):
        current_item = self.object_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "No object selected.")
            return
        obj = current_item.data(Qt.UserRole)
        self.storywriter.story_objects.remove(obj)
        self.object_list.takeItem(self.object_list.row(current_item))
        self.clear_fields()

    def display_object(self, current, previous):
        if current:
            obj = current.data(Qt.UserRole)
            self.name_edit.setText(obj['name'])
            self.tags_edit.setText(obj['tags'])
            self.short_desc_edit.setPlainText(obj['short_desc'])
            self.long_desc_edit.setPlainText(obj['long_desc'])
        else:
            self.clear_fields()

    def clear_fields(self):
        self.name_edit.clear()
        self.tags_edit.clear()
        self.short_desc_edit.setPlainText("")
        self.long_desc_edit.setPlainText("")

