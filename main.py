"""
Telemetria UTFORCE E-RACING
Copyright (c) 2024 Lucas Fernandes Christen. Todos os direitos reservados.

Este software é proprietário e confidencial. É proibida a reprodução, distribuição,
modificação ou uso comercial sem autorização expressa do autor.

Desenvolvido para a Equipe de formula SAE Elétrica UTForce E-Racing.
Última atualização: 02/01/2024

Descrição:
    Aplicativo de telemetria que simula dados de sensores e os visualiza
    em gráficos interativos através de uma interface gráfica moderna.
"""

# main.py 

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from data.data_simulator import DataSimulator
from data.data_processor import DataProcessor

def main():
    app = QApplication(sys.argv)
    
    # Aplicar o stylesheet global
    app.setStyleSheet("""
        QWidget {
            background-color: #2E2E2E; /* Cinza escuro */
            color: #FFFFFF; /* Texto branco */
            font-family: Arial;
            font-size: 14px;
        }
        QCheckBox::indicator {
            background-color: #4A4A4A;
            border: 1px solid #FFFFFF;
            width: 15px;
            height: 15px;
        }
        QCheckBox::indicator:checked {
            background-color: #FFFFFF;
        }
        QPushButton {
            background-color: #4A4A4A;
            border: none;
            padding: 5px 10px;
            color: #FFFFFF;
        }
        QPushButton:hover {
            background-color: #606060;
        }
        QComboBox {
            background-color: #4A4A4A;
            border: 1px solid #FFFFFF;
            color: #FFFFFF;
        }
        QLabel {
            color: #FFFFFF;
        }
        QListWidget {
            background-color: #3A3A3A;
            border: 1px solid #FFFFFF;
            color: #FFFFFF;
        }
        QGroupBox {
            border: 2px solid #4A4A4A;
            border-radius: 5px;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center; /* Ajuste conforme necessário */
            padding: 0 3px;
            color: #FFFFFF;
        }
    """)
    
    # Inicializa a janela principal
    window = MainWindow()
    window.show()
    
    # Inicializa o simulador de dados
    simulator = DataSimulator()
    
    # Inicializa o processador de dados e conecta ao GUI
    processor = DataProcessor()
    processor.data_updated.connect(window.update_graphs_with_data)
    
    # Conecta o simulador ao processador
    simulator.data_generated.connect(processor.process_data)
    
    # Inicia a simulação
    simulator.start()
    
    # Executa o aplicativo
    exit_code = app.exec()
    
    # Para a simulação ao fechar o aplicativo
    simulator.stop()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
