import re

def is_valid_youtube_url(url):
    """
    Проверяет, что переданный URL является ссылкой на YouTube или плейлист YouTube.
    """
    # Можно расширить, добавив проверку на youtube.com, youtu.be, а также различные варианты URL.
    youtube_regex = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$")
    return bool(youtube_regex.match(url))

def sanitize_filename(name):
    """
    Очищает имя файла от недопустимых символов для файловой системы.
    Заменяет недопустимые символы на символ '_'.
    """
    return re.sub(r'[\\/:"*?<>|]+', '_', name)
