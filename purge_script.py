                                                                             
 #              ##     ##                   #                                
 #               #      #                   #                                
 # ##    ###     #      #     ###    ###   ####          #   #  #   #  ##### 
 ##  #  #   #    #      #    #   #      #   #             # #   #   #     #  
 #   #  #####    #      #    #       ####   #              #    #  ##    #   
 #   #  #        #      #    #   #  #   #   #  #          # #    ## #   #    
 #   #   ###    ###    ###    ###    ####    ##          #   #      #  ##### 
                                                  #####         #   #        
                                                                 ###         


import tkinter as tk
from tkinter import messagebox, ttk
import requests
import threading
import re
import time
from PIL import Image, ImageTk

stop_flag = False
proxy_settings = {
    'http': [],
    'https': [],
    'socks5': []
}
current_theme = 'azure-dark'
style = None

class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, on_image, off_image, command=None, *args, **kwargs):
        super().__init__(parent, width=50, height=25, *args, **kwargs)
        self.on_image = ImageTk.PhotoImage(Image.open(on_image))
        self.off_image = ImageTk.PhotoImage(Image.open(off_image))
        self.command = command
        self.state = False
        self.create_image(0, 0, anchor='nw', image=self.off_image)
        self.bind("<Button-1>", self.toggle)

    def toggle(self, event=None):
        self.state = not self.state
        self.create_image(0, 0, anchor='nw', image=self.on_image if self.state else self.off_image)
        if self.command:
            self.command(self.state)

def switch_theme(state):
    global current_theme, style
    new_theme = 'azure-light' if current_theme == 'azure-dark' else 'azure-dark'
    current_theme = new_theme
    style.theme_use(new_theme)
    app.tk.call('set_theme', 'light' if current_theme == 'azure-light' else 'dark')
    load_toggle_images()

def load_toggle_images():
    if current_theme == 'azure-dark':
        on_image = 'themes/azure/on_basic.png'
        off_image = 'themes/azure/off_basic.png'
    else:
        on_image = 'themes/azure/on_accent.png'
        off_image = 'themes/azure/off_basic.png'

    mode_switch.on_image = ImageTk.PhotoImage(Image.open(on_image))
    mode_switch.off_image = ImageTk.PhotoImage(Image.open(off_image))
    mode_switch.create_image(0, 0, anchor='nw', image=mode_switch.on_image if mode_switch.state else mode_switch.off_image)

def show_donation_info():
    ltc_address = "LTDKCv6J1Lupi9cieC652nyRzGsg2Pt6H8"
    messagebox.showinfo("Donate", f"Donate LTC to:\n{ltc_address}")

def purge_messages(channel_id, filters, progress_callback, token, delay, num_messages, proxies=None, log_messages=None):
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
    }

    base_url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    before = None
    total_deleted = 0

    while total_deleted < num_messages and not stop_flag:
        try:
            url = f"{base_url}?before={before}" if before else base_url
            response = requests.get(url, headers=headers, proxies=proxies)
            messages = response.json()

            if not messages:
                break

            for message in messages:
                if all(re.search(filter['regex'], message['content']) for filter in filters):
                    requests.delete(f"{base_url}/{message['id']}", headers=headers, proxies=proxies)
                    total_deleted += 1
                    progress_callback(total_deleted)
                    time.sleep(delay)

                    if log_messages:
                        log_messages.append(f"Deleted message: {message['content']} (ID: {message['id']})")

                    if total_deleted >= num_messages or stop_flag:
                        break

            before = messages[-1]['id']

        except Exception as e:
            time.sleep(5)
            continue

    return total_deleted

def start_purging(channels, dms, progress_callback, token, delay, num_messages, webhook_url=None, proxies=None):
    total_deleted = 0
    log_messages = []

    for channel_id in channels:
        if total_deleted >= num_messages or stop_flag:
            break
        total_deleted += purge_messages(channel_id, [], progress_callback, token, delay, num_messages - total_deleted, proxies, log_messages)

    for dm_id in dms:
        if total_deleted >= num_messages or stop_flag:
            break
        response = requests.get("https://discord.com/api/v9/users/@me/channels", headers={'Authorization': token}, proxies=proxies)
        channels = response.json()
        dm_channel = next((channel for channel in channels if channel['recipients'][0]['id'] == dm_id), None)
        if dm_channel:
            total_deleted += purge_messages(dm_channel['id'], [], progress_callback, token, delay, num_messages - total_deleted, proxies, log_messages)

    log_results(log_messages, webhook_url)
    messagebox.showinfo("Purge Complete", f"Total messages deleted: {total_deleted}")

def log_results(log_messages, webhook_url):
    if webhook_url:
        send_to_webhook(log_messages, webhook_url)
    else:
        save_to_file(log_messages)

def send_to_webhook(log_messages, webhook_url):
    headers = {'Content-Type': 'application/json'}
    for message in log_messages:
        payload = {'content': message}
        requests.post(webhook_url, headers=headers, json=payload)

def save_to_file(log_messages):
    with open('deleted_messages_log.txt', 'w') as file:
        for message in log_messages:
            file.write(f"{message}\n")

def start_purge_thread(channels, dms, token, delay, num_messages, webhook_url, proxies=None):
    global stop_flag
    stop_flag = False
    threading.Thread(target=start_purging, args=(channels, dms, update_progress, token, delay, num_messages, webhook_url, proxies)).start()

def stop_purging():
    global stop_flag
    stop_flag = True
    messagebox.showinfo("Purge Stopped", "The purge process has been stopped.")

def update_progress(total_deleted):
    progress_label.config(text=f"Progress: {total_deleted} messages deleted")
    progress_bar['value'] = total_deleted
    app.update_idletasks()
    log_text.config(state='normal')
    log_text.insert(tk.END, f"{total_deleted} messages deleted\n")
    log_text.config(state='disabled')
    log_text.yview(tk.END)

def validate_token(token):
    try:
        response = requests.get("https://discord.com/api/v9/users/@me", headers={'Authorization': token})
        return response.status_code == 200
    except Exception as e:
        return False

def validate_and_enable_inputs(event=None):
    token = token_entry.get()
    if not validate_token(token):
        messagebox.showerror("Invalid Token", "The provided Discord token is invalid.")
        channel_id_entry.config(state='disabled')
        dm_id_entry.config(state='disabled')
        start_button.config(state='disabled')
    else:
        channel_id_entry.config(state='normal')
        dm_id_entry.config(state='normal')
        start_button.config(state='normal')

def start_purge():
    token = token_entry.get()
    webhook_url = webhook_entry.get()
    num_messages = int(num_messages_entry.get())
    if not token:
        messagebox.showerror("Error", "Please enter a Discord token.")
        return

    if not validate_token(token):
        messagebox.showerror("Invalid Token", "The provided Discord token is invalid.")
        return

    proxies = load_proxies() if mode_switch.state else None
    channels = [channel_id.strip() for channel_id in channel_id_entry.get().split(",") if channel_id.strip()]
    dms = [dm_id.strip() for dm_id in dm_id_entry.get().split(",") if dm_id.strip()]
    start_purge_thread(channels, dms, token, 0 if mode_switch.state else 0.1, num_messages, webhook_url, proxies)

def load_proxies():
    proxies = {
        'http': [],
        'https': [],
        'socks5': []
    }

    for proxy in proxy_settings['http']:
        proxies['http'].append(f"http://{proxy}")

    for proxy in proxy_settings['https']:
        proxies['https'].append(f"https://{proxy}")

    for proxy in proxy_settings['socks5']:
        proxies['socks5'].append(f"socks5://{proxy}")

    return proxies if proxies['http'] or proxies['https'] or proxies['socks5'] else None

def open_proxy_settings():
    def save_proxy_settings():
        proxy_settings['http'] = [proxy.strip() for proxy in http_text.get("1.0", "end").split("\n") if proxy.strip()]
        proxy_settings['https'] = [proxy.strip() for proxy in https_text.get("1.0", "end").split("\n") if proxy.strip()]
        proxy_settings['socks5'] = [proxy.strip() for proxy in socks5_text.get("1.0", "end").split("\n") if proxy.strip()]
        proxy_window.destroy()

    proxy_window = tk.Toplevel(app)
    proxy_window.title("Proxy Settings")

    tk.Label(proxy_window, text="HTTP Proxies:").grid(row=0, column=0)
    http_text = tk.Text(proxy_window, height=5, width=50)
    http_text.grid(row=0, column=1)

    tk.Label(proxy_window, text="HTTPS Proxies:").grid(row=1, column=0)
    https_text = tk.Text(proxy_window, height=5, width=50)
    https_text.grid(row=1, column=1)

    tk.Label(proxy_window, text="SOCKS5 Proxies:").grid(row=2, column=0)
    socks5_text = tk.Text(proxy_window, height=5, width=50)
    socks5_text.grid(row=2, column=1)

    save_button = tk.Button(proxy_window, text="Save", command=save_proxy_settings)
    save_button.grid(row=3, column=0, columnspan=2)

app = tk.Tk()
app.title("Discord Message Purger")

app.tk.call('source', 'themes/azure.tcl')
app.tk.call('set_theme', 'dark')
style = ttk.Style(app)
style.theme_use(current_theme)

tk.Label(app, text="Discord Token:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
token_entry = tk.Entry(app, width=50, show='*')
token_entry.grid(row=0, column=1, padx=10, pady=5)
token_entry.bind("<FocusOut>", validate_and_enable_inputs)
token_entry.bind("<Return>", validate_and_enable_inputs)
token_entry.bind("<KeyRelease>", validate_and_enable_inputs)

tk.Label(app, text="Channel ID(s):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
channel_id_entry = tk.Entry(app, width=50, state='disabled')
channel_id_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Label(app, text="DM ID(s):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
dm_id_entry = tk.Entry(app, width=50, state='disabled')
dm_id_entry.grid(row=2, column=1, padx=10, pady=5)

tk.Label(app, text="Number of Messages:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
num_messages_entry = tk.Entry(app, width=50)
num_messages_entry.grid(row=3, column=1, padx=10, pady=5)
num_messages_entry.insert(0, "100")

tk.Label(app, text="Webhook URL (optional):").grid(row=4, column=0, padx=10, pady=5, sticky="e")
webhook_entry = tk.Entry(app, width=50)
webhook_entry.grid(row=4, column=1, padx=10, pady=5)

start_button = tk.Button(app, text="Start Purge", state='disabled', command=start_purge)
start_button.grid(row=5, column=0, columnspan=2, pady=10)

stop_button = tk.Button(app, text="Stop Purge", command=stop_purging)
stop_button.grid(row=6, column=0, columnspan=2, pady=10)

progress_label = tk.Label(app, text="Progress: 0 messages deleted")
progress_label.grid(row=7, column=0, columnspan=2, pady=5)

progress_bar = ttk.Progressbar(app, length=400, mode='determinate')
progress_bar.grid(row=8, column=0, columnspan=2, pady=5)

log_text = tk.Text(app, height=10, state='disabled')
log_text.grid(row=9, column=0, columnspan=2, pady=5)

proxy_button = tk.Button(app, text="Proxy Settings", command=open_proxy_settings)
proxy_button.grid(row=10, column=0, columnspan=2, pady=5)

mode_switch = ToggleSwitch(app, 'themes/azure/on_basic.png', 'themes/azure/off_basic.png', command=switch_theme)
mode_switch.grid(row=11, column=0, columnspan=2, pady=10)

load_toggle_images()

app.mainloop()
