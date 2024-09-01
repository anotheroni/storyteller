from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QPushButton, QTextEdit

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Story Teller Settings")
        self.layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.chapter_summary_prompt = QTextEdit()
        self.chapter_summary_prompt.setPlaceholderText("Enter prompt for chapter summary generation")
        form_layout.addRow("Chapter Summary Prompt:", self.chapter_summary_prompt)

        self.scene_generation_prompt = QTextEdit()
        self.scene_generation_prompt.setPlaceholderText("Enter prompt for scene generation")
        form_layout.addRow("Scene Generation Prompt:", self.scene_generation_prompt)

        self.layout.addLayout(form_layout)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        self.layout.addWidget(save_button)

    def get_chapter_summary_prompt(self):
        return self.chapter_summary_prompt.toPlainText()

    def set_chapter_summary_prompt(self, prompt):
        self.chapter_summary_prompt.setPlainText(prompt)

    def get_scene_generation_prompt(self):
        return self.scene_generation_prompt.toPlainText()

    def set_scene_generation_prompt(self, prompt):
        self.scene_generation_prompt.setPlainText(prompt)

