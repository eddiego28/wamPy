# subscriber/subGUI.py
import sys, os, json, datetime, logging, asyncio, threading
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
                             QListWidget, QAbstractItemView, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSlot, QMetaObject, Q_ARG
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from common.utils import log_to_file, JsonDetailDialog

class MultiTopicSubscriber(ApplicationSession):
    def __init__(self, config, topics, on_message_callback):
        super().__init__(config)
        self.topics = topics
        self.on_message_callback = on_message_callback
    async def onJoin(self, details):
        print("Conexión establecida en el subscriptor (realm:", self.config.realm, ")")
        for topic in self.topics:
            self.subscribe(self.on_event, topic)
    def on_event(self, *args, **kwargs):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_data = args[0] if args else {}
        message_json = json.dumps(message_data, indent=2, ensure_ascii=False)
        log_to_file(timestamp, "Desconocido", self.config.realm, message_json)
        logging.info(f"Recibido: {timestamp} | Topic: Desconocido | Realm: {self.config.realm}")
        if self.on_message_callback:
            self.on_message_callback(message_data)

def start_subscriber(url, realm, topics, on_message_callback):
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runner = ApplicationRunner(url=url, realm=realm)
        runner.run(lambda config: MultiTopicSubscriber(config, topics, on_message_callback))
    threading.Thread(target=run, daemon=True).start()

class MessageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.initUI()
    def initUI(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Hora", "Topic", "Realm"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.showDetails)
        layout.addWidget(self.table)
        self.setLayout(layout)
    def add_message(self, realm, topic, timestamp, details):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.table.setItem(row, 1, QTableWidgetItem(topic))
        self.table.setItem(row, 2, QTableWidgetItem(realm))
        self.messages.append(details)
    def showDetails(self, item):
        row = item.row()
        if row < len(self.messages):
            dlg = JsonDetailDialog(self.messages[row], self)
            dlg.exec_()

class SubscriberTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.subMessages = []
        self.initUI()
    def initUI(self):
        mainLayout = QHBoxLayout(self)
        configWidget = QWidget()
        configLayout = QVBoxLayout(configWidget)
        connLayout = QHBoxLayout()
        connLayout.addWidget(QLabel("Realm:"))
        self.realmCombo = QComboBox()
        self.realmCombo.addItems(["default"])
        connLayout.addWidget(self.realmCombo)
        connLayout.addWidget(QLabel("Router URL:"))
        self.urlEdit = QLineEdit("ws://127.0.0.1:60001")
        connLayout.addWidget(self.urlEdit)
        configLayout.addLayout(connLayout)
        topicsLayout = QHBoxLayout()
        topicsLayout.addWidget(QLabel("Topics:"))
        self.topicsList = QListWidget()
        self.topicsList.setSelectionMode(QAbstractItemView.MultiSelection)
        topicsLayout.addWidget(self.topicsList)
        btnLayout = QVBoxLayout()
        self.loadTopicsButton = QPushButton("Cargar Topics desde archivo")
        self.loadTopicsButton.clicked.connect(self.loadTopics)
        btnLayout.addWidget(self.loadTopicsButton)
        self.newTopicEdit = QLineEdit()
        self.newTopicEdit.setPlaceholderText("Añadir nuevo topic...")
        btnLayout.addWidget(self.newTopicEdit)
        self.addTopicButton = QPushButton("Agregar")
        self.addTopicButton.clicked.connect(self.addTopic)
        btnLayout.addWidget(self.addTopicButton)
        topicsLayout.addLayout(btnLayout)
        configLayout.addLayout(topicsLayout)
        self.startButton = QPushButton("Iniciar Suscripción")
        self.startButton.clicked.connect(self.startSubscription)
        configLayout.addWidget(self.startButton)
        configLayout.addStretch()
        mainLayout.addWidget(configWidget, 1)
        self.viewer = MessageViewer(self)
        mainLayout.addWidget(self.viewer, 2)
        self.setLayout(mainLayout)
    def loadTopics(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccione JSON de Topics", "", "JSON Files (*.json);;All Files (*)")
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el archivo:\n{e}")
            return
        topics = data if isinstance(data, list) else data.get("topics", [])
        self.topicsList.clear()
        for topic in topics:
            self.topicsList.addItem(topic)
    def addTopic(self):
        new_topic = self.newTopicEdit.text().strip()
        if new_topic:
            self.topicsList.addItem(new_topic)
            self.newTopicEdit.clear()
    def addSubscriberLog(self, realm, topics, timestamp, details):
        self.viewer.add_message(realm, ", ".join(topics), timestamp, details)
    def startSubscription(self):
        from subscriber.subGUI import start_subscriber
        realm = self.realmCombo.currentText()
        url = self.urlEdit.text().strip()
        selected_items = self.topicsList.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, "Error", "Seleccione al menos un topic.")
            return
        topics = [item.text() for item in selected_items]
        start_subscriber(url, realm, topics, on_message_callback=self.onMessageArrived)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.addSubscriberLog(realm, topics, timestamp, {"info": f"Subscriptor iniciado: realm={realm}, topics={topics}"})
    def onMessageArrived(self, content):
        from PyQt5.QtCore import QMetaObject, Q_ARG, Qt
        QMetaObject.invokeMethod(self, "onMessageArrivedMainThread", Qt.QueuedConnection, Q_ARG(dict, content))
    @pyqtSlot(dict)
    def onMessageArrivedMainThread(self, content):
        realm = self.realmCombo.currentText()
        topics = [self.topicsList.item(i).text() for i in range(self.topicsList.count())]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.addSubscriberLog(realm, topics, timestamp, content)
