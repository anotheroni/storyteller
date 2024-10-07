import json
import re
import sys
import traceback

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QMenuBar, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout, QGridLayout, QFileDialog, QFrame, QScrollArea, QSizePolicy, QMessageBox, QComboBox, QToolButton, QMenu
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QFocusEvent
import queue

from src.llm import CountTask, GenerateTask, LLMManager
from src.settingsdialog import SettingsDialog
from src.tokenizedtextedit import TokenizedTextEdit
from src.llmsettingsdialog import LLMSettingsDialog
from src.storyobjectdialog import StoryObjectDialog

def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("caught:", tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

# Create a Qt application
app = QApplication([])

exportedStylesheet = "background-color: rgb(252, 245, 229);"


####################################
## API access

class Worker(QObject):
    finished = pyqtSignal()

    def __init__(self):
        super(Worker, self).__init__()
        self.tasks = queue.Queue()

    @pyqtSlot(QObject)
    def addTask(self, task):
        self.tasks.put(task)
        if not global_thread.isRunning():
            global_thread.start()

    @pyqtSlot()
    def processNextTask(self):
        if not self.tasks.empty():
            task = self.tasks.get()
            task.execute()
            self.processNextTask()
        else:
            self.finished.emit()

# Global worker and thread
global_thread = QThread()

#####################################
## UI

class Scene(QWidget):
    sceneTextResponseReady = pyqtSignal(str)
    def __init__(self, parentChapter, sceneData=None):
        super().__init__()
        self.parentChapter = parentChapter
        self.global_worker = self.parentChapter.parentStory.global_worker
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.parentChapter.scenesLayout.addWidget(self)

        self.textLayout = QGridLayout()
        self.summary = TokenizedTextEdit(self.global_worker, self.parentChapter.parentStory.llm_manager)
        self.summary.setPlaceholderText("Scene Summary")
        self.summary.setMinimumHeight(100)
        self.textLayout.addWidget(QLabel("Scene Summary"),0,0)
        self.textLayout.addWidget(self.summary,1,0)

        self.summary.setToolTip("""This text is sent to the LLM to tell it what this scene is supposed to depict.
It is also used when generating later scenes in this chapter as part of the summary of how the chapter has progressed to this point.""")

        self.text = TokenizedTextEdit(self.global_worker, self.parentChapter.parentStory.llm_manager)
        self.text.setPlaceholderText("Text")
        self.text.setStyleSheet(exportedStylesheet)
        self.text.setToolTip("""This is the finished output text for this story.""")
        self.sceneTextResponseReady.connect(self.updateText)

        self.textLayout.addWidget(QLabel("Text"),0,1)
        self.textLayout.addWidget(self.text,1,1)

        self.layout.addLayout(self.textLayout)

        # Optimized buttons
        # Move/Remove Dropdown next to Scene Summary label
        self.move_remove_button = QToolButton()
        self.move_remove_button.setText('Options')
        self.move_remove_button.setPopupMode(QToolButton.InstantPopup)
        self.move_remove_menu = QMenu()

        move_up_action = QAction('Move Up', self)
        move_up_action.triggered.connect(self.moveSceneUp)
        self.move_remove_menu.addAction(move_up_action)

        move_down_action = QAction('Move Down', self)
        move_down_action.triggered.connect(self.moveSceneDown)
        self.move_remove_menu.addAction(move_down_action)

        remove_action = QAction('Remove Scene', self)
        remove_action.triggered.connect(self.deleteScene)
        self.move_remove_menu.addAction(remove_action)

        self.move_remove_button.setMenu(self.move_remove_menu)
        self.textLayout.addWidget(self.move_remove_button, 0, 0, alignment=Qt.AlignLeft)

        # Generate Dropdown next to Text label
        self.generate_button = QToolButton()
        self.generate_button.setText('Generate')
        self.generate_button.setPopupMode(QToolButton.InstantPopup)
        self.generate_menu = QMenu()

        # Add LLM options
        for llm in self.parentChapter.parentStory.llm_manager.llms:
            action = QAction(f'Generate with {llm.name}', self)
            action.triggered.connect(lambda checked, llm=llm: self.generateScene(llm))
            self.generate_menu.addAction(action)

        self.generate_button.setMenu(self.generate_menu)
        self.textLayout.addWidget(self.generate_button, 0, 1, alignment=Qt.AlignLeft)

        if sceneData:
            self.summary.setPlainTextAndTokens(sceneData["summary"], int(sceneData.get("summaryTokens", -1)))
            self.text.setPlainTextAndTokens(sceneData["text"], int(sceneData.get("textTokens", -1)))

    def deleteScene(self):
        self.parentChapter.scenesLayout.removeWidget(self)
        self.parentChapter.parentStory.update()
        self.deleteLater()
        return

    def generateScene(self, llm):
        chapter = self.parentChapter
        story = chapter.parentStory
        chapter_index = None
        scene_index = None
        for i in range(story.chapterLayout.count()):
            if story.chapterLayout.itemAt(i).widget() == chapter:
                chapter_index= i
                break
        for i in range(chapter.scenesLayout.count()):
            if chapter.scenesLayout.itemAt(i).widget() == self:
                scene_index = i
                break

        prompt = "{{[INPUT]}}\nYou are to take the role of an author writing a story. The story is titled \"" + story.title.text() + "\"."
        if len(story.summary.toPlainText()) > 0:
            prompt = prompt + "\n\nGeneral background information: " + story.summary.toPlainText()
        if len(story.genre.text()) > 0:
            prompt = prompt + "\n\nGenre: " + story.genre.text()
        # Include story objects in the prompt
        if story.story_objects:
            prompt += "\n\nStory Objects:"
            for obj in story.story_objects:
                prompt += f"\n- {obj['name']}: {obj['short_desc']}"

        prompt = prompt + "\n\nThe story so far has had the following major events happen:"
        for c in range(chapter_index + 1):
            chapter = story.chapterLayout.itemAt(c).widget()
            prompt = prompt + "\n\n" + chapter.summary.toPlainText()
        prompt = prompt + "\n\nThe current chapter is titled \"" + chapter.title.text() + "\""
        if scene_index > 1:
            prompt = prompt + "\n\nThe following scenes have already happened in this chapter:"
            for s in range(scene_index-1):
                prompt = prompt + "\n" + chapter.scenesLayout.itemAt(s).widget().summary.toPlainText()
        if scene_index > 0:
            prompt = prompt +"\n\nThe most recent scene before this one was:\n\n" + chapter.scenesLayout.itemAt(scene_index-1).widget().text.toPlainText()

        prompt = prompt + "\n\nYou are now writing the next scene in which the following occurs: " + self.summary.toPlainText() \
                     + "\n\n" + story.scene_generation_prompt + "\n{{[OUTPUT]}}"

        print(prompt)

        task = GenerateTask(prompt, self, llm)
        self.global_worker.addTask(task)
        self.text.setPlainTextAndTokens("Generating...", 0)

    def onResponseGenerated(self, response):
        self.sceneTextResponseReady.emit(response) # PyQt can't handle updates to the UI from other threads, need to route it through a signal
    def updateText(self, response):
        self.text.setPlainText(response)

    def moveScene(self, up):
        chapter = self.parentChapter
        scene_index = None
        scene_count = chapter.scenesLayout.count()
        for i in range(scene_count):
            if chapter.scenesLayout.itemAt(i).widget() == self:
                scene_index = i
                break
        target = scene_index
        if up:
            target = target - 1
        else:
            target = target + 1
        if target < 0 or target >= scene_count or scene_index < 0 or scene_index >= scene_count:
            return
        if scene_index > target:
            scene_index, target = target, scene_index
        layout = chapter.scenesLayout
        widget1 = layout.itemAt(scene_index).widget()
        widget2 = layout.itemAt(target).widget()
        layout.removeWidget(widget1)
        layout.removeWidget(widget2)
        layout.insertWidget(scene_index, widget2)
        layout.insertWidget(target, widget1)
        chapter.update()

    def moveSceneUp(self):
        self.moveScene(True)
    def moveSceneDown(self):
        self.moveScene(False)

class Chapter(QFrame):
    chapterSummaryTextResponseReady = pyqtSignal(str)
    def __init__(self, parentStory, chapterData=None):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.parentStory = parentStory

        title = QFormLayout()

        self.title = QLineEdit()
        self.title.setPlaceholderText('Chapter Title')
        self.title.setStyleSheet(exportedStylesheet)
        title.addRow('Chapter Title:', self.title)

        self.layout.addLayout(title)

        self.summary = TokenizedTextEdit(self.parentStory.global_worker, self.parentStory.llm_manager)
        self.summary.setPlaceholderText('Previous Chapter Summary')
        self.summary.setMinimumHeight(100)
        self.summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summaryLabel = QLabel('Summary of the\nprevious chapter:')
        generate_previous_button = QToolButton()
        generate_previous_button.setText('Generate')
        generate_previous_button.setPopupMode(QToolButton.InstantPopup)
        generate_menu = QMenu()

        # Add LLM options
        for llm in self.parentStory.llm_manager.llms:
            action = QAction(f'Generate with {llm.name}', self)
            action.triggered.connect(lambda checked, llm=llm: self.generateSummary(llm))
            generate_menu.addAction(action)

        generate_previous_button.setMenu(generate_menu)

        summaryContainer = QWidget()
        summaryContainerLayout = QGridLayout()
        summaryContainer.setLayout(summaryContainerLayout)
        summaryContainerLayout.addWidget(summaryLabel,0,0)
        summaryContainerLayout.addWidget(generate_previous_button,1,0)
        summaryContainerLayout.addWidget(self.summary,0,1,2,1)

        summaryContainer.setToolTip("""The summary of the previous chapter is used when prompting the LLM to provide it with context for how the story reached the current point.
Adding a summary of the "previous chapter" to the first chapter can be useful to provide background information that may not be relevant later in the story,
such as a description of how the characters got into the initial situation they first find themselves in.
You can use the AI to automatically generate a summary of the previous chapter's text, but it's good to review and edit it to ensure it focuses on what you consider important.""")
        self.chapterSummaryTextResponseReady.connect(self.updateSummaryText)

        self.layout.addWidget(summaryContainer)

        self.scenesWidget = QWidget()
        self.scenesLayout = QVBoxLayout()
        self.scenesLayout.setContentsMargins(20,0,0,0)
        self.scenesWidget.setLayout(self.scenesLayout)

        self.layout.addWidget(self.scenesWidget)

        buttons = QHBoxLayout()

        self.add_scene_button = QPushButton("Add a new scene to this chapter")
        self.add_scene_button.clicked.connect(self.addScene)
        buttons.addWidget(self.add_scene_button)
        self.delete_button = QPushButton('Remove this chapter')
        self.delete_button.clicked.connect(self.deleteChapter)
        buttons.addWidget(self.delete_button)

        self.layout.addLayout(buttons)

        if chapterData:
            self.title.setText(chapterData["title"])
            self.summary.setPlainTextAndTokens(chapterData["summary"], int(chapterData.get("summaryTokens", -1)))
            for sceneData in chapterData["scenes"]:
                Scene(self, sceneData)

        self.parentStory.chapterLayout.addWidget(self)
        self.parentStory.scrollContent.adjustSize()

    def deleteChapter(self):
        parentLayout = self.parentStory.chapterLayout
        parentLayout.removeWidget(self)
        self.deleteLater()
        self.parentStory.update()

    def addScene(self):
        Scene(self)

    def generateSummary(self, llm):
        chapter = self
        story = chapter.parentStory
        chapter_index = None
        for i in range(story.chapterLayout.count()):
            if story.chapterLayout.itemAt(i).widget() == chapter:
                chapter_index = i
                break
        if chapter_index == 0:
            return

        chapter_index = chapter_index - 1

        print("chapter index " + str(chapter_index))

        prompt = "{{[INPUT]}}\nYou are to take the role of an author writing a story. The story is titled \"" + story.title.text() + "\"."
        if len(story.summary.toPlainText()) > 0:
            prompt = prompt + "\nGeneral background information: " + story.summary.toPlainText()
        if len(story.genre.text()) > 0:
            prompt = prompt + "\n\nGenre: " + story.genre.text()
        prompt = prompt + "\n\nThe most recent chapter of the story is:"
        scenesLayout = story.chapterLayout.itemAt(chapter_index).widget().scenesLayout
        for i in range(scenesLayout.count()):
            prompt = prompt + "\n\n" + scenesLayout.itemAt(i).widget().text.toPlainText()

        prompt = prompt + "\n\n" + story.chapter_summary_prompt + "\n{{[OUTPUT]}}"

        print(prompt)

        task = GenerateTask(prompt, self, llm)
        self.parentStory.global_worker.addTask(task)
        self.summary.setPlainTextAndTokens("Generating...", 0)

    def onResponseGenerated(self, response):
        self.chapterSummaryTextResponseReady.emit(response)

    def updateSummaryText(self, response):
        self.summary.setPlainText(response)


def sanitize_filename(filename):
    return re.sub(r'(?u)[^-\w.]', '_', filename)

class StoryWriter(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Story Writer')
        self.resize(800, 600)

        self.storytitle = ""
        self.summary = ""

        # Worker thread
        self.global_worker = Worker()
        self.global_worker.moveToThread(global_thread)
        global_thread.started.connect(self.global_worker.processNextTask)
        self.global_worker.finished.connect(global_thread.quit)

        # LLM Manager
        self.llm_manager = LLMManager()
        self.llm_manager.load_llm_config()

        # Create a menu bar
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # Create file menu
        file_menu = menubar.addMenu("File")
        new_action = QAction("New", self)
        load_action = QAction("Load", self)
        save_action = QAction("Save", self)
        export_action = QAction("Export", self)
        llm_settings_action = QAction("LLM Settings", self)
        exit_action = QAction("Exit", self)

        # Connect actions to menu items
        file_menu.addAction(new_action)
        file_menu.addAction(load_action)
        file_menu.addAction(save_action)
        file_menu.addAction(export_action)
        file_menu.addAction(llm_settings_action)
        file_menu.addAction(exit_action)

        # Story menu
        settings_menu = menubar.addMenu("Story")
        settings_action = QAction("Settings", self)
        settings_menu.addAction(settings_action)
        new_chapter_action = QAction('Add a new Chapter', self)
        settings_menu.addAction(new_chapter_action)
        story_objects_action = QAction('Story Objects', self)
        settings_menu.addAction(story_objects_action)

        # Create main layout
        layout = QVBoxLayout()

        # Scroll area for chapters
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)

        self.scrollContent = QWidget(self.scrollArea)
        self.chapterLayout = QVBoxLayout(self.scrollContent)
        self.scrollContent.setLayout(self.chapterLayout)
        self.scrollArea.setWidget(self.scrollContent)
        self.scrollArea.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout.addWidget(self.scrollArea)

        # Set main layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Connect actions to functions
        new_action.triggered.connect(self.newStory)
        load_action.triggered.connect(self.loadStory)
        save_action.triggered.connect(self.saveStory)
        export_action.triggered.connect(self.exportStory)
        llm_settings_action.triggered.connect(self.open_llm_settings)
        exit_action.triggered.connect(self.quit_app)
        settings_action.triggered.connect(self.open_settings)
        new_chapter_action.triggered.connect(self.addChapter)
        story_objects_action.triggered.connect(self.open_story_objects)
        self.closeEvent = self.quit_app

        # Initialize default prompts
        self.chapter_summary_prompt = "Please summarize this chapter in 200 words or less, focusing on the information that's important for writing future scenes in this story."
        self.scene_generation_prompt = "Please write out this scene."

        # Initialize story objects
        self.story_objects = []

    def open_llm_settings(self):
        dialog = LLMSettingsDialog(self)
        if dialog.exec_():
            self.llm_manager.save_llm_config()
            # Update generate menus in scenes and chapters
            for i in range(self.chapterLayout.count()):
                chapter = self.chapterLayout.itemAt(i).widget()
                # Update chapter generate menus
                generate_menu = chapter.layout.itemAt(2).itemAt(1).widget().menu()
                generate_menu.clear()
                for llm in self.llm_manager.llms:
                    action = QAction(f'Generate with {llm.name}', self)
                    action.triggered.connect(lambda checked, llm=llm: chapter.generateSummary(llm))
                    generate_menu.addAction(action)
                # Update scenes generate menus
                for j in range(chapter.scenesLayout.count()):
                    scene = chapter.scenesLayout.itemAt(j).widget()
                    generate_menu = scene.generate_menu
                    generate_menu.clear()
                    for llm in self.llm_manager.llms:
                        action = QAction(f'Generate with {llm.name}', self)
                        action.triggered.connect(lambda checked, llm=llm: scene.generateScene(llm))
                        generate_menu.addAction(action)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.set_chapter_summary_prompt(self.chapter_summary_prompt)
        dialog.set_scene_generation_prompt(self.scene_generation_prompt)
        if dialog.exec_():
            self.chapter_summary_prompt = dialog.get_chapter_summary_prompt()
            self.scene_generation_prompt = dialog.get_scene_generation_prompt()

    def newStory(self):
        # TODO remove old to create a new story
        pass

    def quit_app(self, event=None):
        sys.exit()

    def addChapter(self):
        Chapter(self)

    def loadStory(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName()
        if not file_path:
            return
        jsonData = None
        with open(file_path, "r") as f:
            jsonData = json.load(f)
        if jsonData is None:
            return
        if self.chapter_summary_prompt is not None:
            self.chapter_summary_prompt = jsonData.get("chapter_summary_prompt", self.chapter_summary_prompt)
        if self.scene_generation_prompt is not None:
            self.scene_generation_prompt = jsonData.get("scene_generation_prompt", self.scene_generation_prompt)
        self.summary = jsonData.get("summary", "")
        self.storytitle = jsonData["title"]
        for widget in self.scrollContent.findChildren(QWidget):
            widget.deleteLater()
        self.chapterLayout.update()
        for chapterData in jsonData["chapters"]:
            Chapter(self, chapterData)

    def saveStory(self):
        filename = sanitize_filename(self.storytitle.text())
        jsonData = {}
        jsonData["title"] = self.storytitle.text()
        jsonData["chapter_summary_prompt"] = self.chapter_summary_prompt
        jsonData["scene_generation_prompt"] = self.scene_generation_prompt
        jsonData["summary"] = self.summary
        jsonData["chapters"] = []
        for i in range(self.chapterLayout.count()):
            chapter = self.chapterLayout.itemAt(i).widget()
            chapterData = {}
            jsonData["chapters"].append(chapterData)
            chapterData["title"] = chapter.title.text()
            chapterData["summary"] = chapter.summary.toPlainText()
            chapterData["summaryTokens"] = chapter.summary.tokenCount
            chapterData["scenes"] = []
            for i in range(chapter.scenesLayout.count()):
                scene = chapter.scenesLayout.itemAt(i).widget()
                sceneData = {}
                chapterData["scenes"].append(sceneData)
                sceneData["summary"] = scene.summary.toPlainText()
                sceneData["summaryTokens"] = scene.summary.tokenCount
                sceneData["text"] = scene.text.toPlainText()
                sceneData["textTokens"] = scene.text.tokenCount

        with open(filename + ".json", "w") as f:
            f.write(json.dumps(jsonData))

    def exportStory(self):
        filename = sanitize_filename(self.storytitle.text())
        with open(filename + ".txt", "w") as f:
            f.write(self.storytitle.text())
            f.write("\n\n")
            for i in range(self.chapterLayout.count()):
                chapter = self.chapterLayout.itemAt(i).widget()
                f.write(chapter.title.text())
                f.write("\n")
                f.write("="*len(chapter.title.text()))
                f.write("\n\n")
                for i in range(chapter.scenesLayout.count()):
                    scene = chapter.scenesLayout.itemAt(i).widget()
                    f.write(scene.text.toPlainText())
                    f.write("\n\n")



    def open_story_objects(self):
        dialog = StoryObjectDialog(self)
        dialog.exec_()
        # Story objects are managed within the dialog


# Create and show the form
form = StoryWriter()
form.show()

# Run the main Qt loop
app.exec_()

