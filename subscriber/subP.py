# subscriber/subGUI.py

import sys, os, json, datetime, logging, asyncio, threading
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QAbstractItemView, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSlot, QMetaObject, Q_ARG
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

# Asumiendo que en common/utils.py tienes:
# log_to_file(timestamp, topic, realm, message_json)
# y la clase JsonDetailDialog para ver el contenido
from common.utils import log_to_file, JsonDetailDialog

# Variables globales opcionales si quieres mantener referencia de la sesión
global_session_sub = None
global_loop_sub = None

class MultiTopicSubscriber(ApplicationSession):
    def __init__(self, config, topics, on_message_callback):
        super().__init__(config)
        self.topics = topics
        self.on_message_callback = on_message_callback

    async def onJoin(self, details):
        print("Conexión establecida en el subscriptor (realm:", self.config.realm, ")")

        # Función auxiliar para capturar el 'topic' en el callback
        def make_callback(t):
            # Retorna una función lambda que llama a self.on_event con el topic fijado
            return lambda *args, **kwargs: self.on_event(t, *args, **kwargs)

        # Suscribir cada topic con su propio callback
        for topic in self.topics:
            self.subscribe(make_callback(topic), topic)

    def on_event(self, topic, *args, **kwargs):
        """
        Se invoca cada vez que se recibe un mensaje en el 'topic' dado.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extrae el contenido sin forzar un dict con "args"/"kwargs", para evitar que aparezcan "args" y "kwargs" en los logs
        if args and not kwargs:
            content = args[0]
        elif kwargs and not args:
            content = kwargs
        elif args and kwargs:
            # Mezcla ambos
            try:
                content = args[0].copy() if isinstance(args[0], dict) else {}
                content.update(kwargs)
            except Exception:
                content = {"args": args, "kwargs": kwargs}
        else:
            content = {}

        message_json = json.dumps(content, indent=2, ensure_ascii=False)
        log_to_file(timestamp, topic, self.config.realm, message_json)
        logging.info(f"Recibido: {timestamp} | Topic: {topic} | Realm: {self.config.realm}")

        if self.on_message_callback:
            # Llamamos al callback pasando el topic y el contenido
            self.on_message_callback(topic, content)

def start_subscriber(url, realm, topics, on_message_callback):
    """
    Inicia el suscriptor en un hilo separado.
    :param url: la URL WAMP (ej. "ws://127.0.0.1:60001/ws")
    :param realm: el realm a usar
    :param topics: lista de tópicos a suscribir
    :param on_message_callback: función que recibe (topic, content)
    """
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runner = ApplicationRunner(url=url, realm=realm)
        runner.run(lambda config: MultiTopicSubscriber(config, topics, on_message_callback))
    threading.Thread(target=run, daemon=True).start()

class MessageViewer(QWidget):
    """
    Widget que muestra los mensajes recibidos en una tabla.
    """
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
        """
        Agrega una fila a la tabla con realm, topic y timestamp, guardando 'details' en self.messages.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.table.setItem(row, 1, QTableWidgetItem(topic))
        self.table.setItem(row, 2, QTableWidgetItem(realm))
        self.messages.append(details)

    def showDetails(self, item):
        row = item.row()
        if row < len(self.messages):
            # Muestra el JSON en un diálogo
            dlg = JsonDetailDialog(self.messages[row], self)
            dlg.exec_()

class SubscriberTab(QWidget):
    """
    Pestaña que maneja la interfaz del suscriptor: realms, router URL, lista de topics, etc.
    """
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

        self.startButton = QPushButton("Iniciar Suscripción")
        self.startButton.clicked.connect(self.startSubscription)
        configLayout.addWidget(self.startButton)
        configLayout.addStretch()

        mainLayout.addWidget(configWidget, 1)

        self.viewer = MessageViewer(self)
        mainLayout.addWidget(self.viewer, 2)

        self.setLayout(mainLayout)

    def loadTopics(self):
        """
        Carga un archivo JSON que contiene una lista de tópicos (o un dict con 'topics').
        """
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
        """
        Agrega una fila a la tabla de mensajes (un solo topic).
        """
        self.viewer.add_message(realm, topic, timestamp, details)

    def startSubscription(self):
        from subscriber.subGUI import start_subscriber

        realm = self.realmCombo.currentText()
        url = self.urlEdit.text().strip()
        selected_items = self.topicsList.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, "Error", "Seleccione al menos un tópico.")
            return

        # Armamos la lista de topics a suscribir
        topics = [item.text() for item in selected_items]

        # Definimos el callback que recibe (topic, content)
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
        # Registro inicial (opcional)
        self.addSubscriberLog(realm, "Suscripción iniciada", timestamp, {"info": f"Suscriptor iniciado: realm={realm}, topics={topics}"})

    @pyqtSlot(str, dict)
    def onMessageArrivedMainThread(self, topic, content):
        """
        Llega en el hilo principal con un solo topic y el contenido del mensaje.
        """
        realm = self.realmCombo.currentText()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.addSubscriberLog(realm, topic, timestamp, content)
