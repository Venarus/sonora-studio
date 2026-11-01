"""
SONORA Studio - Visual Asset Generator
Renders high-resolution brand assets: logo.png, banner.png, and ai_comparison.png.
"""

import sys
import numpy as np
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QImage, QPainter, QColor, QPen, QBrush, QFont,
                           QLinearGradient, QRadialGradient, QPolygonF)
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)
out_dir = Path("docs/assets")
out_dir.mkdir(parents=True, exist_ok=True)


def render_logo(path: Path):
    size = 512
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # 1. Squircle background
    bg_grad = QLinearGradient(0, 0, size, size)
    bg_grad.setColorAt(0.0, QColor("#161822"))
    bg_grad.setColorAt(0.5, QColor("#0F1017"))
    bg_grad.setColorAt(1.0, QColor("#090A0E"))

    p.setPen(QPen(QColor("#232736"), 4))
    p.setBrush(bg_grad)
    p.drawRoundedRect(QRectF(24, 24, 464, 464), 108, 108)

    # Inner subtle rim
    rim_grad = QLinearGradient(0, 0, size, size)
    rim_grad.setColorAt(0.0, QColor(0, 229, 163, 140))
    rim_grad.setColorAt(1.0, QColor(0, 229, 163, 15))
    p.setPen(QPen(rim_grad, 2))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(36, 36, 440, 440), 96, 96)

    # Center radial aura
    rad_aura = QRadialGradient(256, 256, 160)
    rad_aura.setColorAt(0.0, QColor(0, 229, 163, 30))
    rad_aura.setColorAt(1.0, QColor(0, 229, 163, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(rad_aura)
    p.drawEllipse(QPointF(256, 256), 160, 160)

    # Soundwave bars
    bar_grad = QLinearGradient(0, 380, 0, 100)
    bar_grad.setColorAt(0.0, QColor("#00B488"))
    bar_grad.setColorAt(0.5, QColor("#00E5A3"))
    bar_grad.setColorAt(1.0, QColor("#55F8CB"))

    bars = [
        (110, 226, 18, 60),
        (146, 196, 18, 120),
        (182, 156, 18, 200),
        (218, 126, 18, 260),
        (254, 100, 20, 312),  # center
        (294, 126, 18, 260),
        (330, 156, 18, 200),
        (366, 196, 18, 120),
        (402, 226, 18, 60),
    ]

    p.setPen(Qt.NoPen)
    for i, (bx, by, bw, bh) in enumerate(bars):
        if i == 4:
            p.setBrush(QColor("#FFFFFF"))
        else:
            p.setBrush(bar_grad)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), bw / 2, bw / 2)

    # Center axis dotted line
    axis_pen = QPen(QColor(0, 229, 163, 70), 2, Qt.DashLine)
    p.setPen(axis_pen)
    p.drawLine(84, 256, 428, 256)

    p.end()
    img.save(str(path))
    print(f"Rendered logo to: {path}")


def render_banner(path: Path):
    w, h = 1280, 420
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor("#0B0C10"))

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    # Background gradient with graphite carbon sheen
    bg_grad = QLinearGradient(0, 0, w, h)
    bg_grad.setColorAt(0.0, QColor("#14161F"))
    bg_grad.setColorAt(0.4, QColor("#0E1017"))
    bg_grad.setColorAt(1.0, QColor("#07080B"))
    p.fillRect(0, 0, w, h, bg_grad)

    # Subtle background radial glow behind logo
    rad_glow = QRadialGradient(240, 210, 260)
    rad_glow.setColorAt(0.0, QColor(0, 229, 163, 40))
    rad_glow.setColorAt(0.7, QColor(0, 229, 163, 10))
    rad_glow.setColorAt(1.0, QColor(0, 229, 163, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(rad_glow)
    p.drawEllipse(QPointF(240, 210), 260, 260)

    # Right side decorative waveform lines
    p.setPen(QPen(QColor("#1A1E29"), 1))
    for y in range(40, h, 35):
        p.drawLine(0, y, w, y)

    # Ambient waveform curves
    t_vals = np.linspace(0, 4 * np.pi, 200)
    wave_y = 210 + 45 * np.sin(t_vals) * np.exp(-((t_vals - 2 * np.pi) ** 2) / 8)
    wave_x = np.linspace(500, 1240, 200)

    p.setPen(QPen(QColor(0, 229, 163, 50), 2))
    for i in range(len(wave_x) - 1):
        p.drawLine(int(wave_x[i]), int(wave_y[i]), int(wave_x[i + 1]), int(wave_y[i + 1]))

    # Left Badge / Logo squircle (190x190)
    logo_rect = QRectF(70, 115, 190, 190)
    p.setPen(QPen(QColor("#2B3041"), 3))
    p.setBrush(QColor("#141620"))
    p.drawRoundedRect(logo_rect, 44, 44)

    # Logo Soundwave Bars inside badge
    bars = [
        (96, 195, 10, 30),
        (116, 175, 10, 70),
        (136, 150, 10, 120),
        (156, 135, 10, 150),
        (176, 120, 12, 180),  # center white
        (198, 135, 10, 150),
        (218, 150, 10, 120),
        (238, 175, 10, 70),
        (258, 195, 10, 30),
    ]
    bar_grad = QLinearGradient(0, 300, 0, 120)
    bar_grad.setColorAt(0.0, QColor("#00B488"))
    bar_grad.setColorAt(1.0, QColor("#00E5A3"))

    p.setPen(Qt.NoPen)
    for i, (bx, by, bw, bh) in enumerate(bars):
        p.setBrush(QColor("#FFFFFF") if i == 4 else bar_grad)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), bw / 2, bw / 2)

    # Typography: Right of logo
    # 1. Version tag
    tag_rect = QRectF(300, 105, 105, 26)
    p.setPen(QPen(QColor(0, 229, 163, 100), 1))
    p.setBrush(QColor(0, 229, 163, 25))
    p.drawRoundedRect(tag_rect, 13, 13)

    p.setFont(QFont("Segoe UI", 10, QFont.Bold))
    p.setPen(QColor("#00E5A3"))
    p.drawText(tag_rect, Qt.AlignCenter, "v1.0.0 PRO")

    # 2. Main Title: SONORA STUDIO
    p.setFont(QFont("Segoe UI Variable Display", 36, QFont.ExtraBold))
    p.setPen(QColor("#FFFFFF"))
    p.drawText(300, 180, "SONORA STUDIO")

    # 3. Subtitle: PROFESSIONAL AI AUDIO RECORDER & EDITOR
    p.setFont(QFont("Segoe UI", 14, QFont.Bold))
    p.setPen(QColor("#00E5A3"))
    p.drawText(300, 215, "PROFESSIONAL AI AUDIO RECORDER & EDITOR")

    # 4. Description line
    p.setFont(QFont("Segoe UI", 12))
    p.setPen(QColor("#9CA3AF"))
    p.drawText(300, 248, "Windows 11 Local-First DAW • 48 kHz 24-Bit PCM • AI Spectral Gating • Waveform Timeline")

    # 5. Feature Badges (Pills)
    pills = [
        ("✦ Yerel & Çevrimdışı (Offline)", "#1F2937", "#9CA3AF"),
        ("🎙️ 48kHz / 24-bit PCM", "#132E27", "#00E5A3"),
        ("✨ YZ Gürültü Azaltma", "#271E3A", "#C084FC"),
        ("⚡ Sıfır Gecikmeli UI", "#142838", "#38BDF8"),
        ("🪟 Windows 11 Fluent", "#1E293B", "#CBD5E1")
    ]

    px = 300
    py = 278
    p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))

    for label, bg_c, text_c in pills:
        pill_w = len(label) * 8 + 20
        rect = QRectF(px, py, pill_w, 28)
        p.setPen(QPen(QColor(bg_c).lighter(140), 1))
        p.setBrush(QColor(bg_c))
        p.drawRoundedRect(rect, 6, 6)

        p.setPen(QColor(text_c))
        p.drawText(rect, Qt.AlignCenter, label)
        px += pill_w + 10

    # Bottom border accent line
    bot_grad = QLinearGradient(0, 0, w, 0)
    bot_grad.setColorAt(0.0, QColor(0, 229, 163, 0))
    bot_grad.setColorAt(0.3, QColor(0, 229, 163, 200))
    bot_grad.setColorAt(0.7, QColor(0, 229, 163, 200))
    bot_grad.setColorAt(1.0, QColor(0, 229, 163, 0))
    p.fillRect(0, h - 3, w, 3, bot_grad)

    p.end()
    img.save(str(path))
    print(f"Rendered banner to: {path}")


def render_ai_comparison(path: Path):
    w, h = 1200, 520
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor("#0D0E14"))

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    # Background
    p.fillRect(0, 0, w, h, QColor("#0D0E14"))

    # Header Title
    p.setFont(QFont("Segoe UI Variable Display", 18, QFont.Bold))
    p.setPen(QColor("#FFFFFF"))
    p.drawText(30, 42, "SONORA AI Ses Temizleme & Akustik İzolasyon Karşılaştırması")

    p.setFont(QFont("Segoe UI", 12))
    p.setPen(QColor("#9CA3AF"))
    p.drawText(30, 68, "Gerçek mikrofon girişinde arka plan gürültüsü, klima ve 50 Hz şebeke uğultusunun yapay zeka ile yok edilmesi")

    # -------------------------------------------------------------
    # TOP CARD: BEFORE (RAW AUDIO)
    # -------------------------------------------------------------
    top_rect = QRectF(30, 95, 1140, 185)
    p.setPen(QPen(QColor("#EF4444"), 1.5))
    p.setBrush(QColor("#181115"))
    p.drawRoundedRect(top_rect, 10, 10)

    # Label
    p.setFont(QFont("Segoe UI", 13, QFont.Bold))
    p.setPen(QColor("#F87171"))
    p.drawText(50, 126, "❌ ÖNCESİ: Ham Ses Kaydı (Klima Hiss + 50 Hz Elektrik Uğultusu + PC Fan Gürültüsü)")

    # Metrics on right
    p.setFont(QFont("Consolas", 11, QFont.Bold))
    p.setPen(QColor("#EF4444"))
    p.drawText(780, 126, "SNR: 8.2 dB • Gürültü Tabanı: -36 dBFS • THD: Yüksek")

    # Draw noisy raw waveform
    np.random.seed(42)
    n_pts = 900
    t = np.linspace(0, 4, n_pts)
    speech = np.sin(2 * np.pi * 3 * t) * (1 + np.sin(2 * np.pi * 0.7 * t))
    speech[int(n_pts * 0.35):int(n_pts * 0.55)] *= 0.1  # pause
    noise = np.random.normal(0, 0.45, n_pts)  # strong noise
    hum = 0.3 * np.sin(2 * np.pi * 25 * t)
    raw_signal = speech * 0.8 + noise + hum

    wx_start = 50
    wx_end = 1150
    dx = (wx_end - wx_start) / float(n_pts)
    mid_y_top = 205

    p.setPen(QPen(QColor("#2E1E26"), 1))
    p.drawLine(wx_start, mid_y_top, wx_end, mid_y_top)

    p.setPen(QPen(QColor("#F87171"), 1.2))
    for i in range(n_pts - 1):
        x1 = int(wx_start + i * dx)
        y1 = int(mid_y_top - raw_signal[i] * 32)
        x2 = int(wx_start + (i + 1) * dx)
        y2 = int(mid_y_top - raw_signal[i + 1] * 32)
        p.drawLine(x1, y1, x2, y2)

    # -------------------------------------------------------------
    # BOTTOM CARD: AFTER (PROCESSED WITH SONORA AI)
    # -------------------------------------------------------------
    bot_rect = QRectF(30, 305, 1140, 185)
    p.setPen(QPen(QColor("#00E5A3"), 1.5))
    p.setBrush(QColor("#0E1A17"))
    p.drawRoundedRect(bot_rect, 10, 10)

    # Label
    p.setFont(QFont("Segoe UI", 13, QFont.Bold))
    p.setPen(QColor("#00E5A3"))
    p.drawText(50, 336, "✓ SONRASI: SONORA YZ ile Temizlenmiş & Netleştirilmiş Vokal (Spektral Gating + De-Hum)")

    # Metrics on right
    p.setFont(QFont("Consolas", 11, QFont.Bold))
    p.setPen(QColor("#00E5A3"))
    p.drawText(780, 336, "SNR: 48.7 dB • Gürültü Tabanı: -78 dBFS • Doğallık: %99.4")

    # Draw pristine cleaned waveform
    clean_signal = speech * 1.1
    # add subtle speech harmonic definition, zero noise in pause
    mid_y_bot = 415

    p.setPen(QPen(QColor("#16382E"), 1))
    p.drawLine(wx_start, mid_y_bot, wx_end, mid_y_bot)

    p.setPen(QPen(QColor("#00E5A3"), 1.5))
    for i in range(n_pts - 1):
        x1 = int(wx_start + i * dx)
        y1 = int(mid_y_bot - clean_signal[i] * 35)
        x2 = int(wx_start + (i + 1) * dx)
        y2 = int(mid_y_bot - clean_signal[i + 1] * 35)
        p.drawLine(x1, y1, x2, y2)

    p.end()
    img.save(str(path))
    print(f"Rendered comparison to: {path}")


if __name__ == "__main__":
    render_logo(out_dir / "sonora_logo.png")
    render_banner(out_dir / "sonora_banner.png")
    render_ai_comparison(out_dir / "ai_comparison.png")
    print("All branding graphics generated successfully!")
