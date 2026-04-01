import sys
import os
import threading
import time
import random
import string
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QFileDialog, QPlainTextEdit, 
                             QProgressBar, QSpinBox, QFrame, QGridLayout, QTabWidget,
                             QComboBox, QCheckBox, QTextEdit, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon

# Import logic from autoshopify
try:
    import autoshopify
except ImportError:
    pass


class StripeWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(dict)
    log = pyqtSignal(dict) # Changed to dict to pass status
    
    def __init__(self, cc_file, threads):
        super().__init__()
        self.cc_file = cc_file
        self.threads = threads
        self._is_running = True

    def run(self):
        try:
            try:
                with open(self.cc_file, 'r') as f:
                    cards = [line.strip() for line in f if line.strip() and '|' in line and len(line.split('|')) >= 4]
            except Exception as e:
                self.log.emit({"msg": f"Error reading file: {e}", "status": "ERROR"})
                self.finished.emit()
                return

            if not cards:
                self.log.emit({"msg": "No valid cards found.", "status": "ERROR"})
                self.finished.emit()
                return

            total = len(cards)
            self.log.emit({"msg": f"Checking {total} cards using Custom Stripe API", "status": "INFO"})
            self.log.emit({"msg": f"Threads: {self.threads}", "status": "INFO"})
            self.log.emit({"msg": "=" * 60, "status": "INFO"})
            
            stats = {"total": total, "charged": 0, "declined": 0, "error": 0, "processed": 0}
            self.progress.emit(stats)

            tasks = [(card, i, total) for i, card in enumerate(cards, 1)]
            
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                futures = {executor.submit(autoshopify.process_card, task): task for task in tasks}
                
                for future in as_completed(futures):
                    if not self._is_running:
                        break
                    
                    try:
                        result = future.result()
                        idx, tot, card_display, res_status, res_msg, res_price = result[:6]
                        
                        emoji = ''
                        if res_status == 'CHARGED':
                            stats["charged"] += 1
                            emoji = '✅'
                            # Auto-save
                            with open("charged.txt", "a") as f:
                                f.write(f"{card_display}\n")
                        elif res_status == 'DECLINED':
                            stats["declined"] += 1
                            emoji = '❌'
                        else:
                            stats["error"] += 1
                            emoji = '⚠️'
                        
                        stats["processed"] += 1
                        self.log.emit({
                            "msg": f"[{idx}/{tot}] {card_display} | {res_msg} | {res_status} {emoji}",
                            "status": res_status,
                            "card": card_display if res_status == 'CHARGED' else None
                        })
                        self.progress.emit(stats)
                        
                    except Exception as e:
                        self.log.emit({"msg": f"Thread error: {e}", "status": "ERROR"})

            self.log.emit({"msg": "=" * 60, "status": "INFO"})
            self.log.emit({"msg": f"Done! Charged: {stats['charged']}/{total}", "status": "INFO"})
            
        except Exception as e:
            self.log.emit({"msg": f"Fatal error: {e}", "status": "ERROR"})
        finally:
            self.finished.emit()

    def stop(self):
        self._is_running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stripe API Checker - Premium Edition")
        self.setMinimumSize(1100, 850)
        self.setup_ui()
        self.worker_thread = None
        self.worker = None

    def setup_ui(self):
        self.setStyleSheet("""
            QMainWindow, QTabWidget::pane {
                background-color: #000000;
            }
            QWidget {
                color: #ffffff;
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #111111;
                border-radius: 10px;
                top: -1px;
            }
            QTabBar::tab {
                background: #000000;
                color: #555555;
                padding: 12px 35px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 5px;
                font-weight: bold;
                border: 1px solid #111111;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #000000;
                color: #00b4ff;
                border-bottom: 2px solid #00b4ff;
            }
            QLabel {
                font-weight: 500;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #000000;
                border: 1px solid #1a1a1a;
                padding: 12px;
                border-radius: 8px;
                color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #00b4ff;
            }
            QPushButton {
                background-color: #00b4ff;
                border: none;
                color: #000000;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #33c3ff;
            }
            QPushButton#stopBtn {
                background-color: #ff3b30;
                color: white;
            }
            QPlainTextEdit, QTextEdit {
                background-color: #000000;
                border: 1px solid #111111;
                border-radius: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                color: #cccccc;
                padding: 10px;
            }
            QProgressBar {
                border: 1px solid #1a1a1a;
                border-radius: 10px;
                text-align: center;
                background-color: #000000;
                height: 10px;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: #00b4ff;
                border-radius: 10px;
            }
            QFrame#card {
                background-color: #000000;
                border: 1px solid #111111;
                border-radius: 15px;
            }
            QFrame#statCard {
                background-color: #000000;
                border: 1px solid #111111;
                border-radius: 12px;
                padding: 15px;
            }
            QCheckBox {
                spacing: 10px;
                font-size: 14px;
                font-weight: 500;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.setup_checker_tab()
        self.setup_generator_tab()

    def setup_checker_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        config_frame = QFrame()
        config_frame.setObjectName("card")
        config_layout = QGridLayout(config_frame)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setSpacing(15)

        config_layout.addWidget(QLabel("Cards (Paste):"), 0, 0)
        self.cc_input = QPlainTextEdit()
        self.cc_input.setPlaceholderText("Paste cards here (NUMBER|MONTH|YEAR|CVV)")
        self.cc_input.setMaximumHeight(150)
        config_layout.addWidget(self.cc_input, 0, 1, 1, 2)

        config_layout.addWidget(QLabel("Or select File:"), 1, 0)
        self.cc_path_input = QLineEdit()
        self.cc_path_input.setPlaceholderText("Optional: Select .txt file")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.clicked.connect(self.browse_file)
        config_layout.addWidget(self.cc_path_input, 1, 1)
        config_layout.addWidget(self.browse_btn, 1, 2)

        config_layout.addWidget(QLabel("Threads:"), 2, 0)
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 100)
        self.thread_spin.setValue(10)
        config_layout.addWidget(self.thread_spin, 2, 1)

        layout.addWidget(config_frame)

        dash_frame = QFrame()
        dash_layout = QHBoxLayout(dash_frame)
        dash_layout.setSpacing(15)
        
        self.total_lbl = self.create_stat_card("TOTAL", "0", "#94a3b8")
        self.charged_lbl = self.create_stat_card("CHARGED", "0", "#22c55e")
        self.declined_lbl = self.create_stat_card("DECLINED", "0", "#ef4444")
        self.error_lbl = self.create_stat_card("ERROR", "0", "#f59e0b")

        dash_layout.addWidget(self.total_lbl)
        dash_layout.addWidget(self.charged_lbl)
        dash_layout.addWidget(self.declined_lbl)
        dash_layout.addWidget(self.error_lbl)
        layout.addWidget(dash_frame)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Log & Results Splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Main Logs
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Main logs will appear here...")
        
        # Live Results
        self.live_output = QTextEdit()
        self.live_output.setReadOnly(True)
        self.live_output.setPlaceholderText("CHARGED cards will appear here...")
        self.live_output.setStyleSheet("color: #22c55e; border: 1px solid #22c55e;")
        
        splitter.addWidget(self.log_output)
        splitter.addWidget(self.live_output)
        splitter.setSizes([700, 300])
        
        layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START CHECKING")
        self.start_btn.clicked.connect(self.start_checking)
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_checking)
        self.clear_btn = QPushButton("CLEAR LOGS")
        self.clear_btn.setStyleSheet("background-color: #334155; color: white;")
        self.clear_btn.clicked.connect(self.clear_all_logs)

        btn_layout.addWidget(self.start_btn, 3)
        btn_layout.addWidget(self.stop_btn, 1)
        btn_layout.addWidget(self.clear_btn, 1)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "CHECKER")
        self.setup_generator_tab()

    def clear_all_logs(self):
        self.log_output.clear()
        self.live_output.clear()

    def setup_generator_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        gen_frame = QFrame()
        gen_frame.setObjectName("card")
        gen_layout = QGridLayout(gen_frame)
        gen_layout.setContentsMargins(20, 20, 20, 20)
        gen_layout.setSpacing(15)

        gen_layout.addWidget(QLabel("BIN:"), 0, 0)
        self.bin_input = QLineEdit()
        self.bin_input.setPlaceholderText("e.g. 453271")
        gen_layout.addWidget(self.bin_input, 0, 1)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Custom", "Visa (453271)", "MasterCard (512345)", "UnionPay (622126)"])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_change)
        gen_layout.addWidget(self.preset_combo, 0, 2)

        gen_layout.addWidget(QLabel("Month:"), 1, 0)
        self.month_input = QLineEdit()
        self.month_input.setPlaceholderText("Random")
        gen_layout.addWidget(self.month_input, 1, 1)
        
        gen_layout.addWidget(QLabel("Year:"), 1, 2)
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Random (e.g. 28)")
        gen_layout.addWidget(self.year_input, 1, 3)

        gen_layout.addWidget(QLabel("CVV:"), 2, 0)
        self.cvv_input = QLineEdit()
        self.cvv_input.setPlaceholderText("Random")
        gen_layout.addWidget(self.cvv_input, 2, 1)

        gen_layout.addWidget(QLabel("Quantity:"), 2, 2)
        self.gen_qty = QSpinBox()
        self.gen_qty.setRange(1, 1000)
        self.gen_qty.setValue(10)
        gen_layout.addWidget(self.gen_qty, 2, 3)

        layout.addWidget(gen_frame)

        self.gen_output = QPlainTextEdit()
        self.gen_output.setPlaceholderText("Generated cards will appear here...")
        layout.addWidget(self.gen_output)

        btn_layout = QHBoxLayout()
        self.gen_btn = QPushButton("GENERATE CARDS")
        self.gen_btn.clicked.connect(self.generate_cards)
        
        self.copy_btn = QPushButton("COPY ALL")
        self.copy_btn.setStyleSheet("background-color: #334155; color: white;")
        self.copy_btn.clicked.connect(self.copy_generated)

        self.save_btn = QPushButton("SAVE TO FILE")
        self.save_btn.setStyleSheet("background-color: #334155; color: white;")
        self.save_btn.clicked.connect(self.save_gen_file)

        self.check_now_btn = QPushButton("CHECK NOW")
        self.check_now_btn.setStyleSheet("background-color: #22c55e; color: #000000;")
        self.check_now_btn.clicked.connect(self.auto_check_generated)

        self.auto_start_check = QCheckBox("Auto-start checking after linking")
        self.auto_start_check.setChecked(True)

        btn_layout.addWidget(self.gen_btn, 2)
        btn_layout.addWidget(self.check_now_btn, 2)
        btn_layout.addWidget(self.copy_btn, 1)
        btn_layout.addWidget(self.save_btn, 1)
        layout.addLayout(btn_layout)
        layout.addWidget(self.auto_start_check)

        self.tabs.addTab(tab, "GENERATOR")

    def on_preset_change(self, idx):
        presets = ["", "453271", "512345", "622126"]
        if idx > 0:
            self.bin_input.setText(presets[idx])

    def generate_cards(self):
        bin_str = self.bin_input.text().strip()
        if not bin_str:
            bin_str = random.choice(["4", "5", "6"])
            
        qty = self.gen_qty.value()
        month_fix = self.month_input.text().strip()
        year_fix = self.year_input.text().strip()
        cvv_fix = self.cvv_input.text().strip()

        results = []
        for _ in range(qty):
            card = autoshopify.generate_card_number(bin_str)
            mm = month_fix if month_fix else f"{random.randint(1, 12):02d}"
            yy = year_fix if year_fix else f"{random.randint(25, 30)}"
            cvv = cvv_fix if cvv_fix else f"{random.randint(100, 999):03d}"
            results.append(f"{card}|{mm}|{yy}|{cvv}")
        
        self.gen_output.setPlainText("\n".join(results))

    def copy_generated(self):
        QApplication.clipboard().setText(self.gen_output.toPlainText())

    def save_gen_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Generated Cards", "", "Text Files (*.txt)")
        if filename:
            with open(filename, 'w') as f:
                f.write(self.gen_output.toPlainText())

    def auto_check_generated(self):
        content = self.gen_output.toPlainText().strip()
        if not content:
            return
        
        self.cc_input.setPlainText(content)
        self.cc_path_input.clear()
        self.tabs.setCurrentIndex(0)
        self.log({"msg": f"Auto-loaded {len(content.splitlines())} cards into Checker.", "status": "INFO"})
        
        if self.auto_start_check.isChecked():
            self.start_checking()

    def create_stat_card(self, title, value, color):
        frame = QFrame()
        frame.setObjectName("statCard")
        layout = QVBoxLayout(frame)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        title_lbl.setAlignment(Qt.AlignCenter)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        val_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)
        layout.addWidget(val_lbl)
        frame.value_label = val_lbl
        return frame

    def browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select CC File", "", "Text Files (*.txt);;All Files (*)")
        if filename:
            self.cc_path_input.setText(filename)

    def log(self, data):
        msg = data.get("msg", "")
        status = data.get("status", "INFO")
        card = data.get("card", None)
        
        color = "#cccccc"
        if status == 'CHARGED':
            color = "#22c55e" # Green
            self.live_output.append(card)
        elif status == 'DECLINED':
            color = "#ef4444" # Red
        elif status == 'ERROR':
            color = "#f59e0b" # Orange
        elif status == 'INFO':
            color = "#00b4ff" # Blue
            
        html = f'<span style="color: {color};">{msg}</span>'
        self.log_output.append(html)
        self.log_output.moveCursor(QTextCursor.End)

    def update_progress(self, stats):
        total = stats["total"]
        if total > 0:
            self.progress_bar.setValue(int((stats["processed"] / total) * 100))
        self.total_lbl.value_label.setText(str(total))
        self.charged_lbl.value_label.setText(str(stats["charged"]))
        self.declined_lbl.value_label.setText(str(stats["declined"]))
        self.error_lbl.value_label.setText(str(stats["error"]))

    def start_checking(self):
        threads = self.thread_spin.value()
        input_text = self.cc_input.toPlainText().strip()
        cc_file = self.cc_path_input.text().strip()

        final_cc_file = None
        if input_text:
            temp_path = os.path.join(os.getcwd(), "temp_cards.txt")
            with open(temp_path, "w") as f:
                f.write(input_text)
            final_cc_file = temp_path
        elif cc_file and os.path.exists(cc_file):
            final_cc_file = cc_file
        else:
            self.log({"msg": "Error: Please paste cards or select a valid session file.", "status": "ERROR"})
            return

        if self.worker_thread:
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_output.clear()
        self.live_output.clear()

        self.worker_thread = QThread()
        self.worker = StripeWorker(final_cc_file, threads)
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.on_finished)
        
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        self.worker.log.connect(self.log)
        self.worker.progress.connect(self.update_progress)
        self.worker_thread.start()

    def stop_checking(self):
        if self.worker: self.worker.stop()

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.worker = None
        self.worker_thread = None

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
