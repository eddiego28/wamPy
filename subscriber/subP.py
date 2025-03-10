# subscriber/subGUI.py
import sys, os, json, datetime, logging, asyncio, threading
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QAbstractItemView, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSlot, QMetaObject, Q_ARG
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from common.utils import log_to_file, JsonDetailDialog

# Variables globales para almacenar la sesión del suscriptor
global_session_sub = None
global_loop_sub = None

class MultiTopicSubscriber(ApplicationSession):
    def __init__(self, config, topics, on_message_callback):
        super().__init__(config)
        self.topics = topics
        self.on_message_callback = on_message_callback

    async def onJoin(self, details):
        global global_session_sub, global_loop_sub
        global_session_sub = self
        global_loop_sub = asyncio.get_event_loop()
        print("Conexión establecida en el subscriptor (realm:", self.config.realm, ")")
        # Función auxiliar para capturar el 'topic'
        def make_callback(t):
            return lambda *args, **kwargs: self.on_event(t, *args, **kwargs)
        for topic in self.topics:
            self.subscribe(make_callback(topic), topic)

    def on_event(self, topic, *args, **kwargs):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Recibe el mensaje sin procesar: se construye un diccionario con las claves "args" y "kwargs"
        message_data = {"args": args, "kwargs": kwargs}
        message_json = json.dumps(message_data, indent=2, ensure_ascii=False)
        log_to_file(timestamp, topic, self.config.realm, message_json)
        logging.info(f"Recibido: {timestamp} | Topic: {topic} | Realm: {self.config.realm}")
        if self.on_message_callback:
            self.on_message_callback(topic, message_data)

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
        self.realmCombo.addItems(["default", "ADS.MIDSHMI"])
        connLayout.addWidget(self.realmCombo)
        connLayout.addWidget(QLabel("Router URL:"))
        self.urlEdit = QLineEdit("ws://127.0.0.1:60001/ws")
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
        self.newTopicEdit.setPlaceholderText("Añadir nuevo tópico...")
        btnLayout.addWidget(self.newTopicEdit)
        self.addTopicButton = QPushButton("Agregar")
        self.addTopicButton.clicked.connect(self.addTopic)
        btnLayout.addWidget(self.addTopicButton)
        topicsLayout.addLayout(btnLayout)
        configLayout.addLayout(topicsLayout)

        # Agregamos botones para iniciar, pausar y resetear la suscripción
        btnSubLayout = QHBoxLayout()
        self.startButton = QPushButton("Iniciar Suscripción")
        self.startButton.clicked.connect(self.startSubscription)
        btnSubLayout.addWidget(self.startButton)
        self.pauseButton = QPushButton("Pausar Suscripción")
        self.pauseButton.clicked.connect(self.pauseSubscription)
        btnSubLayout.addWidget(self.pauseButton)
        self.resetLogButton = QPushButton("Resetear Log")
        self.resetLogButton.clicked.connect(self.resetLog)
        btnSubLayout.addWidget(self.resetLogButton)
        configLayout.addLayout(btnSubLayout)
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

    def addSubscriberLog(self, realm, topic, timestamp, details):
        self.viewer.add_message(realm, topic, timestamp, details)

    def startSubscription(self):
        from subscriber.subGUI import start_subscriber
        realm = self.realmCombo.currentText()
        url = self.urlEdit.text().strip()
        selected_items = self.topicsList.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, "Error", "Seleccione al menos un tópico.")
            return
        topics = [item.text() for item in selected_items]

        def on_message_callback(topic, content):
            QMetaObject.invokeMethod(
                self,
                "onMessageArrivedMainThread",
                Qt.QueuedConnection,
                Q_ARG(str, topic),
                Q_ARG(dict, content)
            )

        start_subscriber(url, realm, topics, on_message_callback=on_message_callback)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.addSubscriberLog(realm, "Suscripción iniciada", timestamp, {"info": f"Suscriptor iniciado: realm={realm}, topics={topics}"})

    @pyqtSlot(str, dict)
    def onMessageArrivedMainThread(self, topic, content):
        realm = self.realmCombo.currentText()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.addSubscriberLog(realm, topic, timestamp, content)

    def pauseSubscription(self):
        # Si existe una sesión activa en el suscriptor, se intenta dejarla
        global global_session_sub, global_loop_sub
        if global_session_sub is not None:
            try:
                global_session_sub.leave()
                print("Suscripción pausada.")
            except Exception as e:
                print("Error al pausar la suscripción:", e)
            global_session_sub = None
            global_loop_sub = None
        else:
            QMessageBox.information(self, "Información", "No hay una suscripción activa.")

    def resetLog(self):
        # Limpia la tabla de logs del suscriptor
        self.viewer.table.setRowCount(0)
        self.viewer.messages = []
