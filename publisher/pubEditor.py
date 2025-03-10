# publisher/pubEditor.py

import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

def build_tree_items(data):
    """
    Construye recursivamente una lista de QTreeWidgetItem a partir de un diccionario o lista.
    Cada item muestra la clave en la primera columna y, si es un valor simple, lo muestra en la segunda.
    """
    items = []
    if isinstance(data, dict):
        for key, value in data.items():
            item = QTreeWidgetItem([str(key), ""])
            if isinstance(value, (dict, list)):
                children = build_tree_items(value)
                item.addChildren(children)
            else:
                item.setText(1, str(value))
            items.append(item)
    elif isinstance(data, list):
        for i, value in enumerate(data):
            item = QTreeWidgetItem([f"[{i}]", ""])
            if isinstance(value, (dict, list)):
                children = build_tree_items(value)
                item.addChildren(children)
            else:
                item.setText(1, str(value))
            items.append(item)
    else:
        items.append(QTreeWidgetItem([str(data), ""]))
    return items

class PublisherEditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        mainLayout = QVBoxLayout()

        # Botones para cargar y convertir JSON
        btnLayout = QHBoxLayout()
        self.importButton = QPushButton("Cargar JSON desde Archivo")
        self.importButton.clicked.connect(self.loadJSONFromFile)
        btnLayout.addWidget(self.importButton)
        
        self.convertButton = QPushButton("Actualizar Vista Árbol")
        self.convertButton.clicked.connect(self.convertToTree)
        btnLayout.addWidget(self.convertButton)
        mainLayout.addLayout(btnLayout)

        # Configuración común de envío (puedes dejarlo, o quitar si no es necesario en el editor)
        commonLayout = QHBoxLayout()
        commonLayout.addWidget(QLabel("Tiempo (HH:MM:SS):"))
        self.commonTimeEdit = QLineEdit("00:00:00")
        commonLayout.addWidget(self.commonTimeEdit)
        mainLayout.addLayout(commonLayout)

        # QTabWidget con dos pestañas fijas: "JSON" y "Árbol"
        self.previewTabWidget = QTabWidget()
        self.previewTabWidget.setMinimumHeight(400)

        # Pestaña "JSON": editor de texto para el JSON
        self.jsonPreview = QTextEdit()
        self.jsonPreview.setReadOnly(False)
        self.previewTabWidget.addTab(self.jsonPreview, "JSON")

        # Pestaña "Árbol": vista jerárquica del JSON
        self.treePreview = QTreeWidget()
        self.treePreview.setColumnCount(2)
        self.treePreview.setHeaderLabels(["Clave", "Valor"])
        self.previewTabWidget.addTab(self.treePreview, "Árbol")

        mainLayout.addWidget(self.previewTabWidget)

        self.setLayout(mainLayout)

    def loadJSONFromFile(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccione un archivo JSON", "", "JSON Files (*.json);;All Files (*)")
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Actualiza el editor de texto en la pestaña JSON
            self.jsonPreview.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
            # Actualiza la vista en árbol
            self.buildTreePreview(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el JSON:\n{e}")

    def convertToTree(self):
        """
        Convierte el contenido actual del editor de texto (JSON) en la vista de árbol.
        """
        try:
            data = json.loads(self.jsonPreview.toPlainText())
            self.buildTreePreview(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al convertir a árbol:\n{e}")

    def buildTreePreview(self, data):
        self.treePreview.clear()
        items = build_tree_items(data)
        self.treePreview.addTopLevelItems(items)
        self.treePreview.expandAll()
