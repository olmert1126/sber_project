import sys
import time
import json
import os
import psutil
import win32process
from win32gui import GetForegroundWindow
from PyQt6.QtCore import QThread
from datetime import datetime, date


class StatsWorker(QThread):
    def __init__(self):
        super().__init__()
        self.app_usage_stats = {}
        self.last_app_name = None
        self.last_switch_time = time.time()
        self.is_running = True
        self.error_message = None

        # Путь для хранения статистики
        self.stats_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_stats.json")

        # Загружаем данные при старте
        self.load_stats()
        self.check_new_day()

    def run(self):
        while self.is_running:
            try:
                # Проверяем, не наступил ли новый день, каждый цикл (раз в секунду)
                self.check_new_day()

                hwnd = GetForegroundWindow()
                if not hwnd:
                    time.sleep(1)
                    continue

                # Получаем PID активного окна
                _, pid = win32process.GetWindowThreadProcessId(hwnd)

                # Игнорируем системные процессы с PID 0 или 4
                if pid == 0:
                    time.sleep(1)
                    continue

                process = psutil.Process(pid)
                current_app = process.name().replace(".exe", "")
                current_time = time.time()

                # Логика подсчета времени                if current_app != self.last_app_name:
                if self.last_app_name is not None:
                    duration = current_time - self.last_switch_time
                    if duration > 0:
                        self.app_usage_stats[self.last_app_name] = self.app_usage_stats.get(self.last_app_name,
                                                                                            0) + duration

                self.last_app_name = current_app
                self.last_switch_time = current_time

                time.sleep(1)

            except psutil.NoSuchProcess:
                pass

            except psutil.AccessDenied:
                pass

            except Exception as e:
                self.error_message = str(e)
                time.sleep(1)


    def check_new_day(self):
        #  Проверяет, сменилась ли дата
        last_date_str = self.app_usage_stats.get("_last_date", None)
        today_str = date.today().isoformat()

        if last_date_str != today_str:
            # Обнуляем статистику
            self.app_usage_stats = {"_last_date": today_str}
            self.last_app_name = None
            self.last_switch_time = time.time()
            self.save_stats()


    def load_stats(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                last_date_str = data.get("_last_date", None)
                today_str = date.today().isoformat()

                if last_date_str == today_str:
                    # Если дата совпадает, загружаем данные
                    self.app_usage_stats = data
                    self.app_usage_stats["_last_date"] = today_str
                else:
                    self.app_usage_stats = {"_last_date": today_str}
            except Exception:
                self.app_usage_stats = {"_last_date": date.today().isoformat()}
        else:
            self.app_usage_stats = {"_last_date": date.today().isoformat()}


    def save_stats(self):
        try:
            # Делаем копию, чтобы добавить текущее активное приложение перед сохранением
            stats_to_save = self.app_usage_stats.copy()

            if self.last_app_name:
                current_duration = time.time() - self.last_switch_time
                stats_to_save[self.last_app_name] = stats_to_save.get(self.last_app_name, 0) + current_duration

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения статистики: {e}")


    def get_formatted_stats(self):
        # Возвращает отформатированную строку со статистикой
        if self.error_message:
            return f"Ошибка в работе трекера:\n{self.error_message}"

        stats = self.app_usage_stats.copy()

        # Добавляем текущее активное приложение для отображения
        if self.last_app_name:
            current_duration = time.time() - self.last_switch_time
            stats[self.last_app_name] = stats.get(self.last_app_name, 0) + current_duration

        # Удаляем служебное поле даты из отображения
        stats.pop("_last_date", None)

        if not stats:
            return "Нет данных. Поработайте в каких-нибудь приложениях..."

        msg = "Время использования приложений за сегодня:\n"

        # Сортировка по убыванию времени
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)

        for app_name, seconds in sorted_stats:
            if seconds < 2: continue  # Не показывать если меньше 2 секунд

            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            msg += f"{app_name} : {h:02d}:{m:02d}:{s:02d}\n"
            return msg


    def stop_worker(self):
        self.is_running = False
        self.save_stats()
        self.wait()