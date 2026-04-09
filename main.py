import sys
import json
import os
import ctypes
import psutil
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLineEdit, QMessageBox, QLabel, QListWidgetItem, QGroupBox
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6 import uic



# Проверка прав администратора

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


if not is_admin():
    args = " ".join(f'"{arg}"' for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
    sys.exit()


# Настройки путей
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_FILE = os.path.join(SCRIPT_DIR, "blocked_apps.json")

CRITICAL_PROCESSES = {
    "explorer.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "svchost.exe", "lsass.exe", "smss.exe", "system", "idle"
}


class BlacklistManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Чёрный список приложений")
        self.resize(750, 700)

        self.blacklist = set()
        self.load_blacklist()

        self.setup_ui()
        self.update_list()
        self.refresh_running_apps()

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_processes)
        self.is_monitoring = False

    def setup_ui(self):
        layout = QVBoxLayout()

        # Секция 1: Запущенные приложения
        running_group = QGroupBox("Запущенные приложения (выберите для блокировки)")
        running_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 2px solid #28a745; border-radius: 5px; margin-top: 10px; }")
        running_layout = QVBoxLayout()

        refresh_btn = QPushButton("Обновить список")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 5px; }")
        running_layout.addWidget(refresh_btn)

        self.all_apps_list = QListWidget()
        self.all_apps_list.setMinimumHeight(200)
        self.all_apps_list.setStyleSheet("QListWidget { background-color: #e8f5e9; }")
        running_layout.addWidget(self.all_apps_list)

        self.block_selected_btn = QPushButton("Заблокировать выбранное")
        self.block_selected_btn.setStyleSheet(
            "QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 8px; }")
        running_layout.addWidget(self.block_selected_btn)

        running_group.setLayout(running_layout)
        layout.addWidget(running_group)

        # Секция 2: Чёрный список
        blacklist_group = QGroupBox("Чёрный список")
        blacklist_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 2px solid #ffc107; border-radius: 5px; margin-top: 10px; }")
        blacklist_layout = QVBoxLayout()

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Или введите вручную: game.exe")
        self.add_btn = QPushButton("Добавить")
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.add_btn)
        blacklist_layout.addLayout(input_layout)

        self.remove_btn = QPushButton("Удалить из списка")
        blacklist_layout.addWidget(self.remove_btn)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(150)
        self.list_widget.setStyleSheet("QListWidget { background-color: #fff3cd; }")
        blacklist_layout.addWidget(self.list_widget)

        blacklist_group.setLayout(blacklist_layout)
        layout.addWidget(blacklist_group)

        # Секция 3: Управление
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("ЗАПУСТИТЬ ЗАЩИТУ")
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #007bff; color: white; font-weight: bold; font-size: 12px; padding: 10px; }")
        self.stop_btn = QPushButton("ОСТАНОВИТЬ")
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #6c757d; color: white; font-weight: bold; font-size: 12px; padding: 10px; }")
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        layout.addLayout(control_layout)

        self.log_label = QLabel("Статус: Ожидание...")
        self.log_label.setStyleSheet(
            "font-weight: bold; color: #2c3e50; background-color: #f8f9fa; padding: 8px; border-radius: 3px;")
        layout.addWidget(self.log_label)

        self.setLayout(layout)

        # Сигналы
        refresh_btn.clicked.connect(self.refresh_running_apps)
        self.block_selected_btn.clicked.connect(self.block_selected_app)
        self.add_btn.clicked.connect(self.add_to_blacklist)
        self.remove_btn.clicked.connect(self.remove_from_blacklist)
        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.all_apps_list.itemDoubleClicked.connect(self.block_selected_app)

    def is_system_process(self, name, exe_path):
        """Проверяет, является ли процесс системным"""
        name_lower = name.lower() if name else ""
        exe_lower = exe_path.lower() if exe_path else ""

        system_paths = [
            r"c:\windows",
            r"c:\program files\windows",
            r"c:\program files (x86)\windows",
            r"\system32",
            r"\syswow64"
        ]

        if name_lower in CRITICAL_PROCESSES:
            return True
        for sys_path in system_paths:
            if sys_path in exe_lower:
                return True
        if not name or name_lower == "":
            return True
        return False

    def refresh_running_apps(self):
        self.all_apps_list.clear()

        try:
            apps_dict = {}

            for proc in psutil.process_iter(['pid', 'name', 'exe', 'memory_info']):
                try:
                    name = proc.info['name']
                    exe = proc.info['exe']

                    if not name:
                        continue
                    if self.is_system_process(name, exe or ""):
                        continue

                    name_lower = name.lower()
                    if name_lower not in apps_dict:
                        apps_dict[name_lower] = {
                            "name": name,
                            "count": 0,
                            "pids": [],
                            "exe": exe or "Неизвестно",
                            "in_blacklist": name_lower in self.blacklist
                        }

                    apps_dict[name_lower]["count"] += 1
                    apps_dict[name_lower]["pids"].append(proc.info['pid'])

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            sorted_apps = sorted(apps_dict.items(), key=lambda x: x[0])

            for name_lower, app_info in sorted_apps:
                count = app_info["count"]
                name = app_info["name"]
                pids = app_info["pids"]
                in_blacklist = app_info["in_blacklist"]

                count_text = f"×{count}" if count > 1 else ""
                status = "ЗАБЛОКИРОВАНО" if in_blacklist else "✓"
                color = "#dc3545" if in_blacklist else "#28a745"
                pid_text = f"(PID: {pids[0]})" if len(pids) == 1 else f"(процессов: {count})"

                item_text = f"{status} {name} {count_text} {pid_text}"
                item = QListWidgetItem(item_text)
                item.setForeground(QColor(color))
                item.setData(100, name)
                item.setData(101, pids)
                item.setData(102, count)
                self.all_apps_list.addItem(item)

            total_apps = len(apps_dict)
            total_procs = sum(info["count"] for info in apps_dict.values())
            self.log_label.setText(f"Приложений: {total_apps} | Процессов: {total_procs}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить список:\n{e}")

    def block_selected_app(self):
        selected = self.all_apps_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите приложение из списка!")
            return

        blocked_count = 0
        for item in selected:
            app_name = item.data(100)
            count = item.data(102)

            if app_name:
                app_name = app_name.lower()

                if app_name in CRITICAL_PROCESSES:
                    QMessageBox.critical(self, " Опасно", f"Нельзя блокировать: {app_name}")
                    continue
                if app_name in self.blacklist:
                    continue

                self.blacklist.add(app_name)
                blocked_count += 1
                self.log_label.setText(f" Заблокировано: {app_name} ({count} процессов)")

        if blocked_count > 0:
            self.update_list()
            self.save_blacklist()
            self.refresh_running_apps()
            QMessageBox.information(self, "Готово",
                f"Добавлено в чёрный список: {blocked_count} приложение(й)\n\n"
                f"Все процессы этих приложений будут автоматически закрываться!")

    def load_blacklist(self):
        if os.path.exists(BLACKLIST_FILE):
            try:
                with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                    self.blacklist = set(json.load(f))
            except Exception:
                self.blacklist = set()

    def save_blacklist(self):
        try:
            with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(self.blacklist), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_label.setText(f"Ошибка сохранения: {e}")

    def add_to_blacklist(self):
        text = self.input_field.text().strip().lower()
        if not text:
            QMessageBox.warning(self, "Внимание", "Введите имя приложения!")
            return

        if not text.endswith('.exe'):
            text += '.exe'

        if text in CRITICAL_PROCESSES:
            QMessageBox.critical(self, " Опасно", "Нельзя блокировать системные процессы!")
            return
        if text in self.blacklist:
            QMessageBox.information(self, "Инфо", "Уже в чёрном списке.")
            return

        self.blacklist.add(text)
        self.input_field.clear()
        self.update_list()
        self.save_blacklist()
        self.refresh_running_apps()
        self.log_label.setText(f"Добавлено: {text}")

    def remove_from_blacklist(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите приложение для удаления!")
            return

        for item in selected:
            self.blacklist.discard(item.text().lower())
        self.update_list()
        self.save_blacklist()
        self.refresh_running_apps()
        self.log_label.setText("Удалено из чёрного списка")

    def update_list(self):
        self.list_widget.clear()
        for app in sorted(self.blacklist):
            self.list_widget.addItem(app)

    def start_monitoring(self):
        if not self.blacklist:
            QMessageBox.warning(self, "Внимание", "Добавьте приложения в чёрный список!")
            return

        self.is_monitoring = True
        self.monitor_timer.start(1000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        self.log_label.setText("ЗАЩИТА АКТИВНА! Блокировка работает...")

        self.input_field.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.block_selected_btn.setEnabled(False)

    def stop_monitoring(self):
        self.is_monitoring = False
        self.monitor_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.start_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; }")
        self.log_label.setText("Мониторинг остановлен")

        self.input_field.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        self.block_selected_btn.setEnabled(True)

    def monitor_processes(self):
        if not self.is_monitoring:
            return

        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if name and name.lower() in self.blacklist:
                        pid = proc.info['pid']
                        try:
                            proc.terminate()
                            proc.wait(timeout=2)
                            self.log_label.setText(f"Закрыто: {name} (PID: {pid})")
                        except (psutil.NoSuchProcess, psutil.ZombieProcess):
                            pass
                        except:
                            try:
                                proc.kill()
                                self.log_label.setText(f"УБИТО: {name} (PID: {pid})")
                            except Exception:
                                self.log_label.setText(f"Не удалось закрыть {name}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.log_label.setText(f"❌ Ошибка: {e}")
            return

        self.refresh_running_apps()



# Главное окно

class MyWidget(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi('base.ui', self)

        self.application.clicked.connect(self.open_process_manager)


    def open_process_manager(self):
        self.manager = BlacklistManagerDialog(self)
        self.manager.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())