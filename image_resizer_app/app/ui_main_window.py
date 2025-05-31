import os
import json
import hashlib
import random
import zipfile
import subprocess
from PIL import Image
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QComboBox, QFileDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt
from app.image_canvas import ImageCanvas

SETTINGS_FILE = "settings.json"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Resizer")
        self.setGeometry(200, 200, 1200, 800)
        self.loaded_image_path = None
        self.export_mode = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout()
        central_widget.setLayout(self.main_layout)

        self.init_controls()
        self.init_canvas()
        self.init_footer()
        self.load_settings()

    def init_controls(self):
        layout = QHBoxLayout()

        self.file_type_dropdown = QComboBox()
        self.file_type_dropdown.addItems(["JPEG", "PNG"])
        self.file_type_dropdown.setToolTip("Select the export file format.")

        self.output_label = QLabel("No folder selected")
        self.prefix_input = QLineEdit("cropped")
        self.prefix_input.setToolTip("Prefix for each exported filename.")
        self.suffix_input = QLineEdit("")
        self.suffix_input.setToolTip("Suffix to add at the end of each filename.")
        self.resize_mode_dropdown = QComboBox()
        self.resize_mode_dropdown.addItems(["No Resize", "Resize by Width", "Resize by Height"])
        self.resize_mode_dropdown.setToolTip("Choose whether to resize width or height.")
        self.resize_input = QLineEdit()
        self.resize_input.setPlaceholderText("%")
        self.resize_input.setFixedWidth(50)
        self.resize_input.setToolTip("Enter percentage to resize each cropped image.")

        self.output_btn = QPushButton("📁 Select Output Folder")
        self.output_btn.clicked.connect(self.select_output_folder)
        self.output_btn.setToolTip("Choose the folder where images will be saved.")

        self.grid_btn = QPushButton("🧮 Toggle Grid")
        self.grid_btn.clicked.connect(self.toggle_grid_preview)
        self.grid_btn.setToolTip("Toggle grid overlay preview.")

        self.zip_checkbox = QCheckBox("📦 Export as ZIP only")
        self.zip_checkbox.setToolTip("If enabled, all cropped images will be zipped.")

        self.open_btn = QPushButton("🖼️ Open Image")
        self.open_btn.clicked.connect(self.open_image_dialog)
        self.open_btn.setToolTip("Open an image to begin cropping.")

        self.filename_preview_label = QLabel("Preview:")
        self.filename_preview_label.setStyleSheet("font-size: 10pt; color: gray;")

        self.prefix_input.textChanged.connect(self.update_filename_preview)
        self.suffix_input.textChanged.connect(self.update_filename_preview)
        self.file_type_dropdown.currentTextChanged.connect(self.update_filename_preview)

        for w in [QLabel("Type:"), self.file_type_dropdown,
                  QLabel("Prefix:"), self.prefix_input,
                  QLabel("Suffix:"), self.suffix_input,
                  QLabel("Resize Output:"), self.resize_mode_dropdown, self.resize_input,
                  self.output_btn, self.output_label,
                  self.grid_btn, self.zip_checkbox, self.open_btn]:
            layout.addWidget(w)

        layout.addWidget(self.filename_preview_label)
        self.main_layout.addLayout(layout)

    def update_filename_preview(self):
        prefix = self.prefix_input.text() or "cropped"
        suffix = self.suffix_input.text() or ""
        ext = ".jpg" if self.file_type_dropdown.currentText() == "JPEG" else ".png"
        self.filename_preview_label.setText(f"Preview: {prefix}-1-[HASH]{suffix}{ext}")

    def init_canvas(self):
        self.canvas = ImageCanvas(on_image_loaded=self.on_image_loaded, on_guides_updated=self.on_guides_changed)
        self.main_layout.addWidget(self.canvas, stretch=1)

    def init_footer(self):
        layout = QHBoxLayout()
        self.status = QLabel("")
        self.clear_btn = QPushButton("🧹 Clear")
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        self.clear_btn.setToolTip("Clear the canvas and reset.")
        self.export_btn = QPushButton("🔍 Preview")
        self.export_btn.clicked.connect(self.on_export_clicked)
        self.export_btn.setToolTip("Preview or Export images based on guide lines.")
        for w in [self.status, self.clear_btn, self.export_btn]:
            layout.addWidget(w)
        self.main_layout.addLayout(layout)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_label.setText(folder)

    def open_image_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.canvas.load_image(file_path)
            self.loaded_image_path = file_path
            self.reset_export_mode()
            self.status.setText("🖼️ Image loaded. ➕ Add vertical and horizontal lines to begin, then click Preview.")

    def on_image_loaded(self, path):
        self.loaded_image_path = path

    def toggle_grid_preview(self):
        self.canvas.toggle_grid(not self.canvas.show_grid)

    def on_clear_clicked(self):
        self.canvas.clear_canvas()
        self.reset_export_mode()
        self.status.setText("🧹 Canvas cleared.")

    def reset_export_mode(self):
        self.export_mode = False
        self.canvas.toggle_grid(False)
        self.export_btn.setText("🔍 Preview")

    def on_export_clicked(self):
        if not self.loaded_image_path:
            self.status.setText("⚠️ No image loaded.")
            return

        vertical = self.canvas.get_vertical_guides()
        horizontal = self.canvas.get_horizontal_guides()

        if not self.export_mode:
            self.canvas.toggle_grid(True)
            includes = self.canvas.get_active_crop_flags()
            total_sections = (len(vertical) + 1) * (len(horizontal) + 1)

            if total_sections == 1:
                self.status.setText("⚠️ No crop lines added. The entire image will be exported as one section.")
            else:
                self.status.setText("👀 Preview enabled. Click Export to proceed.")

            self.export_mode = True
            self.export_btn.setText("📤 Export")
        else:
            self.export_images()

    def on_guides_changed(self):
        if not self.export_mode:
            return
        vertical = self.canvas.get_vertical_guides()
        horizontal = self.canvas.get_horizontal_guides()
        if len(vertical) == 0 and len(horizontal) == 0:
            self.status.setText("⚠️ No crop lines added. The entire image will be exported as one section.")
        else:
            self.status.setText("✅ Crop lines added. You can proceed to Export.")
    def export_images(self):
        vertical = self.canvas.get_vertical_guides()
        horizontal = self.canvas.get_horizontal_guides()

        image = Image.open(self.loaded_image_path)
        if image.mode == "RGBA" and self.file_type_dropdown.currentText() == "JPEG":
            image = image.convert("RGB")
        w, h = image.size
        scaled_pixmap = self.canvas.pixmap()
        if not scaled_pixmap or scaled_pixmap.width() == 0 or scaled_pixmap.height() == 0:
            self.status.setText("⚠️ Image not rendered.")
            return

        x_ratio = w / scaled_pixmap.width()
        y_ratio = h / scaled_pixmap.height()
        x_lines = [0] + sorted(int(x * x_ratio) for x in vertical) + [w]
        y_lines = [0] + sorted(int(y * y_ratio) for y in horizontal) + [h]

        includes = self.canvas.get_active_crop_flags()
        total_sections = (len(x_lines) - 1) * (len(y_lines) - 1)
        if len(includes) < total_sections:
            includes += [True] * (total_sections - len(includes))

        num_exporting = sum(1 for flag in includes[:total_sections] if flag)
        if num_exporting == 0:
            self.status.setText("🚫 No crop sections selected.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Export",
            f"📤 You are about to export {num_exporting} cropped image(s). Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if confirm != QMessageBox.StandardButton.Yes:
            self.status.setText("❌ Export cancelled by user.")
            return

        out_dir = self.output_label.text()
        if not out_dir or out_dir == "No folder selected":
            base = os.path.splitext(os.path.basename(self.loaded_image_path))[0]
            out_dir = os.path.join(os.path.dirname(self.loaded_image_path), base)
        os.makedirs(out_dir, exist_ok=True)

        prefix = self.prefix_input.text() or "cropped"
        suffix = self.suffix_input.text() or ""
        ext = ".jpg" if self.file_type_dropdown.currentText() == "JPEG" else ".png"
        export_as_zip = self.zip_checkbox.isChecked()

        def fname(i):
            h = hashlib.sha256(str(random.random()).encode()).hexdigest()[:8]
            return f"{prefix}-{i}-{h}{suffix}{ext}"

        log = open(os.path.join(out_dir, "export_log.txt"), "w")
        log.write("filename,x1,y1,x2,y2\n")

        images = []
        idx = 1
        grid_idx = 0

        for i in range(len(x_lines) - 1):
            for j in range(len(y_lines) - 1):
                if grid_idx >= len(includes) or not includes[grid_idx]:
                    grid_idx += 1
                    continue
                x1, x2 = x_lines[i], x_lines[i + 1]
                y1, y2 = y_lines[j], y_lines[j + 1]
                crop = image.crop((x1, y1, x2, y2))

                resize_mode = self.resize_mode_dropdown.currentText()
                try:
                    percent = float(self.resize_input.text())
                except (ValueError, TypeError):
                    percent = None

                if percent and percent > 0 and resize_mode != "No Resize":
                    w0, h0 = crop.size
                    if resize_mode == "Resize by Width":
                        w1 = int(w0 * percent / 100)
                        h1 = int(h0 * percent / 100)
                    elif resize_mode == "Resize by Height":
                        h1 = int(h0 * percent / 100)
                        w1 = int(w0 * percent / 100)
                    crop = crop.resize((w1, h1), Image.Resampling.LANCZOS)

                name = fname(idx)
                if export_as_zip:
                    temp_path = os.path.join(out_dir, name)
                    crop.save(temp_path)
                    images.append((temp_path, name))
                else:
                    crop.save(os.path.join(out_dir, name))
                log.write(f"{name},{x1},{y1},{x2},{y2}\n")
                idx += 1
                grid_idx += 1
        log.close()

        if export_as_zip:
            zip_path = os.path.join(out_dir, os.path.basename(out_dir) + ".zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path, arcname in images:
                    zipf.write(file_path, arcname=arcname)
                    os.remove(file_path)

        self.status.setStyleSheet("color: green;")
        self.status.setText(f"✅ Exported {idx - 1} images.")
        QMessageBox.information(
            self, "Export Completed",
            f"✅ Successfully exported {idx - 1} image(s) to:\n{out_dir}",
            QMessageBox.StandardButton.Ok
        )
        try:
            path_to_open = os.path.abspath(out_dir).replace("/", "\\")
            subprocess.Popen(["explorer", path_to_open])
        except Exception as e:
            print("Could not open folder:", e)
        self.save_settings()

    def save_settings(self):
        data = {
            "file_type": self.file_type_dropdown.currentText(),
            "output_folder": self.output_label.text(),
            "zip_enabled": self.zip_checkbox.isChecked()
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                self.file_type_dropdown.setCurrentText(data.get("file_type", "JPEG"))
                self.output_label.setText(data.get("output_folder", "No folder selected"))
                self.zip_checkbox.setChecked(data.get("zip_enabled", False))