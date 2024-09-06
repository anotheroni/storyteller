from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QFormLayout, QPushButton, QTextEdit, QLineEdit

from src.tokenizedtextedit import TokenizedTextEdit

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storywriter = parent
        self.setWindowTitle("Story Writer Settings")
        self.layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        # Title input
        self.title = QLineEdit(self.storywriter.storytitle)
        form_layout.addRow("Title", self.title)
        self.title.setToolTip("The title of the story. This is also currently used as the filename when saving or exporting the story.")

        # Summary input
        self.summary = TokenizedTextEdit(parent.global_worker)
        self.summary.setText(self.storywriter.summary)
        form_layout.addRow("Background\nInformation", self.summary)
        self.summary.setToolTip("Background information is always added at the top of prompts sent to the LLM.")

        self.chapter_summary_prompt = QTextEdit()
        self.chapter_summary_prompt.setPlaceholderText("Enter prompt for chapter summary generation")
        form_layout.addRow("Chapter Summary Prompt:", self.chapter_summary_prompt)

        self.scene_generation_prompt = QTextEdit()
        self.scene_generation_prompt.setPlaceholderText("Enter prompt for scene generation")
        form_layout.addRow("Scene Generation Prompt:", self.scene_generation_prompt)

        self.layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        save_button = QPushButton("OK")
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        self.layout.addLayout(button_layout)

    def accept(self):
        self.storywriter.storytitle = self.title.text()
        self.storywriter.summary = self.summary.toPlainText()
        super().accept()

    def get_chapter_summary_prompt(self):
        return self.chapter_summary_prompt.toPlainText()

    def set_chapter_summary_prompt(self, prompt):
        self.chapter_summary_prompt.setPlainText(prompt)

    def get_scene_generation_prompt(self):
        return self.scene_generation_prompt.toPlainText()

    def set_scene_generation_prompt(self, prompt):
        self.scene_generation_prompt.setPlainText(prompt)

