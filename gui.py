import os
import tkinter as tk
from tkinter import messagebox, ttk
from validators import is_valid_youtube_url
from downloader import Downloader

class YouTubeAudioDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Downloader")

        # Увеличиваем изначальный размер окна, чтобы элементы умещались
        self.root.geometry("750x550")

        # Создаём объект Style и выбираем тему (пример)
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        # Настройка кнопок (пример)
        self.style.configure(
            "Custom.TButton",
            font=("Helvetica", 10, "bold"),
            foreground="#333333",
            padding=6
        )

        # Настройка чекбокса
        self.style.configure(
            "Custom.TCheckbutton",
            font=("Helvetica", 9),
            foreground="#333333"
        )

        # Настройка прогрессбара
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor="#FFFFFF",
            background="#4CAF50"
        )

        # Очередь ссылок
        self.audio_queue = []
        self.download_folder = os.path.join(os.getcwd(), "Downloaded_Audio")

        self._init_ui()

        self.downloader = Downloader(
            download_folder=self.download_folder,
            log_callback=self.log,
            progress_callback=self.update_progress
        )

    def _init_ui(self):
        """
        Инициализация всех виджетов интерфейса.
        """
        # --- Верхняя строка: поле ввода и кнопка очистки ---
        input_frame = ttk.Frame(self.root, padding="5 5 5 5")
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="Введите ссылку на видео или плейлист:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(input_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5)

        clear_btn = ttk.Button(
            input_frame,
            text="✖",
            style="Custom.TButton",
            command=self.clear_input
        )
        clear_btn.pack(side=tk.LEFT)

        # Вместо биндов <Control-v> и проверки раскладки
        # используем единый обработчик <Control-KeyPress> и проверяем keycode
        self.url_entry.bind("<Control-KeyPress>", self.on_ctrl_keypress)
        # Также можно привязать Shift+Ctrl, если нужно:
        self.url_entry.bind("<Control-Shift-KeyPress>", self.on_ctrl_keypress)

        # --- Вторая строка: часть кнопок ---
        control_frame_1 = ttk.Frame(self.root, padding="5 5 5 5")
        control_frame_1.pack(fill=tk.X)

        ttk.Button(control_frame_1, text="Добавить в очередь", style="Custom.TButton",
                   command=self.add_to_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame_1, text="Удалить выбранное", style="Custom.TButton",
                   command=self.remove_selected_from_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame_1, text="Очистить очередь", style="Custom.TButton",
                   command=self.clear_queue).pack(side=tk.LEFT, padx=5)

        # --- Третья строка: оставшиеся кнопки + чекбокс ---
        control_frame_2 = ttk.Frame(self.root, padding="5 5 5 5")
        control_frame_2.pack(fill=tk.X)

        ttk.Button(control_frame_2, text="Скачать аудио", style="Custom.TButton",
                   command=self.start_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame_2, text="Остановить", style="Custom.TButton",
                   command=self.stop_download).pack(side=tk.LEFT, padx=5)

        # Чекбокс «Скачать с метаданными?»
        self.metadata_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame_2, text="Скачать с метаданными?",
                        style="Custom.TCheckbutton",
                        variable=self.metadata_var).pack(side=tk.LEFT, padx=5)

        # --- Средняя часть: список очереди и логи ---
        middle_frame = ttk.Frame(self.root, padding="5 5 5 5")
        middle_frame.pack(fill="both", expand=True)

        queue_frame = ttk.Frame(middle_frame, relief=tk.GROOVE)
        queue_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
        ttk.Label(queue_frame, text="Очередь ссылок:").pack()
        self.queue_listbox = tk.Listbox(queue_frame, width=50, height=15, selectmode=tk.SINGLE)
        self.queue_listbox.pack(padx=5, pady=5, fill="both", expand=True)

        log_frame = ttk.Frame(middle_frame, relief=tk.GROOVE)
        log_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=5, pady=5)
        ttk.Label(log_frame, text="Логи:").pack()
        self.log_text = tk.Text(log_frame, width=50, height=15, state="disabled")
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

        # --- Полоса прогресса ---
        ttk.Label(self.root, text="Прогресс загрузки:").pack(pady=5)
        self.progress = ttk.Progressbar(self.root, length=600, mode="determinate",
                                        style="Custom.Horizontal.TProgressbar")
        self.progress.pack(pady=5)

    # ------------------------------------------------------------------------
    #  Обработчик события <Control-KeyPress>
    #  Проверяем keycode: на Windows для физической клавиши V это 86,
    #  для A — 65. Таким образом вставка/выделение сработают в любой раскладке.
    # ------------------------------------------------------------------------
    def on_ctrl_keypress(self, event):
        """
        Универсальный обработчик Ctrl+V и Ctrl+A по физической клавише (Windows).
        """
        # Проверяем, что зажата клавиша Ctrl (бит 0x4 в event.state).
        # На Windows, keycode=86 => физическая 'V', keycode=65 => физическая 'A'.
        # При необходимости добавьте проверки для 'C', 'X' и т.д.
        if event.state & 4:
            if event.keycode == 86:  # V
                return self.paste_clipboard()
            elif event.keycode == 65:  # A
                return self.select_all_text()
        return None

    def paste_clipboard(self, event=None):
        """
        Вставка текста из буфера обмена, универсальная для любой раскладки.
        """
        try:
            clipboard_text = self.root.clipboard_get()
            self.url_entry.insert(tk.INSERT, clipboard_text)
        except tk.TclError:
            messagebox.showwarning("Ошибка", "Буфер обмена пуст.")
        return "break"

    def select_all_text(self, event=None):
        """
        Выделение всего текста в поле ввода.
        """
        self.url_entry.select_range(0, tk.END)
        self.url_entry.focus()
        return "break"

    # --- Остальные методы приложения ---

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def clear_input(self):
        self.url_entry.delete(0, tk.END)

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Ошибка", "Введите корректную ссылку!")
            return

        if not is_valid_youtube_url(url):
            messagebox.showwarning("Ошибка", "Ссылка не является ссылкой на YouTube!")
            return

        self.audio_queue.append(url)
        self.queue_listbox.insert(tk.END, url)
        self.log(f"Добавлено в очередь: {url}")
        self.url_entry.delete(0, tk.END)

    def remove_selected_from_queue(self):
        selected_index = self.queue_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            url = self.audio_queue.pop(index)
            self.queue_listbox.delete(index)
            self.log(f"Удалено из очереди: {url}")
        else:
            messagebox.showwarning("Ошибка", "Выберите ссылку для удаления!")

    def clear_queue(self):
        self.audio_queue.clear()
        self.queue_listbox.delete(0, tk.END)
        self.log("Очередь очищена.")

    def start_download(self):
        if not self.audio_queue:
            messagebox.showwarning("Ошибка", "Очередь пуста!")
            return

        # Устанавливаем флаг метаданных
        self.downloader.with_metadata = self.metadata_var.get()
        self.log("Начало загрузки...")
        self.downloader.start_download(self.audio_queue.copy(), self.on_all_downloads_complete)

    def stop_download(self):
        self.downloader.stop_download()

    def on_all_downloads_complete(self):
        self.root.after(0, self._downloads_finished)

    def _downloads_finished(self):
        self.progress["value"] = 0
        self.audio_queue.clear()
        self.queue_listbox.delete(0, tk.END)
        self.log("Все задачи завершены.")
        messagebox.showinfo("Готово", "Все аудио успешно скачаны!")

    def update_progress(self, value):
        self.root.after(0, lambda: self.progress.config(value=value))
