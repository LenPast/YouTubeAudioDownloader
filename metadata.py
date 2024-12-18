import os
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, error
from mutagen.mp3 import MP3

def convert_thumbnail(webp_path):
    """
    Конвертирует webp изображение в jpeg формат и возвращает путь к новому файлу.
    Если не удаётся открыть изображение, возвращает None.
    """
    if not os.path.exists(webp_path):
        return None
    try:
        img = Image.open(webp_path).convert("RGB")
        jpeg_path = webp_path.replace(".webp", ".jpg")
        img.save(jpeg_path, "JPEG")
        return jpeg_path
    except Exception:
        return None

def add_metadata(file_path, info, thumbnail_path):
    """
    Добавляет метаданные и обложку в MP3-файл.
    info - словарь, возвращаемый yt_dlp с информацией о треке.
    """
    if not os.path.exists(file_path):
        return "MP3 file not found."

    # Получаем теги или создаём, если их нет
    try:
        audio = MP3(file_path, ID3=ID3)
    except error:
        audio = MP3(file_path)
        audio.add_tags()

    # Добавление обложки, если есть
    if thumbnail_path and os.path.exists(thumbnail_path):
        with open(thumbnail_path, 'rb') as img:
            audio.tags.add(APIC(
                encoding=3,  # UTF-8
                mime='image/jpeg',
                type=3,  # Front cover
                desc='Cover',
                data=img.read()
            ))
    # Добавляем базовые метаданные
    title = info.get('title', 'Unknown Title')
    artist = info.get('uploader', 'Unknown Artist')
    album = info.get('playlist_title', 'YouTube Audio')

    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))
    audio.tags.add(TALB(encoding=3, text=album))

    audio.save(v2_version=3)
    return "Metadata added successfully."
