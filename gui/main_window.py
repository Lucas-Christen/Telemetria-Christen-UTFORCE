# gui/main_window.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGridLayout, QTabWidget,
    QLabel, QPushButton, QDialog, QFormLayout, QMessageBox,
    QListWidget, QListWidgetItem, QHBoxLayout, QApplication, QSpinBox, QMenu, QColorDialog, QComboBox
)
from PySide6.QtCore import Qt, QMimeData, QSize, QPoint, Signal
from PySide6.QtGui import QPalette, QColor, QDrag, QCursor, QPixmap, QPainter, QBrush, QAction, QFont
from gui.sensor_selection import SensorSelectionWidget
from gui.comparison_view import ComparisonView
from gui.styles import DARK_THEME, LIGHT_THEME
from gui.setup_view import SetupView
from gui.car_monitoring_view import CarMonitoringView
from pyqtgraph import PlotWidget, mkPen
import pyqtgraph as pg
import json
import os
import time
import math
from data.data_simulator import DataSimulator  # Importar o DataSimulator

# --- Diálogo para configurar gráficos (não grade) ---
class GraphConfigurationDialog(QDialog):
    def __init__(self, graph_widgets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Gráficos")
        self.graph_widgets = graph_widgets

        layout = QVBoxLayout(self)

        # Lista para selecionar um gráfico (seleção única)
        self.graph_list = QListWidget()
        self.graph_list.setSelectionMode(QListWidget.SingleSelection)
        for name in self.graph_widgets.keys():
            item = QListWidgetItem(name)
            self.graph_list.addItem(item)
        layout.addWidget(QLabel("Selecione o gráfico para configurar:"))
        layout.addWidget(self.graph_list)

        # Formulário para configurar as propriedades do gráfico
        form_layout = QFormLayout()

        # Combobox para selecionar o tipo de gráfico
        self.type_combo = QComboBox()
        self.type_combo.addItems(["line", "bar", "radial"])
        form_layout.addRow("Tipo de Gráfico:", self.type_combo)

        # Botão para escolher a cor da linha
        self.line_color_button = QPushButton("Selecionar")
        self.line_color_button.clicked.connect(self.select_line_color)
        form_layout.addRow("Cor da Linha:", self.line_color_button)

        # Botão para escolher a cor de fundo
        self.bg_color_button = QPushButton("Selecionar")
        self.bg_color_button.clicked.connect(self.select_bg_color)
        form_layout.addRow("Cor do Fundo:", self.bg_color_button)

        layout.addLayout(form_layout)

        # Botões OK/Cancelar
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancelar")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Variáveis para armazenar as cores escolhidas
        self.chosen_line_color = None
        self.chosen_bg_color = None

        # Quando o usuário selecionar um gráfico na lista, carregar suas configurações atuais
        self.graph_list.currentTextChanged.connect(self.load_graph_settings)

    def load_graph_settings(self, graph_name):
        widget = self.graph_widgets.get(graph_name)
        if widget:
            self.type_combo.setCurrentText(widget.current_chart_type)
            self.chosen_line_color = widget.line_color
            self.chosen_bg_color = widget.palette().color(widget.backgroundRole()).name()
            self.line_color_button.setStyleSheet(f"background-color: {self.chosen_line_color};")
            self.bg_color_button.setStyleSheet(f"background-color: {self.chosen_bg_color};")

    def select_line_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.chosen_line_color = color.name()
            self.line_color_button.setStyleSheet(f"background-color: {self.chosen_line_color};")

    def select_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.chosen_bg_color = color.name()
            self.bg_color_button.setStyleSheet(f"background-color: {self.chosen_bg_color};")

# --- Diálogo unificado para selecionar cores (usado pelo DraggablePlotWidget) ---
class ColorSelectionDialog(QDialog):
    def __init__(self, current_line_color, current_bg_color, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Cores")

        # Armazena as cores iniciais
        self.line_color = current_line_color
        self.bg_color = current_bg_color

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Botão para selecionar a cor da linha
        self.line_color_button = QPushButton("Selecionar")
        self.line_color_button.setStyleSheet(f"background-color: {self.line_color};")
        self.line_color_button.clicked.connect(self.select_line_color)
        form_layout.addRow("Cor da Linha:", self.line_color_button)

        # Botão para selecionar a cor de fundo
        self.bg_color_button = QPushButton("Selecionar")
        self.bg_color_button.setStyleSheet(f"background-color: {self.bg_color};")
        self.bg_color_button.clicked.connect(self.select_bg_color)
        form_layout.addRow("Cor do Fundo:", self.bg_color_button)

        layout.addLayout(form_layout)

        # Botões OK/Cancelar
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancelar")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def select_line_color(self):
        color = QColorDialog.getColor(QColor(self.line_color), self, "Selecione a Cor da Linha")
        if color.isValid():
            self.line_color = color.name()
            self.line_color_button.setStyleSheet(f"background-color: {self.line_color};")

    def select_bg_color(self):
        color = QColorDialog.getColor(QColor(self.bg_color), self, "Selecione a Cor do Fundo")
        if color.isValid():
            self.bg_color = color.name()
            self.bg_color_button.setStyleSheet(f"background-color: {self.bg_color};")

class DraggablePlotWidget(PlotWidget):
    def __init__(self, title, main_window, parent=None):
        super().__init__(parent=parent)
        self.main_window = main_window  # Referência à MainWindow

        # Inicializa propriedades necessárias
        self.setTitle(title)
        self.setAcceptDrops(True)
        self.drag_start_position = None

        # Atributos para definir o tipo do gráfico e as cores
        self.current_chart_type = "line"  # Tipo padrão
        self.line_color = 'r'             # Cor inicial da linha (vermelho)

        # Arrays de dados
        self.data_x = []
        self.data_y = []

        # Configuração inicial do plot
        self.setBackground('#2E2E2E' if self.main_window.current_theme == "Dark" else '#ffe0e0')
        self.setTitle(title, color=self.line_color, size="16pt", bold=True)
        self.setLabel("left", "Valor", color="w", size="12pt")
        self.setLabel("bottom", "Tempo (s)", color="w", size="12pt")
        
        # Habilitar a grade por padrão com opacidade máxima
        self.showGrid(x=True, y=True, alpha=1.0)

        # Personaliza a fonte dos ticks dos eixos
        left_axis = self.getAxis("left")
        left_axis.tickFont = QFont("Arial", 12)
        bottom_axis = self.getAxis("bottom")
        bottom_axis.tickFont = QFont("Arial", 12)

        self.plot_item = self.plot([], [], pen=mkPen(color=self.line_color, width=2))

        # Desabilita o menu de contexto (não permite alterar propriedades pelo clique)
        self.setContextMenuPolicy(Qt.NoContextMenu)

    def set_chart_type(self, chart_type):
        """
        Define o tipo de gráfico e atualiza a visualização.
        """
        self.current_chart_type = chart_type
        self.update_chart()

    def update_chart(self):
        """
        Redesenha o gráfico de acordo com o tipo selecionado.
        """
        self.clear()
        if self.current_chart_type == "line":
            self.plot(self.data_x, self.data_y, pen=mkPen(color=self.line_color, width=2))
        elif self.current_chart_type == "bar":
            bar_graph = pg.BarGraphItem(x=self.data_x, height=self.data_y, width=0.5, brush='g')
            self.addItem(bar_graph)
        elif self.current_chart_type == "radial":
            radial_plot = pg.PlotCurveItem(
                x=self.data_x,
                y=self.data_y,
                pen=mkPen(color='b', width=2, style=Qt.DashLine),
                name="Radial"
            )
            self.addItem(radial_plot)

    def add_data_point(self, x, y):
        """
        Adiciona um novo ponto de dados e atualiza o gráfico (mantendo somente os 100 últimos pontos).
        """
        self.data_x.append(x)
        self.data_y.append(y)
        if len(self.data_x) > 100:
            self.data_x = self.data_x[-100:]
            self.data_y = self.data_y[-100:]
        self.update_chart()

    # Se desejar manter o suporte a drag-and-drop, mantenha os métodos de mouse e drag
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        distance = (event.position() - self.drag_start_position).manhattanLength()
        if distance < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.objectName())
        drag.setMimeData(mime_data)

        pixmap = self.grab()
        shadow = QPixmap(pixmap.size())
        shadow.fill(Qt.transparent)
        painter = QPainter(shadow)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
        painter.drawRoundedRect(shadow.rect(), 10, 10)
        painter.end()

        combined = QPixmap(pixmap.size())
        combined.fill(Qt.transparent)
        painter = QPainter(combined)
        painter.drawPixmap(10, 10, shadow)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        drag.setPixmap(combined.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.highlight_target(True)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.highlight_target(False)
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            source_sensor = event.mimeData().text()
            target_sensor = self.objectName()
            confirm = QMessageBox.question(
                self,
                "Confirmar Troca",
                f"Deseja trocar o gráfico '{source_sensor}' com o gráfico '{target_sensor}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                self.main_window.swap_plots(source_sensor, target_sensor)
            self.highlight_target(False)
            event.acceptProposedAction()
        else:
            event.ignore()

    def highlight_target(self, highlight):
        palette = self.palette()
        if highlight:
            palette.setColor(QPalette.Window, QColor("#FFDD57"))
            self.setCursor(QCursor(Qt.PointingHandCursor))
        else:
            palette.setColor(QPalette.Window, QColor("#2E2E2E") if self.main_window.current_theme == "Dark" else QColor("#ffe0e0"))
            self.setCursor(QCursor(Qt.ArrowCursor))
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.update()

# --- MainWindow (versão simplificada sem as configurações de grade) ---
class MainWindow(QMainWindow):
    # Definir o sinal theme_changed
    theme_changed = Signal(str)  # Emite o nome do tema atual
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telemetria Utforce")
        self.setGeometry(100, 100, 1600, 900)

        self.current_theme = "Dark"
        self.apply_theme(DARK_THEME)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Botão para configurar gráficos
        self.configure_graph_button = QPushButton("Configurar Gráficos", self)
        self.configure_graph_button.setToolTip("Configurar as propriedades dos gráficos exibidos")
        self.configure_graph_button.clicked.connect(self.open_graph_config_dialog)
        self.configure_graph_button.setStyleSheet("""
            QPushButton {
                color: white;
                border: 2px solid white;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                border: 2px solid #fb0e0e;
            }
        """)
        self.configure_graph_button.setFixedSize(150, 40)
        
        # Botões de tema flutuantes
        self.dark_theme_button = QPushButton("Tema Escuro", self)
        self.light_theme_button = QPushButton("Tema Claro", self)
        
        # Estilizar os botões de tema
        self.dark_theme_button.setStyleSheet("""
            QPushButton {
                background-color: #2E2E2E;
                color: white;
                border: 2px solid white;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                border: 2px solid #fb0e0e;
            }
        """)
        
        self.light_theme_button.setStyleSheet("""
            QPushButton {
                background-color: #ffe0e0;
                color: black;
                border: 2px solid black;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                border: 2px solid #bd0000;
            }
        """)
        
        self.dark_theme_button.setToolTip("Ativar Tema Escuro")
        self.light_theme_button.setToolTip("Ativar Tema Claro")
        
        self.dark_theme_button.clicked.connect(lambda: self.change_theme("Dark"))
        self.light_theme_button.clicked.connect(lambda: self.change_theme("Light"))
        
        # Adicionar os botões de tema como widgets flutuantes
        self.dark_theme_button.setFixedSize(100, 40)
        self.light_theme_button.setFixedSize(100, 40)
        
        # Função para atualizar a posição dos botões quando a janela for redimensionada
        def update_theme_buttons_position():
            # Posicionar os botões lado a lado no canto superior direito
            self.configure_graph_button.move(self.width() - 380, 10)  # Movido mais para a direita
            self.dark_theme_button.move(self.width() - 220, 10)
            self.light_theme_button.move(self.width() - 110, 10)
        
        # Conectar o sinal de redimensionamento
        self.update_theme_buttons_position = update_theme_buttons_position
        
        # Posicionar os botões inicialmente
        update_theme_buttons_position()
        
        # Mostrar os botões
        self.configure_graph_button.show()
        self.dark_theme_button.show()
        self.light_theme_button.show()
        
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.monitoring_page = QWidget()
        self.monitoring_layout = QHBoxLayout()
        self.monitoring_page.setLayout(self.monitoring_layout)
        self.tabs.addTab(self.monitoring_page, "Monitoramento em Tempo Real")

        self.sensor_selection = SensorSelectionWidget()
        self.monitoring_layout.addWidget(self.sensor_selection, stretch=1)

        self.graph_grid_layout = QGridLayout()
        self.graph_grid_widget = QWidget()
        self.graph_grid_widget.setLayout(self.graph_grid_layout)
        self.monitoring_layout.addWidget(self.graph_grid_widget, stretch=4)

        self.graph_widgets = {}
        self.highlighted_positions = set()
        self.selected_sensors = []

        self.sensor_selection.selections_applied.connect(self.setup_graphs)

        self.comparison_page = ComparisonView(self)
        self.tabs.addTab(self.comparison_page, "Comparação de Voltas")

        self.setup_page = SetupView()
        self.tabs.addTab(self.setup_page, "Setup do Carro")

        self.car_monitoring_page = CarMonitoringView()
        self.tabs.addTab(self.car_monitoring_page, "Monitoramento do Carro")

        self.data_simulator = DataSimulator()
        self.data_simulator.data_generated.connect(self.update_graphs_with_data)
        self.data_simulator.start()

        # Conectar o sinal de mudança de tab para mostrar/esconder o botão de configuração
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Inicialmente, mostrar o botão de configuração (assumindo que o primeiro tab é o de monitoramento)
        self.configure_graph_button.setVisible(True)
        
    def open_graph_config_dialog(self):
        dialog = GraphConfigurationDialog(self.graph_widgets, self)
        if dialog.exec() == QDialog.Accepted:
            selected_item = dialog.graph_list.currentItem()
            if selected_item:
                graph_name = selected_item.text()
                widget = self.graph_widgets.get(graph_name)
                if widget:
                    widget.set_chart_type(dialog.type_combo.currentText())
                    if dialog.chosen_line_color:
                        widget.line_color = dialog.chosen_line_color
                    if dialog.chosen_bg_color:
                        widget.setBackground(dialog.chosen_bg_color)
                        widget.bg_color = dialog.chosen_bg_color
                    widget.update_chart()

    def change_theme(self, theme_name):
        """
        Altera o tema da aplicação.
        """
        if theme_name == "Dark":
            self.apply_theme(DARK_THEME)
            self.current_theme = "Dark"
            print("Tema alterado para Escuro")
            
            # Atualizar estilos dos botões para tema escuro
            self.dark_theme_button.setStyleSheet("""
                QPushButton {
                    background-color: #2E2E2E;
                    color: white;
                    border: 2px solid white;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border: 2px solid #fb0e0e;
                }
            """)
            
            self.light_theme_button.setStyleSheet("""
                QPushButton {
                    background-color: #ffe0e0;
                    color: black;
                    border: 2px solid black;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border: 2px solid #bd0000;
                }
            """)
            
            self.configure_graph_button.setStyleSheet("""
                QPushButton {
                    color: white;
                    border: 2px solid white;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border: 2px solid #fb0e0e;
                }
            """)
            
        elif theme_name == "Light":
            self.apply_theme(LIGHT_THEME)
            self.current_theme = "Light"
            print("Tema alterado para Claro")
            
            # Atualizar estilos dos botões para tema claro
            self.dark_theme_button.setStyleSheet("""
                QPushButton {
                    background-color: #2E2E2E;
                    color: white;
                    border: 2px solid white;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border: 2px solid #fb0e0e;
                }
            """)
            
            self.light_theme_button.setStyleSheet("""
                QPushButton {
                    background-color: #ffe0e0;
                    color: black;
                    border: 2px solid black;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border: 2px solid #bd0000;
                }
            """)
            
            self.configure_graph_button.setStyleSheet("""
                QPushButton {
                    color: black;
                    border: 2px solid black;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border: 2px solid #bd0000;
                }
            """)

        # Emit the theme changed signal
        print(f"Emitindo sinal theme_changed com o tema: {self.current_theme}")
        self.theme_changed.emit(self.current_theme)

        # Update graph backgrounds
        for sensor_name, plot in self.graph_widgets.items():
            plot.setBackground('#2E2E2E' if self.current_theme == "Dark" else '#ffe0e0')
            # Atualizar as cores do texto dos gráficos
            text_color = 'white' if self.current_theme == "Dark" else 'black'
            plot.setLabel('left', 'Valor', color=text_color)
            plot.setLabel('bottom', 'Tempo (s)', color=text_color)
            plot.getAxis('left').setTextPen(text_color)
            plot.getAxis('bottom').setTextPen(text_color)
            plot.getAxis('left').setPen(text_color)
            plot.getAxis('bottom').setPen(text_color)
            # Corrigir o erro de title
            current_title = plot.plotItem.titleLabel.text
            plot.setTitle(current_title, color=text_color)

    def apply_theme(self, stylesheet):
        self.setStyleSheet(stylesheet)

    def setup_graphs(self, selected_sensors_list):
        self.selected_sensors = selected_sensors_list
        self.clear_grid_layout()
        self.highlighted_positions.clear()
        self.graph_widgets.clear()

        num_sensors = len(selected_sensors_list)
        if num_sensors == 0:
            return

        rows = math.ceil(math.sqrt(num_sensors))
        cols = math.ceil(num_sensors / rows)
        for index, sensor in enumerate(selected_sensors_list):
            row = index // cols
            col = index % cols
            plot = DraggablePlotWidget(title=sensor, main_window=self, parent=self.graph_grid_widget)
            plot.data_x = []
            plot.data_y = []
            plot.setObjectName(sensor)
            self.graph_grid_layout.addWidget(plot, row, col, 1, 1)
            self.graph_widgets[sensor] = plot

        self.adjust_grid_stretch(rows, cols)
        self.graph_grid_widget.update()
        QMessageBox.information(self, "Configuração Atualizada", "Os gráficos foram configurados com sucesso!")

    def adjust_grid_stretch(self, rows, cols):
        for r in range(self.graph_grid_layout.rowCount()):
            self.graph_grid_layout.setRowStretch(r, 0)
        for c in range(self.graph_grid_layout.columnCount()):
            self.graph_grid_layout.setColumnStretch(c, 0)
        for r in range(rows):
            self.graph_grid_layout.setRowStretch(r, 1)
        for c in range(cols):
            self.graph_grid_layout.setColumnStretch(c, 1)

    def clear_grid_layout(self):
        while self.graph_grid_layout.count():
            item = self.graph_grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.graph_grid_layout.update()

    def update_graphs_with_data(self, sensor_data):
        current_time = time.time()
        for sensor in self.selected_sensors:
            if sensor in sensor_data:
                value = sensor_data[sensor]
                plot = self.graph_widgets.get(sensor)
                if plot:
                    plot.add_data_point(current_time, value)

    def closeEvent(self, event):
        self.data_simulator.stop()
        super().closeEvent(event)

    def swap_plots(self, source_sensor, target_sensor):
        plot_source = self.graph_widgets.get(source_sensor)
        plot_target = self.graph_widgets.get(target_sensor)
        if plot_source and plot_target:
            pos_source = self.graph_grid_layout.getItemPosition(self.graph_grid_layout.indexOf(plot_source))
            pos_target = self.graph_grid_layout.getItemPosition(self.graph_grid_layout.indexOf(plot_target))
            self.graph_grid_layout.addWidget(plot_target, pos_source[0], pos_source[1], pos_source[2], pos_source[3])
            self.graph_grid_layout.addWidget(plot_source, pos_target[0], pos_target[1], pos_target[2], pos_target[3])
            self.graph_widgets[source_sensor], self.graph_widgets[target_sensor] = plot_target, plot_source
            print(f"Troca realizada: Gráfico '{source_sensor}' ↔ Gráfico '{target_sensor}'")

    def on_tab_changed(self, index):
        """
        Método chamado quando o usuário muda de tab.
        Mostra/esconde os botões apropriados dependendo da página atual.
        """
        # O primeiro tab (índice 0) é o de monitoramento
        self.configure_graph_button.setVisible(index == 0)
        
        # Mantém os botões de tema sempre visíveis
        self.dark_theme_button.setVisible(True)
        self.light_theme_button.setVisible(True)

    def resizeEvent(self, event):
        """Método para lidar com o evento de redimensionamento da janela"""
        super().resizeEvent(event)
        if hasattr(self, 'update_theme_buttons_position'):
            self.update_theme_buttons_position()
