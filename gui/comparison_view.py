# gui/comparison_view.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy,
    QGroupBox, QColorDialog, QMessageBox, QGridLayout, QCheckBox, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from pyqtgraph import PlotWidget, mkPen
import pyqtgraph as pg
import random
import numpy as np
import os
import json
from datetime import datetime

from gui.sensor_selection import SensorSelectionWidget
from gui.flow_layout import FlowLayout
from gui.styles import DARK_THEME, LIGHT_THEME

class PlotMixin:
    def get_y_at_x(self, curve, x):
        """
        Retorna o valor y correspondente ao ponto x na curva, interpolando se necessário.
        """
        x_data = curve.x_data
        y_data = curve.y_data
        if x < x_data[0] or x > x_data[-1]:
            return None  # Fora do intervalo de dados

        # Encontrar o índice i tal que x_data[i] <= x <= x_data[i+1]
        for i in range(len(x_data) - 1):
            if x_data[i] <= x <= x_data[i + 1]:
                x0, y0 = x_data[i], y_data[i]
                x1, y1 = x_data[i + 1], y_data[i + 1]
                if x1 - x0 == 0:
                    return y0  # Evitar divisão por zero
                # Interpolação linear
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return None

    def on_mouse_moved(self, pos):
        """
        Atualiza as legendas com os valores correspondentes ao ponto x atual do mouse.
        """
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mouse_point.x()

            # Mover a linha vertical para a posição x atual
            self.vLine.setPos(x)

            # Iterar sobre todas as curvas para atualizar as legendas
            for (lap, sensor), curve in self.curves.items():
                y = self.get_y_at_x(curve, x)
                if y is not None:
                    self.legend_labels[(lap, sensor)].setText(f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: {x:.3f} - Valor: {y:.2f}")
                else:
                    self.legend_labels[(lap, sensor)].setText(f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: N/A - Valor: N/A")
        else:
            # Resetar a linha vertical e todas as legendas
            self.vLine.setPos(None)
            for (lap, sensor), label in self.legend_labels.items():
                label.setText(f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: N/A - Valor: N/A")


class FullscreenPlotWindow(QWidget, PlotMixin):
    def __init__(self, curves, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comparação de Voltas - Tela Cheia")
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.showFullScreen()

        # Store reference to parent and main window
        self.parent_widget = parent
        self.main_window = parent.main_window if parent and hasattr(parent, 'main_window') else None

        # Layout principal
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # PlotWidget para tela cheia
        self.plot_widget = PlotWidget(title="Comparação de Voltas - Tela Cheia")
        self.plot_widget.setBackground('#ffe6e6')  # Cor inicial clara para o fundo do gráfico
        self.plot_widget.setLabel('left', 'Valor', color='black')
        self.plot_widget.setLabel('bottom', 'Tempo (s)', color='black')
        self.plot_widget.getAxis('left').setTextPen('black')
        self.plot_widget.getAxis('bottom').setTextPen('black')
        self.plot_widget.getAxis('left').setPen('black')
        self.plot_widget.getAxis('bottom').setPen('black')
        self.plot_widget.setTitle("Comparação de Voltas - Tela Cheia", color='black')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setMouseEnabled(x=True, y=True)

        main_layout.addWidget(self.plot_widget, stretch=5)

        # Botão para sair da tela cheia
        exit_fullscreen_button = QPushButton("Sair da Tela Cheia")
        exit_fullscreen_button.setFixedWidth(150)
        exit_fullscreen_button.clicked.connect(self.close)
        main_layout.addWidget(exit_fullscreen_button, alignment=Qt.AlignRight)

        # Caixa de legenda compacta com FlowLayout
        self.legend_box = QGroupBox("Legenda das Linhas")
        self.legend_layout = FlowLayout()
        self.legend_box.setLayout(self.legend_layout)
        self.legend_box.setStyleSheet("font-size: 10px;")
        main_layout.addWidget(self.legend_box, stretch=1)

        # Adicionando linha vertical para tooltips
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', width=1))  # Linha branca
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)

        # Mapeamento de curvas para legendas
        self.legend_labels = {}  # {(lap, sensor): QLabel}

        # Plotar as curvas no PlotWidget de tela cheia
        self.curves = {}
        for (lap, sensor), curve in curves.items():
            time_data = curve.xData
            value_data = curve.yData
            color = curve.opts['pen'].color()
            pen = mkPen(color=color, width=2)
            new_curve = self.plot_widget.plot(
                name=f"{lap} - {sensor.replace('_', ' ').title()}",
                symbol='o', symbolSize=5, symbolBrush=color
            )
            new_curve.setData(time_data, value_data, pen=pen)
            self.curves[(lap, sensor)] = new_curve

            # Adicionar legenda compacta
            label = QLabel(f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: N/A - Valor: N/A")
            label.setStyleSheet("font-size: 10px; font-weight: bold; color: black;")
            self.legend_layout.addWidget(label)
            self.legend_labels[(lap, sensor)] = label

        # Depuração: Verificar quantas curvas foram plotadas
        print(f"FullscreenPlotWindow: {len(self.curves)} curvas plotadas.")

        # Conectar o sinal de movimento do mouse
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)

    def change_background_color(self):
        """
        Abre um diálogo de seleção de cor e atualiza a cor de fundo do gráfico.
        """
        print("Abrindo diálogo de seleção de cor")
        
        # Obter a cor atual do fundo
        if self.plot_widget is not None:
            # Tentar obter a cor atual do fundo
            try:
                # Verificar se temos uma cor personalizada definida
                if hasattr(self, 'custom_bg_color') and self.custom_bg_color is not None:
                    current_color = QColor(self.custom_bg_color)
                else:
                    # Usar a cor padrão com base no tema atual
                    current_color = QColor('#212121')  # Dark theme default
            except Exception as e:
                print(f"Erro ao obter cor de fundo: {e}")
                current_color = QColor('#212121')  # Fallback para tema escuro
        else:
            current_color = QColor('#212121')
        
        # Criar um diálogo personalizado com botões de seleção de cor e reset
        dialog = QDialog(self)
        dialog.setWindowTitle("Selecionar Cor de Fundo")
        dialog.setModal(True)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        
        # Criar o color dialog padrão
        color_dialog = QColorDialog(dialog)
        color_dialog.setCurrentColor(current_color)
        color_dialog.setOption(QColorDialog.DontUseNativeDialog, True)
        
        # Adicionar o color dialog ao layout
        layout.addWidget(color_dialog)
        
        # Layout para botões
        button_layout = QHBoxLayout()
        
        # Botão de reset
        reset_button = QPushButton("Reset para Tema Original", dialog)
        reset_button.clicked.connect(lambda: self.reset_background_color(dialog))
        button_layout.addWidget(reset_button)
        
        # Botões de OK e Cancelar
        ok_button = QPushButton("OK", dialog)
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancelar", dialog)
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        # Adicionar o layout de botões ao layout principal
        layout.addLayout(button_layout)
        
        # Mostrar o diálogo
        if dialog.exec_() == QDialog.Accepted:
            # Obter a cor selecionada
            selected_color = color_dialog.selectedColor()
            
            # Armazenar a cor personalizada
            self.custom_bg_color = selected_color.name()
            
            # Atualizar a cor de fundo do gráfico
            if self.plot_widget is not None:
                self.plot_widget.setBackground(selected_color)
            
            # Determinar a cor do texto com base no brilho da cor de fundo
            brightness = (selected_color.red() * 299 + selected_color.green() * 587 + selected_color.blue() * 114) / 1000
            text_color = 'white' if brightness < 128 else 'black'
            
            # Atualizar as cores do texto
            self.update_text_colors(text_color)
            
            # Se estiver em tela cheia, atualizar também o gráfico da janela de tela cheia
            if hasattr(self, 'fullscreen_window') and self.fullscreen_window is not None:
                self.fullscreen_window.plot_widget.setBackground(selected_color)
                self.fullscreen_window.update_text_colors(text_color)
            
            print(f"Cor de fundo alterada para: {selected_color.name()}")
            print(f"Cor do texto ajustada para: {text_color}")
    
    def reset_background_color(self, dialog=None):
        """
        Reseta a cor de fundo para a cor original do tema atual.
        """
        print("Resetando cor de fundo para o tema original")
        
        # Limpar a cor personalizada
        self.custom_bg_color = None
        
        # Determinar o tema atual
        if self.main_window and hasattr(self.main_window, 'current_theme'):
            is_dark = self.main_window.current_theme == "Dark"
        else:
            # Se não tiver acesso à janela principal, usar o tema do widget pai
            is_dark = self.parent_widget.is_dark if hasattr(self.parent_widget, 'is_dark') else True
        
        # Definir a cor de fundo com base no tema
        if is_dark:
            bg_color = QColor('#212121')  # Dark theme background
            text_color = '#FFFFFF'  # Dark theme text
        else:
            bg_color = QColor('#ffe6e6')  # Light theme background
            text_color = '#000000'  # Light theme text
        
        # Atualizar a cor de fundo do gráfico
        if self.plot_widget is not None:
            self.plot_widget.setBackground(bg_color)
        
        # Atualizar as cores do texto
        self.update_text_colors(text_color)
        
        print(f"Cor de fundo resetada para: {bg_color.name()}")
        print(f"Cor do texto ajustada para: {text_color}")
        
        # Se o diálogo foi fornecido, fechá-lo
        if dialog:
            dialog.accept()

    def update_text_colors(self, text_color):
        """
        Atualiza as cores do texto no gráfico e elementos da interface.
        """
        print(f"Atualizando cores do texto para: {text_color}")
        
        # Atualiza as cores dos eixos
        self.plot_widget.setLabel('left', 'Valor', color=text_color)
        self.plot_widget.setLabel('bottom', 'Tempo (s)', color=text_color)
        self.plot_widget.getAxis('left').setTextPen(text_color)
        self.plot_widget.getAxis('bottom').setTextPen(text_color)
        self.plot_widget.getAxis('left').setPen(text_color)
        self.plot_widget.getAxis('bottom').setPen(text_color)
        
        # Atualiza a linha vertical se existir e estiver inicializada
        if hasattr(self, 'vLine') and self.vLine is not None:
            try:
                self.vLine.setPen(pg.mkPen(text_color, width=1))
            except RuntimeError:
                print("Aviso: vLine ainda não está pronta para atualização")
        
        # Atualiza a grade
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Atualiza o título se existir
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {text_color};")
        
        # Atualiza as cores das curvas se existirem
        if hasattr(self, 'curves') and self.curves:
            for curve in self.curves.values():
                curve.setPen(text_color)
        
        # Atualiza a legenda se existir
        if hasattr(self, 'legend'):
            self.legend.setLabelTextColor(text_color)
        
        # Atualiza as cores dos labels da legenda
        for label in self.legend_labels.values():
            label.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {text_color};")
        
        print("Cores do texto atualizadas com sucesso")

    def on_theme_changed(self, is_dark):
        """
        Atualiza as cores do gráfico quando o tema é alterado.
        """
        print(f"Tema alterado para: {'Escuro' if is_dark else 'Claro'}")
        
        # Definir as cores com base no tema
        if is_dark:
            bg_color = '#212121'  # Dark theme background from styles.py
            text_color = '#FFFFFF'  # Dark theme text from styles.py
            theme_name = "Dark"
            button_bg = '#fb0e0e'  # Dark theme button color from styles.py
            button_hover = '#ff0000'
            widget_bg = '#333333'  # Dark widget background
            border_color = '#fb0e0e'  # Dark border color
        else:
            bg_color = '#ffe6e6'  # Light theme background from styles.py
            text_color = '#000000'  # Light theme text from styles.py
            theme_name = "Light"
            button_bg = '#bd0000'  # Light theme button color from styles.py
            button_hover = '#ff0000'
            widget_bg = '#ffcccc'  # Light widget background
            border_color = '#bd0000'  # Light border color
        
        # Atualizar a cor de fundo do gráfico
        if self.plot_widget is not None:
            self.plot_widget.setBackground(bg_color)
        
        # Atualizar o botão de fundo para refletir a cor atual
        if hasattr(self, 'bg_color_button'):
            self.bg_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {button_bg};
                    color: {text_color};
                    border: 2px solid {text_color};
                    border-radius: 4px;
                    padding: 5px;
                    font-family: Arial;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {button_hover};
                }}
            """)
        
        # Atualizar as cores do texto
        if self.plot_widget is not None:
            self.update_text_colors(text_color)
        
        # Atualizar o estilo dos botões
        self.update_button_styles(is_dark)
        
        # Se estiver em tela cheia, atualizar também o gráfico da janela de tela cheia
        if hasattr(self, 'fullscreen_window') and self.fullscreen_window is not None:
            self.fullscreen_window.plot_widget.setBackground(bg_color)
            self.fullscreen_window.update_text_colors(text_color)
            self.fullscreen_window.on_theme_changed(is_dark)
        
        # Atualizar a grade do gráfico
        if self.plot_widget is not None:
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Atualizar a linha vertical
        if hasattr(self, 'vLine') and self.plot_widget is not None:
            self.vLine.setPen(pg.mkPen(text_color, width=1))
        
        # Atualizar as cores dos eixos e título
        if self.plot_widget is not None:
            self.plot_widget.setLabel('left', 'Valor', color=text_color)
            self.plot_widget.setLabel('bottom', 'Tempo (s)', color=text_color)
            self.plot_widget.getAxis('left').setTextPen(text_color)
            self.plot_widget.getAxis('bottom').setTextPen(text_color)
            self.plot_widget.getAxis('left').setPen(text_color)
            self.plot_widget.getAxis('bottom').setPen(text_color)
            self.plot_widget.setTitle("Comparação de Voltas", color=text_color)
        
        print(f"Tema alterado para: {theme_name}")
        print(f"Cor de fundo: {bg_color}")
        print(f"Cor do texto: {text_color}")
        
        # Força a atualização do widget
        self.plot_widget.update()
        if hasattr(self, 'fullscreen_window') and self.fullscreen_window is not None:
            self.fullscreen_window.plot_widget.update()

    def update_button_styles(self, is_dark):
        """
        Atualiza os estilos dos botões com base no tema.
        """
        print(f"Atualizando estilos dos botões para tema {'escuro' if is_dark else 'claro'}")
        
        # Definir cores com base no tema
        if is_dark:
            bg_color = '#212121'  # Dark theme background
            text_color = '#FFFFFF'  # Dark theme text
            button_bg = '#fb0e0e'  # Dark theme button background
            button_hover = '#ff0000'  # Dark theme button hover
            border_color = '#FFFFFF'  # Dark theme border
        else:
            bg_color = '#ffe6e6'  # Light theme background
            text_color = '#000000'  # Light theme text
            button_bg = '#bd0000'  # Light theme button background
            button_hover = '#ff0000'  # Light theme button hover
            border_color = '#000000'  # Light theme border
        
        # Estilo base para botões
        base_button_style = f"""
            QPushButton {{
                background-color: {button_bg};
                color: {text_color if is_dark else '#FFFFFF'};
                border: 2px solid {border_color};
                border-radius: 4px;
                padding: 5px;
                font-family: Arial;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:disabled {{
                background-color: {'#4A4A4A' if is_dark else '#ffb8b8'};
                color: {'#808080' if is_dark else '#666666'};
                border: 2px solid {'#808080' if is_dark else '#666666'};
            }}
        """
        
        # Aplicar estilo aos botões
        for button in self.findChildren(QPushButton):
            button.setStyleSheet(base_button_style)
        
        # Estilo para checkboxes
        checkbox_style = f"""
            QCheckBox {{
                color: {text_color};
                font-family: Arial;
                font-size: 14px;
            }}
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                background-color: {'#4A4A4A' if is_dark else '#ffcccc'};
                border: 1px solid {button_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {button_bg};
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {button_hover};
            }}
        """
        
        # Aplicar estilo aos checkboxes
        for checkbox in self.findChildren(QCheckBox):
            checkbox.setStyleSheet(checkbox_style)
        
        print("Estilos dos botões atualizados com sucesso")


class ComparisonView(QWidget, PlotMixin):
    def __init__(self, main_window=None):
        super().__init__()
        
        # Inicialização de dados
        self.lap_data = {}
        self.curves = {}
        self.selected_sensors = []
        self.selected_laps = []
        self.legend_labels = {}
        self.color_buttons = {}
        self.lap_checkboxes = {}  # Movido para o início
        self.is_fullscreen = False
        self.fullscreen_window = None
        
        # Store reference to main window
        self.main_window = main_window
        
        # Flag to track if a custom background color has been set
        self.custom_bg_color = None

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Layout para seleção de sensores (esquerda) - Reduzido para 20% da largura
        left_panel = QWidget()
        left_panel.setFixedWidth(200)  # Largura fixa para o painel esquerdo
        left_layout = QVBoxLayout(left_panel)
        self.sensor_selection = SensorSelectionWidget()
        left_layout.addWidget(self.sensor_selection)
        main_layout.addWidget(left_panel)

        # Layout para seleção de voltas e gráfico (direita) - 80% da largura
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_layout.addWidget(right_panel, stretch=4)

        # Seção de seleção de voltas (topo) - Reduzida para 15% da altura
        selection_box = QGroupBox("Selecione as Voltas para Comparar")
        selection_layout = QVBoxLayout(selection_box)
        
        # Grid de checkboxes para voltas
        lap_grid = QWidget()
        lap_grid_layout = QGridLayout(lap_grid)
        lap_grid_layout.setSpacing(5)  # Reduzir espaçamento entre checkboxes

        # Adicionar voltas simuladas com caixas de seleção
        max_columns = 10
        for i in range(1, 21):
            checkbox = QCheckBox(f"{i}")
            row = (i - 1) // max_columns
            col = (i - 1) % max_columns
            lap_grid_layout.addWidget(checkbox, row, col)
            self.lap_checkboxes[f"Volta {i}"] = checkbox

        selection_layout.addWidget(lap_grid)
        right_layout.addWidget(selection_box)

        # Área de gráficos (meio) - 70% da altura
        graph_box = QGroupBox("Gráfico de Comparação")
        graph_layout = QVBoxLayout(graph_box)
        
        self.plot_widget = PlotWidget(title="Comparação de Voltas")
        self.plot_widget.setBackground('#2E2E2E')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Valor')
        self.plot_widget.setLabel('bottom', 'Tempo (s)')
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # Adicionar linha vertical para tooltips
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', width=1))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)

        graph_layout.addWidget(self.plot_widget)
        right_layout.addWidget(graph_box, stretch=4)

        # Área de legendas (base) - 15% da altura
        self.legend_box = QGroupBox("Legenda das Linhas")
        self.legend_layout = FlowLayout()
        self.legend_layout.setSpacing(5)  # Reduzir espaçamento entre itens
        self.legend_box.setLayout(self.legend_layout)
        right_layout.addWidget(self.legend_box)

        # Botões de controle (abaixo da legenda)
        button_layout = QHBoxLayout()
        self.compare_button = QPushButton("Comparar Voltas")
        
        button_layout.addWidget(self.compare_button)
        right_layout.addLayout(button_layout)

        # Conectar sinais
        self.compare_button.clicked.connect(self.compare_laps)
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)
        self.sensor_selection.selections_applied.connect(self.update_selected_sensors)

        # Desabilitar botão inicialmente
        self.compare_button.setEnabled(False)

        # Connect to the main window's theme change signal after UI is setup
        if self.main_window and hasattr(self.main_window, 'theme_changed'):
            print("Conectando ao sinal theme_changed da janela principal")
            self.main_window.theme_changed.connect(self.on_main_theme_changed)
            
            # Set initial theme based on main window's current theme
            if hasattr(self.main_window, 'current_theme'):
                print(f"Definindo tema inicial: {self.main_window.current_theme}")
                self.on_main_theme_changed(self.main_window.current_theme)
            else:
                print("Tema inicial não encontrado, usando tema escuro como padrão")
                self.on_main_theme_changed("Dark")
        else:
            print("Janela principal não fornecida ou sinal theme_changed não encontrado")
            # Set default theme
            self.on_theme_changed(True)  # Default to dark theme

    def on_mouse_moved(self, pos):
        """
        Atualiza as legendas com os valores correspondentes ao ponto x atual do mouse.
        """
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mouse_point.x()

            # Mover a linha vertical para a posição x atual
            self.vLine.setPos(x)

            # Iterar sobre todas as curvas para atualizar as legendas
            for (lap, sensor), curve in self.curves.items():
                y = self.get_y_at_x(curve, x)
                if y is not None:
                    self.legend_labels[(lap, sensor)].setText(f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: {x:.3f} - Valor: {y:.2f}")
                else:
                    self.legend_labels[(lap, sensor)].setText(f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: N/A - Valor: N/A")
        else:
            # Resetar a linha vertical e todas as legendas
            self.vLine.setPos(None)
            for (lap, sensor), label in self.legend_labels.items():
                label.setText(f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: N/A - Valor: N/A")

    def on_sensor_selection_changed(self, selected_sensors):
        """
        Called when sensor selection changes.
        """
        self.selected_sensors = selected_sensors
        print("Sensores Selecionados na Comparação:", self.selected_sensors)
        
        # Verificar se há sensores selecionados e voltas selecionadas para habilitar o botão de geração
        self.update_generate_button_state()
        
        # Atualizar o título do gráfico
        if len(self.selected_sensors) > 0:
            self.plot_widget.setTitle("Selecione voltas para gerar o gráfico", color=self.plot_widget.getAxis('left').textPen().color())
        else:
            self.plot_widget.setTitle("Selecione sensores para comparar voltas", color=self.plot_widget.getAxis('left').textPen().color())

    def update_selected_sensors(self, selected_sensors):
        """
        Atualiza a lista de sensores selecionados e atualiza o estado do botão de geração.
        """
        self.selected_sensors = selected_sensors
        print("Sensores Selecionados na Comparação:", self.selected_sensors)
        self.update_generate_button_state()

    def update_generate_button_state(self):
        """
        Atualiza o estado do botão de geração de gráfico com base nas seleções.
        """
        # Verificar se há sensores selecionados
        has_sensors = len(self.selected_sensors) > 0
        
        # Verificar se há voltas selecionadas
        selected_laps = [lap for lap, checkbox in self.lap_checkboxes.items() if checkbox.isChecked()]
        has_laps = len(selected_laps) > 0
        
        # Habilitar o botão apenas se houver sensores e voltas selecionados
        self.compare_button.setEnabled(has_sensors and has_laps)
        
        # Atualizar o título do gráfico
        if has_sensors and has_laps:
            self.plot_widget.setTitle("Clique em 'Gerar Gráfico' para visualizar a comparação", color=self.plot_widget.getAxis('left').textPen().color())
        elif has_sensors:
            self.plot_widget.setTitle("Selecione voltas para gerar o gráfico", color=self.plot_widget.getAxis('left').textPen().color())
        elif has_laps:
            self.plot_widget.setTitle("Selecione sensores para gerar o gráfico", color=self.plot_widget.getAxis('left').textPen().color())
        else:
            self.plot_widget.setTitle("Selecione sensores e voltas para gerar o gráfico", color=self.plot_widget.getAxis('left').textPen().color())
    
    def generate_graph(self):
        """
        Gera o gráfico com base nos sensores e voltas selecionados.
        """
        if not self.selected_sensors:
            print("Nenhum sensor selecionado para comparação.")
            QMessageBox.warning(self, "Nenhum Sensor Selecionado", "Por favor, selecione pelo menos um sensor para comparar.")
            return

        # Coletar voltas selecionadas
        self.selected_laps = [lap for lap, checkbox in self.lap_checkboxes.items() if checkbox.isChecked()]
        print("Voltas Selecionadas para Comparar:", self.selected_laps)

        if not self.selected_laps:
            print("Nenhuma volta selecionada para comparação.")
            QMessageBox.warning(self, "Nenhuma Volta Selecionada", "Por favor, selecione pelo menos uma volta para comparar.")
            return

        # Limpar gráficos anteriores
        self.plot_widget.clear()
        self.curves = {}
        print("Gráficos anteriores limpos.")

        # Readicionar a linha vertical e tooltips
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        print("Linha vertical adicionada novamente.")

        # Limpar legend_box
        for i in reversed(range(self.legend_layout.count())):
            widget_to_remove = self.legend_layout.itemAt(i).widget()
            self.legend_layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
        self.legend_labels.clear()
        self.color_buttons.clear()

        # Plotar dados simulados para cada volta e sensor selecionados
        for lap in self.selected_laps:
            for sensor in self.selected_sensors:
                if (lap, sensor) not in self.lap_data:
                    # Simular dados para a volta e sensor
                    time_data = list(range(60))
                    value_data = [random.uniform(150, 200) for _ in time_data]
                    self.lap_data[(lap, sensor)] = (time_data, value_data)
                    print(f"Simulando dados para {lap} - {sensor}")

                time_data, value_data = self.lap_data[(lap, sensor)]
                # Gerar uma cor única para cada curva baseada no hash do sensor e volta
                color = pg.intColor(abs(hash(lap + sensor)) % 256)
                pen = mkPen(color=color, width=2)
                curve = self.plot_widget.plot(
                    name=f"{lap} - {sensor.replace('_', ' ').title()}",
                    symbol='o', symbolSize=5, symbolBrush=color
                )
                curve.setData(time_data, value_data, pen=pen)
                self.curves[(lap, sensor)] = curve
                print(f"Plotando {lap} - {sensor}")

                # Adicionar legenda e botão de cor
                self.add_legend_entry(lap, sensor, curve)

        print("Comparação de voltas concluída")

    def add_legend_entry(self, lap, sensor, curve):
        """
        Adiciona uma entrada de legenda e botão de cor para a combinação de volta e sensor.
        """
        # Criar e configurar o label da legenda
        label_text = f"{lap} - {sensor.replace('_', ' ').title()} - Tempo: N/A - Valor: N/A"
        label = QLabel(label_text)
        
        # Determinar a cor do texto com base no tema atual
        text_color = 'white' if self.main_window and self.main_window.current_theme == "Dark" else 'black'
        label.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {text_color};")
        
        self.legend_layout.addWidget(label)
        self.legend_labels[(lap, sensor)] = label

        # Criar e configurar o botão de cor
        color_button = QPushButton("🔴")
        color_button.setFixedWidth(30)
        color_button.setStyleSheet(f"background-color: {curve.opts['pen'].color().name()}; border: none;")
        color_button.clicked.connect(lambda checked, s=(lap, sensor): self.change_line_color(s))
        self.legend_layout.addWidget(color_button)
        self.color_buttons[(lap, sensor)] = color_button

    def change_line_color(self, sensor_tuple):
        """
        Abre um diálogo para selecionar a cor da linha do sensor especificado.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            color_hex = color.name()
            print(f"Cor selecionada para {sensor_tuple}: {color_hex}")
            
            # Verificar se a curva existe antes de tentar acessá-la
            if sensor_tuple not in self.curves:
                print(f"Erro: Curva não encontrada para {sensor_tuple}")
                return
                
            # Atualizar a cor no gráfico
            curve = self.curves[sensor_tuple]
            curve.setPen(mkPen(color=color_hex, width=2))
            curve.setSymbolBrush(pg.mkBrush(color_hex))
            
            # Atualizar a cor do botão
            if sensor_tuple in self.color_buttons:
                self.color_buttons[sensor_tuple].setStyleSheet(f"background-color: {color_hex}; border: none;")

    def on_main_theme_changed(self, theme):
        """
        Atualiza o tema quando a janela principal muda de tema.
        """
        print(f"Tema da janela principal alterado para: {theme}")
        
        # Se houver uma cor de fundo personalizada, não alterar
        if hasattr(self, 'custom_bg_color') and self.custom_bg_color is not None:
            print("Mantendo cor de fundo personalizada")
            return
            
        # Atualizar o tema
        is_dark = theme == "Dark"
        self.on_theme_changed(is_dark)
        
        print(f"Tema atualizado para: {theme}")

    def on_theme_changed(self, is_dark):
        """
        Atualiza as cores do gráfico quando o tema é alterado.
        """
        print(f"Tema alterado para: {'Escuro' if is_dark else 'Claro'}")
        
        # Definir as cores com base no tema
        if is_dark:
            bg_color = '#212121'  # Dark theme background from styles.py
            text_color = '#FFFFFF'  # Dark theme text from styles.py
            theme_name = "Dark"
            button_bg = '#fb0e0e'  # Dark theme button color from styles.py
            button_hover = '#ff0000'
            widget_bg = '#333333'  # Dark widget background
            border_color = '#fb0e0e'  # Dark border color
        else:
            bg_color = '#ffe6e6'  # Light theme background from styles.py
            text_color = '#000000'  # Light theme text from styles.py
            theme_name = "Light"
            button_bg = '#bd0000'  # Light theme button color from styles.py
            button_hover = '#ff0000'
            widget_bg = '#ffcccc'  # Light widget background
            border_color = '#bd0000'  # Light border color
        
        # Atualizar a cor de fundo do gráfico
        if self.plot_widget is not None:
            self.plot_widget.setBackground(bg_color)
        
        # Atualizar o botão de fundo para refletir a cor atual
        if hasattr(self, 'bg_color_button'):
            self.bg_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {button_bg};
                    color: {text_color};
                    border: 2px solid {text_color};
                    border-radius: 4px;
                    padding: 5px;
                    font-family: Arial;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {button_hover};
                }}
            """)
        
        # Atualizar as cores do texto
        if self.plot_widget is not None:
            self.update_text_colors(text_color)
        
        # Atualizar o estilo dos botões
        self.update_button_styles(is_dark)
        
        # Se estiver em tela cheia, atualizar também o gráfico da janela de tela cheia
        if hasattr(self, 'fullscreen_window') and self.fullscreen_window is not None:
            self.fullscreen_window.plot_widget.setBackground(bg_color)
            self.fullscreen_window.update_text_colors(text_color)
            self.fullscreen_window.on_theme_changed(is_dark)
        
        # Atualizar a grade do gráfico
        if self.plot_widget is not None:
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Atualizar a linha vertical
        if hasattr(self, 'vLine') and self.plot_widget is not None:
            self.vLine.setPen(pg.mkPen(text_color, width=1))
        
        # Atualizar as cores dos eixos e título
        if self.plot_widget is not None:
            self.plot_widget.setLabel('left', 'Valor', color=text_color)
            self.plot_widget.setLabel('bottom', 'Tempo (s)', color=text_color)
            self.plot_widget.getAxis('left').setTextPen(text_color)
            self.plot_widget.getAxis('bottom').setTextPen(text_color)
            self.plot_widget.getAxis('left').setPen(text_color)
            self.plot_widget.getAxis('bottom').setPen(text_color)
            self.plot_widget.setTitle("Comparação de Voltas", color=text_color)
        
        print(f"Tema alterado para: {theme_name}")
        print(f"Cor de fundo: {bg_color}")
        print(f"Cor do texto: {text_color}")
        
        # Força a atualização do widget
        self.plot_widget.update()
        if hasattr(self, 'fullscreen_window') and self.fullscreen_window is not None:
            self.fullscreen_window.plot_widget.update()

    def update_button_styles(self, is_dark):
        """
        Atualiza os estilos dos botões com base no tema.
        """
        print(f"Atualizando estilos dos botões para tema {'escuro' if is_dark else 'claro'}")
        
        # Definir cores com base no tema
        if is_dark:
            bg_color = '#212121'  # Dark theme background
            text_color = '#FFFFFF'  # Dark theme text
            button_bg = '#fb0e0e'  # Dark theme button background
            button_hover = '#ff0000'  # Dark theme button hover
            border_color = '#FFFFFF'  # Dark theme border
        else:
            bg_color = '#ffe6e6'  # Light theme background
            text_color = '#000000'  # Light theme text
            button_bg = '#bd0000'  # Light theme button background
            button_hover = '#ff0000'  # Light theme button hover
            border_color = '#000000'  # Light theme border
        
        # Estilo base para botões
        base_button_style = f"""
            QPushButton {{
                background-color: {button_bg};
                color: {text_color if is_dark else '#FFFFFF'};
                border: 2px solid {border_color};
                border-radius: 4px;
                padding: 5px;
                font-family: Arial;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:disabled {{
                background-color: {'#4A4A4A' if is_dark else '#ffb8b8'};
                color: {'#808080' if is_dark else '#666666'};
                border: 2px solid {'#808080' if is_dark else '#666666'};
            }}
        """
        
        # Aplicar estilo aos botões
        for button in self.findChildren(QPushButton):
            button.setStyleSheet(base_button_style)
        
        # Estilo para checkboxes
        checkbox_style = f"""
            QCheckBox {{
                color: {text_color};
                font-family: Arial;
                font-size: 14px;
            }}
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                background-color: {'#4A4A4A' if is_dark else '#ffcccc'};
                border: 1px solid {button_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {button_bg};
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {button_hover};
            }}
        """
        
        # Aplicar estilo aos checkboxes
        for checkbox in self.findChildren(QCheckBox):
            checkbox.setStyleSheet(checkbox_style)
        
        print("Estilos dos botões atualizados com sucesso")

    def update_text_colors(self, text_color):
        """
        Atualiza as cores do texto no gráfico e elementos da interface.
        """
        print(f"Atualizando cores do texto para: {text_color}")
        
        # Atualiza as cores dos eixos
        self.plot_widget.setLabel('left', 'Valor', color=text_color)
        self.plot_widget.setLabel('bottom', 'Tempo (s)', color=text_color)
        self.plot_widget.getAxis('left').setTextPen(text_color)
        self.plot_widget.getAxis('bottom').setTextPen(text_color)
        self.plot_widget.getAxis('left').setPen(text_color)
        self.plot_widget.getAxis('bottom').setPen(text_color)
        
        # Atualiza a linha vertical se existir e estiver inicializada
        if hasattr(self, 'vLine') and self.vLine is not None:
            try:
                self.vLine.setPen(pg.mkPen(text_color, width=1))
            except RuntimeError:
                print("Aviso: vLine ainda não está pronta para atualização")
        
        # Atualiza a grade
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Atualiza o título se existir
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {text_color};")
        
        # Atualiza as cores das curvas se existirem
        if hasattr(self, 'curves') and self.curves:
            for curve in self.curves.values():
                curve.setPen(text_color)
        
        # Atualiza a legenda se existir
        if hasattr(self, 'legend'):
            self.legend.setLabelTextColor(text_color)
        
        # Atualiza as cores dos labels da legenda
        for label in self.legend_labels.values():
            label.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {text_color};")
        
        print("Cores do texto atualizadas com sucesso")

    def compare_laps(self):
        """
        Compara as voltas selecionadas com os sensores escolhidos.
        """
        # Coletar voltas selecionadas
        self.selected_laps = [lap for lap, checkbox in self.lap_checkboxes.items() if checkbox.isChecked()]
        print("Voltas Selecionadas para Comparar:", self.selected_laps)

        # Validar seleções
        if not self.selected_sensors:
            QMessageBox.warning(self, "Nenhum Sensor Selecionado", "Por favor, selecione pelo menos um sensor para comparar.")
            return

        if not self.selected_laps:
            QMessageBox.warning(self, "Nenhuma Volta Selecionada", "Por favor, selecione pelo menos uma volta para comparar.")
            return

        # Limpar gráficos anteriores
        self.plot_widget.clear()
        self.curves = {}
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)

        # Limpar legend_box
        self._clear_legend_box()

        # Plotar dados para cada combinação de volta e sensor
        for lap in self.selected_laps:
            for sensor in self.selected_sensors:
                self._plot_lap_sensor_data(lap, sensor)

    def _clear_legend_box(self):
        """Limpa a caixa de legenda."""
        for i in reversed(range(self.legend_layout.count())):
            widget_to_remove = self.legend_layout.itemAt(i).widget()
            self.legend_layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
        self.legend_labels.clear()
        self.color_buttons.clear()

    def _plot_lap_sensor_data(self, lap, sensor):
        """Plota os dados para uma combinação específica de volta e sensor."""
        # Gerar ou recuperar dados
        if (lap, sensor) not in self.lap_data:
            time_data = list(range(60))
            value_data = [random.uniform(150, 200) for _ in time_data]
            self.lap_data[(lap, sensor)] = (time_data, value_data)
            print(f"Simulando dados para {lap} - {sensor}")

        time_data, value_data = self.lap_data[(lap, sensor)]
        
        # Criar curva
        color = pg.intColor(abs(hash(lap + sensor)) % 256)
        pen = mkPen(color=color, width=2)
        curve = self.plot_widget.plot(
            time_data, value_data, pen=pen,
            name=f"{lap} - {sensor.replace('_', ' ').title()}",
            symbol='o', symbolSize=5, symbolBrush=color
        )
        
        # Anexar dados à curva
        curve.x_data = time_data
        curve.y_data = value_data
        self.curves[(lap, sensor)] = curve
        
        # Adicionar legenda
        self.add_legend_entry(lap, sensor, curve)
        print(f"Plotando {lap} - {sensor}")
