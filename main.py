import http.server
import os
import shutil
import socket
import socketserver
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import qrcode


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "QR Share"
LOG_PATH = Path(tempfile.gettempdir()) / "qr_share_error_log.txt"

BACKGROUND_COLOR = "#0B1220"
SURFACE_COLOR = "#121C2E"
SURFACE_ALT_COLOR = "#17253B"
ACCENT_COLOR = "#38BDF8"
ACCENT_HOVER_COLOR = "#0EA5E9"
SUCCESS_COLOR = "#22C55E"
SUCCESS_SURFACE_COLOR = "#0F2B1D"
TEXT_PRIMARY = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
TEXT_SUBTLE = "#64748B"
STOP_COLOR = "#EF4444"
STOP_HOVER_COLOR = "#DC2626"

httpd = None
TARGET_FILE_PATH = ""


def append_error_log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(f"{message}\n")


def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def find_free_port(ip: str, start_port: int = 8000) -> int | None:
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((ip, port))
                return port
            except OSError:
                continue
    return None


def format_file_size(file_size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(file_size)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            precision = 0 if unit == "B" else 1
            return f"{size:.{precision}f} {unit}"
        size /= 1024
    return f"{file_size} B"


def truncate_middle(text: str, max_length: int = 54) -> str:
    if len(text) <= max_length:
        return text
    head = max_length // 2 - 2
    tail = max_length - head - 3
    return f"{text[:head]}...{text[-tail:]}"


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class SingleFileHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        global TARGET_FILE_PATH

        try:
            if not os.path.exists(TARGET_FILE_PATH):
                self.send_error(404, "File not found")
                return

            file_size = os.path.getsize(TARGET_FILE_PATH)
            filename = os.path.basename(TARGET_FILE_PATH)
            encoded_filename = urllib.parse.quote(filename)

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(file_size))
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{encoded_filename}",
            )
            self.end_headers()

            with open(TARGET_FILE_PATH, "rb") as source:
                shutil.copyfileobj(source, self.wfile)
        except ConnectionResetError:
            pass
        except OSError as error:
            append_error_log(f"Send file error: {error}")


def start_server_thread(ip: str, port: int, on_error_callback) -> None:
    global httpd

    try:
        with ThreadedTCPServer((ip, port), SingleFileHandler) as server:
            httpd = server
            server.serve_forever()
    except OSError as error:
        if on_error_callback:
            on_error_callback(f"Не удалось открыть порт {port}.\n{error}")


def stop_server() -> None:
    global httpd

    server = httpd
    httpd = None
    if server is not None:
        threading.Thread(target=server.shutdown, daemon=True).start()


class ShareWindow(ctk.CTk):
    def __init__(self, file_path: str, url: str, ip: str, port: int) -> None:
        super().__init__()

        self.file_path = Path(file_path)
        self.url = url
        self.ip = ip
        self.port = port
        self.file_name = self.file_path.name
        self.file_size = format_file_size(self.file_path.stat().st_size)

        self.title(APP_TITLE)
        self.geometry("520x760")
        self.resizable(False, False)
        self.configure(fg_color=BACKGROUND_COLOR)
        self.grid_columnconfigure(0, weight=1)

        self.copy_button = None
        self.status_label = None
        self.url_entry = None
        self.qr_image = self._build_qr_image()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.handle_close)

    def _build_qr_image(self) -> ctk.CTkImage:
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(self.url)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white").get_image().convert("RGB")
        return ctk.CTkImage(light_image=qr_image, dark_image=qr_image, size=(270, 270))

    def _build_ui(self) -> None:
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        outer.grid_columnconfigure(0, weight=1)

        qr_card = ctk.CTkFrame(outer, fg_color=SURFACE_COLOR, corner_radius=26)
        qr_card.grid(row=0, column=0, sticky="ew")
        qr_card.grid_columnconfigure(0, weight=1)

        brand_chip = ctk.CTkFrame(qr_card, fg_color="#0F1A2D", corner_radius=999)
        brand_chip.grid(row=0, column=0, pady=(20, 10))
        ctk.CTkLabel(
            brand_chip,
            text=APP_TITLE,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=ACCENT_COLOR,
        ).grid(row=0, column=0, padx=14, pady=7)

        qr_surface = ctk.CTkFrame(qr_card, fg_color="#FFFFFF", corner_radius=26)
        qr_surface.grid(row=1, column=0, pady=(0, 16))
        ctk.CTkLabel(qr_surface, text="", image=self.qr_image).grid(row=0, column=0, padx=18, pady=18)

        ctk.CTkLabel(
            qr_card,
            text="Сканируйте для скачивания",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=2, column=0, pady=(0, 6))

        ctk.CTkLabel(
            qr_card,
            text="Откройте камеру на телефоне и перейдите по ссылке из QR-кода.",
            justify="center",
            wraplength=410,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=TEXT_MUTED,
        ).grid(row=3, column=0, padx=28)

        status_frame = ctk.CTkFrame(
            qr_card,
            fg_color=SUCCESS_SURFACE_COLOR,
            corner_radius=999,
        )
        status_frame.grid(row=4, column=0, pady=(16, 10))
        self.status_label = ctk.CTkLabel(
            status_frame,
            text=f"Сервер активен  |  Порт {self.port}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=SUCCESS_COLOR,
        )
        self.status_label.grid(row=0, column=0, padx=14, pady=8)

        ctk.CTkLabel(
            qr_card,
            text="Устройства должны быть в одной сети Wi-Fi или LAN.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_SUBTLE,
        ).grid(row=5, column=0, pady=(0, 20))

        info_card = ctk.CTkFrame(outer, fg_color=SURFACE_ALT_COLOR, corner_radius=22)
        info_card.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        info_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            info_card,
            text="Файл",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_SUBTLE,
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 6))

        ctk.CTkLabel(
            info_card,
            text=self.file_name,
            anchor="w",
            justify="left",
            wraplength=420,
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=1, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(
            info_card,
            text=f"{self.file_size}  |  {truncate_middle(str(self.file_path), 62)}",
            anchor="w",
            justify="left",
            wraplength=420,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 18))

        link_card = ctk.CTkFrame(outer, fg_color=SURFACE_ALT_COLOR, corner_radius=22)
        link_card.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        link_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            link_card,
            text="Ссылка для скачивания",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_SUBTLE,
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))

        link_row = ctk.CTkFrame(link_card, fg_color="transparent")
        link_row.grid(row=1, column=0, sticky="ew", padx=20)
        link_row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            link_row,
            height=42,
            corner_radius=14,
            border_width=0,
            fg_color=SURFACE_COLOR,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.insert(0, self.url)
        self.url_entry.configure(state="readonly")

        self.copy_button = ctk.CTkButton(
            link_row,
            text="Копировать",
            width=118,
            height=42,
            corner_radius=14,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self.copy_link,
        )
        self.copy_button.grid(row=0, column=1)

        info_row = ctk.CTkFrame(link_card, fg_color="transparent")
        info_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 18))
        info_row.grid_columnconfigure((0, 1), weight=1)

        self._build_info_chip(info_row, 0, f"IP: {self.ip}")
        self._build_info_chip(info_row, 1, f"Порт: {self.port}")

        actions = ctk.CTkFrame(outer, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        actions.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            actions,
            text="Открыть папку",
            height=46,
            corner_radius=16,
            fg_color=SURFACE_ALT_COLOR,
            hover_color="#22324C",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self.open_folder,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="Копировать путь",
            height=46,
            corner_radius=16,
            fg_color=SURFACE_ALT_COLOR,
            hover_color="#22324C",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self.copy_path,
        ).grid(row=0, column=1, sticky="ew", padx=8)

        ctk.CTkButton(
            actions,
            text="Остановить",
            height=46,
            corner_radius=16,
            fg_color=STOP_COLOR,
            hover_color=STOP_HOVER_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self.handle_close,
        ).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        ctk.CTkLabel(
            outer,
            text="Если телефон не открывает страницу, проверьте, что ПК и телефон подключены к одной сети.",
            justify="left",
            wraplength=460,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_SUBTLE,
        ).grid(row=4, column=0, sticky="w", pady=(16, 0), padx=4)

    def _build_info_chip(self, parent: ctk.CTkFrame, column: int, text: str) -> None:
        chip = ctk.CTkFrame(parent, fg_color=SURFACE_COLOR, corner_radius=999)
        chip.grid(row=0, column=column, sticky="w", padx=(0, 10) if column == 0 else 0)
        ctk.CTkLabel(
            chip,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, padx=12, pady=7)

    def set_status(self, text: str, color: str) -> None:
        if self.status_label is not None:
            self.status_label.configure(text=text, text_color=color)

    def copy_link(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.url)
        self.update()
        self.copy_button.configure(text="Скопировано")
        self.after(1800, lambda: self.copy_button.configure(text="Копировать"))

    def copy_path(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(str(self.file_path))
        self.update()
        self.set_status("Путь к файлу скопирован", ACCENT_COLOR)
        self.after(1800, lambda: self.set_status(f"Сервер активен  |  Порт {self.port}", SUCCESS_COLOR))

    def open_folder(self) -> None:
        os.startfile(self.file_path.parent)

    def handle_close(self) -> None:
        stop_server()
        self.destroy()

    def show_start_error(self, message: str) -> None:
        self.after(0, lambda: self._show_start_error(message))

    def _show_start_error(self, message: str) -> None:
        self.set_status("Ошибка запуска сервера", STOP_COLOR)
        messagebox.showerror(APP_TITLE, message)


def show_warning_and_exit(message: str) -> None:
    root = ctk.CTk()
    root.withdraw()
    messagebox.showwarning(APP_TITLE, message)
    root.destroy()


def show_error_and_exit(message: str) -> None:
    root = ctk.CTk()
    root.withdraw()
    messagebox.showerror(APP_TITLE, message)
    root.destroy()


def main() -> None:
    global TARGET_FILE_PATH

    if len(sys.argv) < 2:
        show_warning_and_exit("Запустите приложение из контекстного меню файла.")
        return

    TARGET_FILE_PATH = sys.argv[1]
    if not os.path.exists(TARGET_FILE_PATH):
        show_error_and_exit("Выбранный файл не найден.")
        return

    ip = get_local_ip()
    port = find_free_port(ip, 8000)
    if port is None:
        show_error_and_exit("Не удалось найти свободный порт в диапазоне 8000-8099.")
        return

    file_name = os.path.basename(TARGET_FILE_PATH)
    encoded_name_url = urllib.parse.quote(file_name)
    url = f"http://{ip}:{port}/{encoded_name_url}"

    app = ShareWindow(TARGET_FILE_PATH, url, ip, port)

    threading.Thread(
        target=start_server_thread,
        args=(ip, port, app.show_start_error),
        daemon=True,
    ).start()

    app.mainloop()


if __name__ == "__main__":
    main()
