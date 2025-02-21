import os
import sys
import threading
import yt_dlp
from shutil import which
from metadata import add_metadata, convert_thumbnail


class Downloader:
    def __init__(self, download_folder, log_callback, progress_callback):
        """
        Класс, отвечающий за скачивание аудио с YouTube.
        :param download_folder: Папка для сохранения аудио.
        :param log_callback: Функция для логирования сообщений.
        :param progress_callback: Функция для обновления прогресса (принимает значение процента).
        """
        self.download_folder = download_folder
        os.makedirs(self.download_folder, exist_ok=True)
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.stop_event = threading.Event()
        self.thread = None
        self.with_metadata = False  # По умолчанию метаданные не добавляются

        # Определяем путь к ffmpeg в папке bin проекта.
        # Если приложение запущено из собранного exe (PyInstaller), используем sys._MEIPASS.
        if hasattr(sys, '_MEIPASS'):
            base_dir = os.path.join(sys._MEIPASS, 'bin')
        else:
            base_dir = os.path.join(os.path.dirname(__file__), 'bin')

        bin_ffmpeg = os.path.join(base_dir, 'ffmpeg.exe')
        bin_ffprobe = os.path.join(base_dir, 'ffprobe.exe')

        if os.path.exists(bin_ffmpeg) and os.path.exists(bin_ffprobe):
            self.ffmpeg_path = bin_ffmpeg
            self.ffprobe_path = bin_ffprobe
            self.log_callback(f"ffmpeg найден в папке bin: {self.ffmpeg_path}")
        else:
            # Если ffmpeg не найден в bin, ищем в системном PATH
            self.ffmpeg_path = which("ffmpeg")
            self.ffprobe_path = which("ffprobe")
            if self.ffmpeg_path:
                self.log_callback(f"ffmpeg найден в PATH: {self.ffmpeg_path}")
            else:
                self.log_callback("ffmpeg не найден ни в папке bin, ни в PATH.")

    def start_download(self, url_list, completion_callback):
        """
        Запускает загрузку в отдельном потоке.
        :param url_list: Список ссылок для загрузки.
        :param completion_callback: Функция, вызываемая по завершении всех загрузок.
        """
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._download_all, args=(url_list, completion_callback))
        self.thread.start()

    def stop_download(self):
        """
        Останавливает процесс загрузки.
        """
        self.stop_event.set()

    def _download_all(self, url_list, completion_callback):
        total = len(url_list)
        for idx, url in enumerate(url_list):
            if self.stop_event.is_set():
                self.log_callback("Загрузка остановлена пользователем.")
                break
            try:
                self.log_callback(f"Обработка ссылки: {url}")
                result = self.download_audio(url)
                self.log_callback(result)
            except Exception as e:
                self.log_callback(f"Ошибка: {e}")

            progress = (idx + 1) / total * 100
            self.progress_callback(progress)

        completion_callback()

    def download_audio(self, url):
        """
        Скачивает аудиофайл с YouTube.
        Если with_metadata = True, дополнительно внедряет метаданные (обложку, автора и т.д.).
        Возвращает строку с результатом.
        """
        if not self._ffmpeg_available():
            return "ffmpeg не найден. Установите ffmpeg для продолжения."

        # Формируем базовые опции для yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_folder, '%(playlist_title)s', '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': self.ffmpeg_path,
            'no_color': True,
            'progress_hooks': [self._progress_hook],
            # Добавляем HTTP-заголовки для имитации браузера
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
            },
        }

        # Скачиваем thumbnail только если нужны метаданные
        if self.with_metadata:
            ydl_opts['writethumbnail'] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)

            # Проверяем, плейлист это или одиночное видео
            if info_dict.get('_type') == 'playlist':
                entries = info_dict.get('entries', [])
                result_messages = []
                for entry in entries:
                    msg = self._process_single_entry(entry)
                    result_messages.append(msg)
                return "\n".join(result_messages)
            else:
                return self._process_single_entry(info_dict)

    def _process_single_entry(self, info_dict):
        """
        Обрабатывает одну запись (один видео-трек).
        Если with_metadata = True, добавляет метаданные и обложку.
        """
        downloads = info_dict.get('requested_downloads', [])
        if not downloads:
            return "Не удалось определить скачанный файл для одной из записей."

        downloaded_path = downloads[0]['filepath']
        if not os.path.exists(downloaded_path):
            return f"Файл не был скачан: {downloaded_path}"

        if self.with_metadata:
            base_name, _ = os.path.splitext(downloaded_path)
            webp_thumbnail = base_name + ".webp"
            thumbnail_path = None

            if os.path.exists(webp_thumbnail):
                thumbnail_path = convert_thumbnail(webp_thumbnail)

            meta_result = add_metadata(downloaded_path, info_dict, thumbnail_path)

            # Удаляем временные файлы миниатюр
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            if os.path.exists(webp_thumbnail):
                os.remove(webp_thumbnail)

            return f"Готово: {downloaded_path}. {meta_result}"
        else:
            # Если метаданные не нужны, возвращаем сообщение без встраивания обложки
            return f"Готово: {downloaded_path} (без метаданных)"

    def _progress_hook(self, d):
        """
        Хук для прогресса, вызывается yt_dlp.
        """
        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%').strip()
            try:
                p_val = float(p_str.replace('%', ''))
            except ValueError:
                p_val = 0.0
            self.progress_callback(p_val)

    def _ffmpeg_available(self):
        """
        Проверяет доступность ffmpeg по найденному пути.
        """
        return self.ffmpeg_path is not None and os.path.exists(self.ffmpeg_path)
