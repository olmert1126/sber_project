# site_blocker_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLineEdit, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt
from site_blocker import is_valid_domain, normalize_domain, update_hosts_file, get_blocked_domains
import os


class SiteBlockerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 Блокировка сайтов")
        self.resize(500, 400)
        self.setup_ui()
        self.update_list()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        header = QLabel("Добавьте сайты, которые нужно заблокировать")
        header.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0;")
        layout.addWidget(header)

        # Ввод сайта
        input_layout = QHBoxLayout()
        self.site_input = QLineEdit()
        self.site_input.setPlaceholderText("example.com, vk.com, youtube.com")
        self.site_input.returnPressed.connect(self.add_site)

        self.add_btn = QPushButton("➕ Заблокировать")
        self.add_btn.clicked.connect(self.add_site)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8; color: white; 
                font-weight: bold; padding: 8px 15px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #138496; }
        """)

        input_layout.addWidget(self.site_input)
        input_layout.addWidget(self.add_btn)
        layout.addLayout(input_layout)

        # Список заблокированных
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa; border: 1px solid #ddd;
                border-radius: 4px; padding: 5px;
            }
            QListWidgetItem:selected { background-color: #17a2b8; color: white; }
        """)
        layout.addWidget(QLabel("🔒 Заблокированные сайты:"))
        layout.addWidget(self.list_widget)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.remove_btn = QPushButton("🗑️ Разблокировать выбранные")
        self.remove_btn.clicked.connect(self.remove_site)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107; color: black;
                font-weight: bold; padding: 8px; border-radius: 4px;
            }
        """)

        self.flush_btn = QPushButton("🔄 Обновить DNS")
        self.flush_btn.clicked.connect(self.flush_dns)
        self.flush_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d; color: white;
                padding: 8px; border-radius: 4px;
            }
        """)

        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.flush_btn)
        layout.addLayout(btn_layout)

        # Статус
        self.status_label = QLabel("Статус: Готово")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def update_list(self):
        """Обновляет список в интерфейсе"""
        self.list_widget.clear()
        for site in sorted(get_blocked_domains()):
            self.list_widget.addItem(site)

    def add_site(self):
        """Добавляет сайт в блокировку"""
        text = self.site_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Внимание", "Введите домен сайта!")
            return

        if not is_valid_domain(text):
            QMessageBox.critical(self, "Ошибка", "Некорректный формат!\nПример: `vk.com`")
            return

        domain = normalize_domain(text)
        current = get_blocked_domains()

        if domain in current:
            QMessageBox.information(self, "Инфо", "Сайт уже в списке блокировки.")
            return

        current.add(domain)
        try:
            update_hosts_file(current)
            self.site_input.clear()
            self.update_list()
            self.status_label.setText(f"✅ Заблокирован: {domain}")
            self.status_label.setStyleSheet("color: #28a745;")
        except PermissionError:
            QMessageBox.critical(self, "Ошибка", "Запустите программу от имени администратора!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def remove_site(self):
        """Убирает выбранные сайты из блокировки"""
        selected = [item.text() for item in self.list_widget.selectedItems()]
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите сайт для разблокировки!")
            return

        current = get_blocked_domains()
        for domain in selected:
            current.discard(domain)
            current.discard(f"www.{domain}")

        try:
            update_hosts_file(current)
            self.update_list()
            self.status_label.setText(f"🔓 Разблокировано: {len(selected)}")
            self.status_label.setStyleSheet("color: #ffc107;")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def flush_dns(self):
        """Очищает DNS-кэш"""
        try:
            os.system('ipconfig /flushdns >nul 2>&1')
            self.status_label.setText("🔄 DNS-кэш очищен")
            self.status_label.setStyleSheet("color: #007bff;")
        except:
            QMessageBox.warning(self, "Внимание", "Не удалось очистить DNS")