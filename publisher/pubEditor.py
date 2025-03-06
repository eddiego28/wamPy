# publisher/pubEditor.py
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
                             QTextEdit, QFormLayout, QScrollArea, QFileDialog, QMessageBox, QTabWidget, QTreeWidget, QTreeWidgetItem)
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
        layout = QVBoxLayout()
        
        # Selección de modo (Formulario Dinámico o JSON)
        modeLayout = QHBoxLayout()
        modeLayout.addWidget(QLabel("Editar en:"))
        self.editModeSelector = QComboBox()
        self.editModeSelector.addItems(["Formulario Dinámico", "JSON"])
        modeLayout.addWidget(self.editModeSelector)
        layout.addLayout(modeLayout)
        
        # Botones para cargar y convertir JSON
        self.importButton = QPushButton("Cargar JSON desde Archivo")
        self.importButton.clicked.connect(self.loadJSONFromFile)
        layout.addWidget(self.importButton)
        
        self.convertButton = QPushButton("Convertir a JSON")
        self.convertButton.clicked.connect(self.convertToJSON)
        layout.addWidget(self.convertButton)
        
        # Configuración común de envío
        commonLayout = QHBoxLayout()
        commonLayout.addWidget(QLabel("Modo de envío:"))
        self.commonModeCombo = QComboBox()
        self.commonModeCombo.addItems(["Programado", "Hora de sistema", "On-demand"])
        commonLayout.addWidget(self.commonModeCombo)
        commonLayout.addWidget(QLabel("Tiempo (HH:MM:SS):"))
        self.commonTimeEdit = QLineEdit("00:00:00")
        commonLayout.addWidget(self.commonTimeEdit)
        layout.addLayout(commonLayout)
        
        # Área de previsualización: QTabWidget con dos pestañas (JSON y Árbol)
        self.previewTabWidget = QTabWidget()
        self.jsonPreview = QTextEdit()
        self.jsonPreview.setReadOnly(True)
        self.previewTabWidget.addTab(self.jsonPreview, "JSON")
        self.treePreview = QTreeWidget()
        self.treePreview.setColumnCount(2)
        self.treePreview.setHeaderLabels(["Campo", "Valor"])
        self.previewTabWidget.addTab(self.treePreview, "Árbol")
        layout.addWidget(self.previewTabWidget)
        
        # Widget dinámico para editar el JSON
        from .pubDynamicForm import DynamicPublisherMessageForm
        self.dynamicWidget = DynamicPublisherMessageForm(self)
        layout.addWidget(self.dynamicWidget)
        
        self.setLayout(layout)
        
    def loadJSONFromFile(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccione un archivo JSON", "", "JSON Files (*.json);;All Files (*)")
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.jsonPreview.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
            self.buildTreePreview(data)
            self.dynamicWidget.build_form(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el JSON:\n{e}")
        
    def convertToJSON(self):
        data = self.dynamicWidget.collect_form_data(self.dynamicWidget.formLayout)
        json_text = json.dumps(data, indent=2, ensure_ascii=False)
        self.jsonPreview.setPlainText(json_text)
        self.buildTreePreview(data)
        self.editModeSelector.setCurrentText("JSON")
        
    def buildTreePreview(self, data):
        self.treePreview.clear()
        items = build_tree_items(data)
        self.treePreview.addTopLevelItems(items)
        self.treePreview.expandAll()
