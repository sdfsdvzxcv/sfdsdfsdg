#!/usr/bin/env python3
"""
Запуск всех компонентов проекта "Рильке"
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path

def check_dependencies():
    """Проверка наличия необходимых зависимостей"""
    required_files = ['bot.py', 'app.py', 'requirements.txt']
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Отсутствуют необходимые файлы: {', '.join(missing_files)}")
        return False
    
    return True

def check_env_file():
    """Проверка наличия файла .env"""
    if not Path('.env').exists():
        print("⚠️  Файл .env не найден. Создайте его на основе .env.example")
        print("   Для работы бота необходимо указать BOT_TOKEN и ADMIN_IDS")
        return False
    return True

def start_process(command, name):
    """Запуск процесса"""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        print(f"✅ {name} запущен (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Ошибка запуска {name}: {e}")
        return None

def monitor_process(process, name):
    """Мониторинг процесса"""
    if process is None:
        return
    
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.strip()}")
    except KeyboardInterrupt:
        print(f"\n🛑 Остановка {name}...")
        process.terminate()
        process.wait()

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    print("\n🛑 Получен сигнал завершения. Останавливаю все процессы...")
    sys.exit(0)

def main():
    """Основная функция запуска"""
    print("🎭 Запуск проекта 'Рильке'")
    print("=" * 50)
    
    # Проверки
    if not check_dependencies():
        sys.exit(1)
    
    if not check_env_file():
        print("⚠️  Продолжаем без проверки .env файла...")
    
    # Настройка обработчика сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    processes = []
    
    try:
        # Запуск Flask веб-приложения
        print("\n🌐 Запуск веб-приложения...")
        flask_process = start_process([sys.executable, 'app.py'], 'Flask App')
        if flask_process:
            processes.append(flask_process)
        
        # Небольшая пауза для запуска Flask
        time.sleep(2)
        
        # Запуск Telegram бота
        print("\n🤖 Запуск Telegram бота...")
        bot_process = start_process([sys.executable, 'bot.py'], 'Telegram Bot')
        if bot_process:
            processes.append(bot_process)
        
        print("\n✅ Все компоненты запущены!")
        print("🌐 Веб-приложение: http://localhost:5000")
        print("🤖 Telegram бот: активен")
        print("\n📝 Логи процессов:")
        print("-" * 50)
        
        # Мониторинг процессов
        while processes:
            for process in processes[:]:
                if process.poll() is not None:
                    print(f"⚠️  Процесс завершился (PID: {process.pid})")
                    processes.remove(process)
                else:
                    # Читаем вывод процесса
                    try:
                        line = process.stdout.readline()
                        if line:
                            process_name = "Flask App" if process == flask_process else "Telegram Bot"
                            print(f"[{process_name}] {line.strip()}")
                    except:
                        pass
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал завершения...")
    
    finally:
        # Остановка всех процессов
        print("🛑 Остановка всех процессов...")
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Процесс остановлен (PID: {process.pid})")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⚠️  Процесс принудительно остановлен (PID: {process.pid})")
            except Exception as e:
                print(f"❌ Ошибка остановки процесса: {e}")
        
        print("👋 Все процессы остановлены")

if __name__ == "__main__":
    main()