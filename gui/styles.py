# gui/styles.py

DARK_THEME = """
    QWidget {
        background-color: #212121; /* Fundo escuro */
        color: #FFFFFF; /* Texto branco */
        font-family: Arial;
        font-size: 14px;
    }
    QCheckBox::indicator {
        background-color: #4A4A4A;
        border: 1px solid #fb0e0e;
        width: 15px;
        height: 15px;
    }
    QCheckBox::indicator:checked {
        background-color: #fb0e0e;
    }
    QPushButton {
        background-color: #fb0e0e;
        border: none;
        padding: 5px 10px;
        color: #FFFFFF;
    }
    QPushButton:hover {
        background-color: #fb0e0e;
    }
    QComboBox {
        background-color: #4A4A4A;
        border: 1px solid #000000;
        color: #FFFFFF;
    }
    QLabel {
        color: #FFFFFF;
    }
    QListWidget {
        background-color: #3A3A3A;
        border: 1px solid #fb0e0e;
        color: #FFFFFF;
    }
    QGroupBox {
        border: 2px solid #4A4A4A;
        border-radius: 5px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 3px;
        color: #FFFFFF;
    }
    QTabBar::tab {
        background-color: #4A4A4A;
        color: #FFFFFF;
        padding: 10px;
        border: 1px solid #fb0e0e;
        border-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #fb0e0e;
        margin-bottom: -1px;
    }
    QHeaderView::section {
        background-color: #444444;
        color: #FFFFFF;
        font-size: 14px;
        font-weight: bold;
        padding: 4px;
        border: 1px solid #333333;
    }
"""


LIGHT_THEME = """
    /* Fundo geral com tom de vermelho muito claro */
    QWidget {
        background-color: #ffe6e6;
        color: #000000; /* Texto preto */
        font-family: Arial;
        font-size: 14px;
    }
    
    /* Checkbox com tom de vermelho claro */
    QCheckBox::indicator {
        background-color: #ffcccc;
        border: 1px solid #000000;
        width: 15px;
        height: 15px;
    }
    QCheckBox::indicator:checked {
        background-color: #bd0000;
    }
    
    /* Botões com vermelho intenso */
    QPushButton {
        background-color: #bd0000;
        border: none;
        padding: 5px 10px;
        color: #ffffff;
    }
    QPushButton:hover {
        background-color: #ff0000;
    }
    
    /* Combobox com fundo vermelho */
    QComboBox {
        background-color: #bd0000;
        border: 1px solid #000000;
        color: #000000;
    }
    
    /* Labels com texto preto */
    QLabel {
        color: #000000;
    }
    
    /* Lista com fundo diferenciado e texto preto */
    QListWidget {
        background-color: #ffb8b8;
        border: 2px solid #000000;
        color: #000000;
    }
    
    /* Item selecionado na lista */
    QListWidget::item:selected {
        background-color: #ffcccc;
        color: #000000;
        outline: 2px solid #000000;
        outline-offset: -2px;
    }
    
    /* Item da lista quando hover */
    QListWidget::item:hover {
        background-color: #ffa3a3;
    }
    
    /* GroupBox com borda e título em preto */
    QGroupBox {
        border: 2px solid #bd0000;
        border-radius: 5px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 3px;
        color: #000000;
    }
    
    /* Abas do QTabWidget: fundo vermelho e texto preto */
    QTabBar::tab {
        background-color: #ffa3a3;
        color: #000000;
        padding: 10px;
        border: 1px solid #bd0000;
        border-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #bd0000;
        color: #ffffff;
        margin-bottom: -1px;
    }
    
    /* Cabeçalhos de tabela com tom intermediário de vermelho e texto preto */
    QHeaderView::section {
        background-color: #ffd5d5;
        color: #000000;
        font-size: 12px;
        font-weight: bold;
        padding: 4px;
        border: 1px solid #bd0000;
    }
    
    /* Widget destinado a gráficos – defina o objectName="GraphWidget" se necessário */
    QWidget#GraphWidget {
        background-color: #ffcccc;
        border: 2px solid #bd0000;
    }
"""
