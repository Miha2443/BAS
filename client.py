import socket
import os
import zlib
import json
import sys

def calculate_file_crc32(file_path):
    """Вычислить CRC32 всего файла"""
    crc32 = 0
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            crc32 = zlib.crc32(chunk, crc32)
    return f"{crc32 & 0xFFFFFFFF:08x}"

def send_file(server_ip, server_port, file_path):
    """Отправить файл на сервер"""
    try:
        file_size = os.path.getsize(file_path)
        file_crc32 = calculate_file_crc32(file_path)
        file_name = os.path.basename(file_path)
        
        # Подключение к серверу
        print(f"Подключение к серверу {server_ip}:{server_port}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((server_ip, server_port))

            # Отправка метаданных
            metadata = json.dumps({
                'file_name': file_name,
                'file_size': file_size,
                'file_crc32': file_crc32
            })
            sock.send(metadata.encode('utf-8'))

            # Получение ответа от сервера
            response = sock.recv(1024).decode('utf-8')
            if response == 'continue':
                current_size = int(sock.recv(1024).decode('utf-8'))
                print(f"Сервер продолжает передачу с позиции {current_size} байт.")
            elif response == 'new':
                current_size = 0
                print("Сервер начинает новую передачу.")

            # Передача файла
            with open(file_path, 'rb') as file:
                file.seek(current_size)  # Продолжить с места разрыва
                while chunk := file.read(1024 * 1024):  # Чтение чанка размером 1 MB
                    sock.send(chunk)
                    print(f"Отправлено {file.tell()}/{file_size} байт", end='\r')

            print("\nПередача завершена. Ожидание ответа от сервера...")

            # Ожидание результата CRC32
            result = sock.recv(1024).decode('utf-8')
            if result == 'CRC32_OK':
                print("Передача файла завершена успешно. Контрольная сумма совпала.")
            elif result == 'CRC32_ERROR':
                print("Ошибка: контрольная сумма не совпала.")
            else:
                print(f"Неизвестный ответ от сервера: {result}")

    except Exception as e:
        print(f"Ошибка при передаче файла: {e}")

if __name__ == "__main__":
    # Ввод IP-адреса сервера
    server_ip = input("Введите IP-адрес сервера: ").strip()
    if not server_ip:
        print("Ошибка: IP-адрес сервера не может быть пустым.")
        sys.exit(1)

    # Порт сервера
    server_port = int(input("Порт: "))

    # Ввод пути к файлу
    file_path = input("Введите путь к файлу для отправки: ").strip()
    if not os.path.isfile(file_path):
        print(f"Ошибка: файл '{file_path}' не найден.")
        sys.exit(1)

    send_file(server_ip, server_port, file_path)
