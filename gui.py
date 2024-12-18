import os
import tkinter as tk
from tkinter import messagebox, ttk
from validators import is_valid_youtube_url
from downloader import Downloader

class YouTubeAudioDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Downloader")
        self.root.geometry("700x500")

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
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=5)

        tk.Label(input_frame, text="Введите ссылку на видео или плейлист:").pack(side=tk.LEFT, padx=5)
        self.url_entry = tk.Entry(input_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="✖", command=self.clear_input, fg="red").pack(side=tk.LEFT)

        # Вместо биндов для каждого символа, делаем общий бинд на Control-KeyPress
        self.url_entry.bind("<Control-KeyPress>", self.on_ctrl_keypress)
        # Дополнительно поддержим Ctrl+Insert для вставки
        self.url_entry.bind("<Control-Insert>", self.paste_clipboard)

        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=5)
        tk.Button(control_frame, text="Добавить в очередь", command=self.add_to_queue).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Удалить выбранное", command=self.remove_selected_from_queue).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Очистить очередь", command=self.clear_queue).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Скачать аудио", command=self.start_download).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Остановить", command=self.stop_download, fg="red").pack(side=tk.LEFT, padx=5)

        middle_frame = tk.Frame(self.root)
        middle_frame.pack(fill="both", expand=True)

        queue_frame = tk.Frame(middle_frame, bd=2, relief=tk.GROOVE)
        queue_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
        tk.Label(queue_frame, text="Очередь ссылок:").pack()
        self.queue_listbox = tk.Listbox(queue_frame, width=50, height=15, selectmode=tk.SINGLE)
        self.queue_listbox.pack(padx=5, pady=5, fill="both", expand=True)

        log_frame = tk.Frame(middle_frame, bd=2, relief=tk.GROOVE)
        log_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=5, pady=5)
        tk.Label(log_frame, text="Логи:").pack()
        self.log_text = tk.Text(log_frame, width=50, height=15, state="disabled")
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

        tk.Label(self.root, text="Прогресс загрузки:").pack(pady=5)
        self.progress = ttk.Progressbar(self.root, length=600, mode="determinate")
        self.progress.pack(pady=5)

    def on_ctrl_keypress(self, event):
        """
        Обработчик нажатия клавиши с контролом.
        Проверяем event.keysym и в зависимости от символа вызываем нужное действие.
        """
        # Проверяем keysym (имя клавиши) в нижнем регистре
        k = event.keysym.lower()

        # Вставка: на английской раскладке 'v', на русской может быть 'м' или другой символ.
        # Предполагая что на месте 'v' в русской раскладке 'м':
        if k in ('v', 'м'):
            return self.paste_clipboard(event)

        # Выделить всё: на английской 'a', на русской может быть 'ф'
        # (если пользователь пожелает поддерживать select all и на русской раскладке).
        if k in ('a', 'ф'):
            return self.select_all_text(event)

        # Если ни одна из горячих клавиш не совпала, не прерываем обработку события.
        return None

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def clear_input(self):
        self.url_entry.delete(0, tk.END)

    def paste_clipboard(self, event=None):
        """Вставка текста из буфера обмена."""
        try:
            clipboard_text = self.root.clipboard_get()
            self.url_entry.insert(tk.END, clipboard_text)
        except tk.TclError:
            messagebox.showwarning("Ошибка", "Буфер обмена пуст.")
        return "break"

    def select_all_text(self, event=None):
        """Выделение всего текста в поле ввода."""
        self.url_entry.select_range(0, tk.END)
        return "break"

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
