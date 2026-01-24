import sys
import os
import socket
import threading
import http.server
import socketserver
import urllib.parse
import shutil
import customtkinter as ctk
from PIL import Image, ImageTk 
from tkinter import messagebox

# --- НАСТРОЙКИ ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

httpd = None
TARGET_FILE_PATH = "" 

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def find_free_port(start_port=8000):
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('0.0.0.0', port)) != 0:
                return port
    return None

class SingleFileHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
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
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{encoded_filename}")
            self.end_headers()

            with open(TARGET_FILE_PATH, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
                
        except ConnectionResetError:
            pass
        except Exception as e:
            with open("error_log.txt", "a") as log:
                log.write(f"Error sending file: {e}\n")

def start_server_thread(ip, port, on_error_callback):
    global httpd
    try:
        # Привязываемся жестко к IP, а не к 0.0.0.0 (иногда помогает от фаервола)
        server_address = (ip, port)
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(server_address, SingleFileHandler) as server:
            httpd = server
            server.serve_forever()
    except OSError as e:
        if on_error_callback:
            on_error_callback(f"Ошибка порта {port}:\n{e}")

def stop_server_and_exit(app):
    global httpd
    if httpd:
        threading.Thread(target=httpd.shutdown, daemon=True).start()
    app.quit()
    sys.exit()

def main():
    global TARGET_FILE_PATH
    
    if len(sys.argv) < 2:
        root = ctk.CTk()
        root.withdraw()
        messagebox.showwarning("QR Share", "Запустите через ПКМ по файлу -> QR Share")
        return

    TARGET_FILE_PATH = sys.argv[1]
    if not os.path.exists(TARGET_FILE_PATH):
        return
        
    file_name = os.path.basename(TARGET_FILE_PATH)
    port = find_free_port(8000)
    if not port: return

    ip = get_local_ip()
    encoded_name_url = urllib.parse.quote(file_name)
    url = f"http://{ip}:{port}/{encoded_name_url}"

    # --- GUI ---
    app = ctk.CTk()
    app.title("QR Share")
    app.geometry("400x550")
    app.resizable(False, False)
    app.grid_columnconfigure(0, weight=1)

    lbl_title = ctk.CTkLabel(app, text="Сканируй для скачивания", font=("Roboto Medium", 20))
    lbl_title.grid(row=0, column=0, pady=(25, 15))

    import qrcode
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="white", back_color="transparent")
    qr_ctk_img = ctk.CTkImage(light_image=qr_img.get_image(), dark_image=qr_img.get_image(), size=(250, 250))
    
    lbl_qr = ctk.CTkLabel(app, image=qr_ctk_img, text="")
    lbl_qr.grid(row=1, column=0, pady=10)

    short_name = file_name if len(file_name) < 35 else file_name[:32] + "..."
    lbl_file = ctk.CTkLabel(app, text=short_name, text_color="gray", font=("Arial", 12))
    lbl_file.grid(row=2, column=0, pady=(5, 5))

    entry = ctk.CTkEntry(app, width=320, justify="center")
    entry.insert(0, url)
    entry.configure(state="readonly")
    entry.grid(row=3, column=0, pady=10)

    lbl_status = ctk.CTkLabel(app, text=f"● Раздается (Порт: {port})", text_color="#4CAF50", font=("Arial", 12, "bold"))
    lbl_status.grid(row=4, column=0, pady=(5, 20))

    btn_stop = ctk.CTkButton(app, text="Остановить", fg_color="#CD3838", hover_color="#A82A2A",
                             height=40, width=200, command=lambda: stop_server_and_exit(app))
    btn_stop.grid(row=5, column=0)

    # Передаем IP в функцию запуска
    threading.Thread(target=start_server_thread, args=(ip, port, messagebox.showerror), daemon=True).start()

    app.protocol("WM_DELETE_WINDOW", lambda: stop_server_and_exit(app))
    app.mainloop()

if __name__ == "__main__":
    main()