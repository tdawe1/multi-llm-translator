# Conceptual example
import threading
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log
from core import csv_handshake_worker, folder_monitor_worker

class TUI(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Log(id="log_view", auto_scroll=True)
        yield Footer()

    def on_mount(self) -> None:
        """Start the worker threads when the TUI mounts."""
        self.stop_event = threading.Event()
        self.csv_thread = threading.Thread(target=csv_handshake_worker, args=(self.stop_event,))
        self.folder_thread = threading.Thread(target=folder_monitor_worker, args=(self.stop_event,), daemon=True)
        self.csv_thread.start()
        self.folder_thread.start()

    def on_unmount(self) -> None:
        """Signal workers to stop when the TUI exits."""
        self.stop_event.set()
        self.csv_thread.join()

if __name__ == "__main__":
    app = TUI()
    app.run()