import os
import socket
import json
import zlib
import time

def get_current_size(file_path):
    """Получить текущий размер файла, если он существует"""
    return os.path.getsize(file_path) if os.path.exists(file_path) else 0

def calculate_file_crc32(file_path):
    """Вычислить CRC32 всего файла"""
    crc32 = 0
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            crc32 = zlib.crc32(chunk, crc32)
    return f"{crc32 & 0xFFFFFFFF:08x}"

def receive_file(port, save_directory):
    """Сервер для приема файла с обработкой отключений клиента"""
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
        print(f"Создана директория для сохранения файлов: {save_directory}")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('localhost', port))
        server_socket.listen(5)
        print(f"Сервер слушает на порту {port}. Файлы будут сохранены в {save_directory}...")

        while True:
            try:
                conn, addr = server_socket.accept()
                with conn:
                    print(f"Подключено к {addr}")
                    
                    # Получение метаданных
                    metadata = conn.recv(1024).decode('utf-8')
                    metadata = json.loads(metadata)
                    file_name = metadata['file_name']
                    file_size = metadata['file_size']
                    file_crc32 = metadata['file_crc32']
                    print(f"Ожидается файл: {file_name}, размер: {file_size} байт, CRC32: {file_crc32}")

                    # Полный путь к файлу
                    file_path = os.path.join(save_directory, file_name)
                    print(f"Файл будет сохранен по пути: {file_path}")

                    # Проверка существующего файла
                    current_size = get_current_size(file_path)
                    if current_size < file_size:
                        conn.send(b'continue')
                        time.sleep(2)
                        conn.send(str(current_size).encode('utf-8'))
                    else:
                        conn.send(b'new')

                    # Получение файла
                    total_received = current_size
                    with open(file_path, 'ab') as file:
                        while total_received < file_size:
                            try:
                                data = conn.recv(min(1024 * 1024, file_size - total_received))
                                if not data:
                                    print("Клиент отключился до завершения передачи.")
                                    break
                                file.write(data)
                                total_received += len(data)
                                print(f"Получено: {total_received}/{file_size} байт")
                            except ConnectionResetError:
                                print("Соединение сброшено клиентом.")
                                break

                    # Проверка CRC32, если файл передан полностью
                    if total_received == file_size:
                        print("Проверка CRC32...")
                        calculated_crc32 = calculate_file_crc32(file_path)
                        print(f"Ожидаемый CRC32: {file_crc32}, вычисленный: {calculated_crc32}")
                        
                        if calculated_crc32 == file_crc32:
                            conn.send(b"CRC32_OK")
                            print("CRC32 совпали. Передача завершена успешно.")
                        else:
                            conn.send(b"CRC32_ERROR")
                            print(f"CRC32 не совпадает. Ожидалось {file_crc32}, получено {calculated_crc32}.")
                    else:
                        print(f"Файл не был полностью передан. Получено {total_received} из {file_size} байт.")
                    
                    print("Сервер завершил обработку файла.")
            except Exception as e:
                print(f"Ошибка при обработке соединения: {e}")

if __name__ == "__main__":
    receive_file(int(input("Порт: ")), input("Директория сохранения: "))
