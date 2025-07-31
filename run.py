#!/usr/bin/env python3
"""
Скрипт для запуска всех компонентов системы Рильке
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    try:
        import aiogram
        import flask
        import sqlite3
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False

def check_env_file():
    """Проверяет наличие файла .env"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден")
        print("Скопируйте .env.example в .env и настройте переменные окружения")
        return False
    
    # Проверяем основные переменные
    with open('.env', 'r') as f:
        content = f.read()
        if 'BOT_TOKEN' not in content or 'ADMIN_BOT_TOKEN' not in content:
            print("⚠️  Не все переменные окружения настроены в .env")
            print("Убедитесь, что BOT_TOKEN и ADMIN_BOT_TOKEN установлены")
            return False
    
    print("✅ Файл .env настроен")
    return True

def start_process(command, name):
    """Запускает процесс и возвращает объект процесса"""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        print(f"🚀 {name} запущен (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Ошибка запуска {name}: {e}")
        return None

def monitor_process(process, name):
    """Мониторит процесс и выводит его вывод"""
    while process.poll() is None:
        output = process.stdout.readline()
        if output:
            print(f"[{name}] {output.strip()}")
    
    # Выводим оставшийся вывод
    remaining_output, error_output = process.communicate()
    if remaining_output:
        print(f"[{name}] {remaining_output.strip()}")
    if error_output:
        print(f"[{name} ERROR] {error_output.strip()}")

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    print("\n🛑 Получен сигнал завершения. Останавливаю процессы...")
    sys.exit(0)

def main():
    """Основная функция запуска"""
    print("🎭 Запуск системы Рильке")
    print("=" * 50)
    
    # Проверки
    if not check_dependencies():
        sys.exit(1)
    
    if not check_env_file():
        sys.exit(1)
    
    # Настройка обработчика сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    processes = []
    
    try:
        # Запуск Flask веб-приложения
        print("\n🌐 Запуск веб-приложения...")
        web_process = start_process([sys.executable, 'app.py'], 'Web App')
        if web_process:
            processes.append(('Web App', web_process))
        
        # Небольшая задержка для запуска веб-приложения
        time.sleep(2)
        
        # Запуск основного телеграм бота
        print("\n🤖 Запуск основного телеграм бота...")
        bot_process = start_process([sys.executable, 'bot.py'], 'Telegram Bot')
        if bot_process:
            processes.append(('Telegram Bot', bot_process))
        
        # Небольшая задержка
        time.sleep(1)
        
        # Запуск админ телеграм бота
        print("\n👨‍💼 Запуск админ телеграм бота...")
        admin_process = start_process([sys.executable, 'admin_bot.py'], 'Admin Bot')
        if admin_process:
            processes.append(('Admin Bot', admin_process))
        
        print("\n" + "=" * 50)
        print("🎉 Все компоненты запущены!")
        print("\n📱 Доступные сервисы:")
        print("   🌐 Веб-приложение: http://localhost:5000")
        print("   🤖 Основной бот: @your_bot_username")
        print("   👨‍💼 Админ бот: @your_admin_bot_username")
        print("\n💡 Для остановки нажмите Ctrl+C")
        print("=" * 50)
        
        # Мониторинг процессов
        threads = []
        for name, process in processes:
            thread = threading.Thread(target=monitor_process, args=(process, name))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Ожидание завершения процессов
        while True:
            time.sleep(1)
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️  {name} завершился с кодом {process.returncode}")
                    return
    
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал завершения")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        # Завершение всех процессов
        print("\n🔄 Завершение процессов...")
        for name, process in processes:
            if process.poll() is None:
                print(f"🛑 Остановка {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"⚠️  Принудительное завершение {name}")
                    process.kill()
        
        print("✅ Все процессы завершены")

if __name__ == "__main__":
    main()