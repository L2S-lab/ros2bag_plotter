from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import pandas as pd
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .bag_reader import Ros2BagReader
from .exporter import export_csv, save_html, save_image
from .mapping_dialog import MappingDialog
from .plotting import build_combined_figure, build_per_topic_figure
from .processing_service import BagProcessingService
from .type_mapping import list_leaf_paths


class MsgSchemaDialog(QDialog):
    def __init__(self, msg_type: str, error_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Missing custom type: {msg_type}")
        self.resize(780, 420)
        lay = QVBoxLayout(self)
        lay.addWidget(
            QLabel(
                "Paste the full .msg definition for this custom type.\n"
                "Example fields: `float32[] values`, `string[] names`, etc."
            )
        )
        if error_text:
            err_lbl = QLabel(f"Last decode error: {error_text}")
            err_lbl.setStyleSheet("color: #9f1239;")
            lay.addWidget(err_lbl)
        self.text = QTextEdit()
        lay.addWidget(self.text)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def value(self) -> str:
        return self.text.toPlainText().strip()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROS2 Bag Plotter v1.1")
        self.resize(1100, 620)
        self._set_logo_window_icon()

        self.processor = BagProcessingService()
        self.root_dir = Path.cwd()
        self.topic_frames: Dict[str, pd.DataFrame] = {}
        self.topic_controls: Dict[str, tuple[QCheckBox, QCheckBox, QCheckBox]] = {}
        self.current_bag: Path | None = None
        self.current_fig = None

        self._ui()
        self.refresh_bags()

    def _is_container_runtime(self) -> bool:
        return Path("/.dockerenv").exists() or os.getenv("container") is not None

    def _open_html_file(self, html_path: Path) -> bool:
        if self._is_container_runtime():
            if shutil.which("xdg-open"):
                proc = subprocess.run(
                    ["xdg-open", str(html_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                return proc.returncode == 0
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(html_path)))

    def _logo_path(self) -> Path:
        return Path(__file__).resolve().parent / "assets" / "logo.svg"

    def _set_logo_window_icon(self):
        logo = self._logo_path()
        if logo.exists():
            self.setWindowIcon(QIcon(str(logo)))

    def _load_logo_pixmap(self, size: int = 56) -> QPixmap | None:
        logo = self._logo_path()
        if not logo.exists():
            return None
        renderer = QSvgRenderer(str(logo))
        if not renderer.isValid():
            return None
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    def _ui(self):
        lay = QVBoxLayout(self)

        header = QHBoxLayout()
        logo_pixmap = self._load_logo_pixmap()
        if logo_pixmap is not None:
            logo_label = QLabel()
            logo_label.setPixmap(logo_pixmap)
            logo_label.setFixedSize(logo_pixmap.size())
            header.addWidget(logo_label)
        title = QLabel("ROS2 Bag Plotter")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        lay.addLayout(header)

        top = QHBoxLayout()
        self.lbl_root = QLabel(f"Root: {self.root_dir}")
        btn_root = QPushButton("Select Root")
        btn_refresh = QPushButton("Refresh Bags")
        btn_root.clicked.connect(self.select_root)
        btn_refresh.clicked.connect(self.refresh_bags)
        top.addWidget(self.lbl_root)
        top.addWidget(btn_root)
        top.addWidget(btn_refresh)
        lay.addLayout(top)

        row = QHBoxLayout()
        row.addWidget(QLabel("Bag:"))
        self.cmb_bag = QComboBox()
        self.cmb_bag.currentIndexChanged.connect(self.refresh_topics)
        row.addWidget(self.cmb_bag)
        lay.addLayout(row)

        lay.addWidget(QLabel("Topic filter (check to include):"))
        self.lst_topics = QListWidget()
        lay.addWidget(self.lst_topics)

        ops = QHBoxLayout()
        self.chk_open = QCheckBox("Open combined HTML after save")
        self.chk_open.setChecked(not self._is_container_runtime())
        if self._is_container_runtime():
            self.chk_open.setToolTip(
                "Auto-open is disabled by default in Docker; open HTML directly from the plots folder."
            )
        self.chk_per_topic_html = QCheckBox("Per-topic separate HTML")
        self.chk_per_topic_html.setChecked(True)
        self.spin_smooth_samples = QSpinBox()
        self.spin_smooth_samples.setRange(1, 501)
        self.spin_smooth_samples.setSingleStep(2)
        self.spin_smooth_samples.setValue(5)
        self.spin_smooth_samples.setToolTip("Moving-average window in samples for derivative smoothing.")
        ops.addWidget(self.chk_open)
        ops.addWidget(self.chk_per_topic_html)
        ops.addWidget(QLabel("Smooth window (samples):"))
        ops.addWidget(self.spin_smooth_samples)
        ops.addStretch(1)
        lay.addLayout(ops)

        btns = QHBoxLayout()
        self.btn_plot = QPushButton("Plot Selected Bag")
        self.btn_csv = QPushButton("Export CSV Selected Bag")
        self.btn_png = QPushButton("Save PNG Selected Bag")
        self.btn_svg = QPushButton("Save SVG Selected Bag")
        self.btn_all = QPushButton("Batch Export ALL Bags")
        self.btn_plot.clicked.connect(self.plot_selected)
        self.btn_csv.clicked.connect(self.export_csv_selected)
        self.btn_png.clicked.connect(lambda: self.export_image_selected("png"))
        self.btn_svg.clicked.connect(lambda: self.export_image_selected("svg"))
        self.btn_all.clicked.connect(self.batch_export_all)
        for b in [
            self.btn_plot,
            self.btn_csv,
            self.btn_png,
            self.btn_svg,
            self.btn_all,
        ]:
            btns.addWidget(b)
        lay.addLayout(btns)

        self.progress = QProgressBar()
        lay.addWidget(self.progress)

    def select_root(self):
        p = QFileDialog.getExistingDirectory(self, "Select root", str(self.root_dir))
        if p:
            self.root_dir = Path(p)
            self.lbl_root.setText(f"Root: {self.root_dir}")
            self.refresh_bags()

    def refresh_bags(self):
        self.cmb_bag.clear()
        for b in Ros2BagReader.discover_bag_folders(self.root_dir):
            self.cmb_bag.addItem(b.name, str(b))
        if self.cmb_bag.count() == 0:
            self.cmb_bag.addItem("No bags found", "")
        self.refresh_topics()

    def selected_bag(self) -> Path | None:
        d = self.cmb_bag.currentData()
        return Path(d) if d else None

    def refresh_topics(self):
        self.lst_topics.clear()
        self.topic_controls.clear()
        bag = self.selected_bag()
        if not bag:
            return
        try:
            reader = Ros2BagReader(bag)
            tmap = reader.get_topic_type_map()
            for topic, tname in tmap.items():
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(4, 0, 4, 0)
                row_layout.setSpacing(10)

                chk_include = QCheckBox(f"{topic}   ({tname})")
                chk_include.setChecked(True)
                chk_derivative = QCheckBox("Plot d1/d2")
                chk_derivative.setToolTip("Generate first and second derivative plot for this topic.")
                chk_smooth = QCheckBox("Smooth d1/d2")
                chk_smooth.setToolTip("Apply moving-average smoothing to derivative traces.")
                chk_smooth.setEnabled(False)

                def on_derivative_toggle(checked: bool, smooth_box=chk_smooth):
                    smooth_box.setEnabled(bool(checked))
                    if not checked:
                        smooth_box.setChecked(False)

                chk_derivative.toggled.connect(on_derivative_toggle)

                row_layout.addWidget(chk_include)
                row_layout.addStretch(1)
                row_layout.addWidget(chk_derivative)
                row_layout.addWidget(chk_smooth)

                it = QListWidgetItem()
                it.setData(Qt.UserRole, topic)
                it.setSizeHint(row_widget.sizeHint())
                self.lst_topics.addItem(it)
                self.lst_topics.setItemWidget(it, row_widget)
                self.topic_controls[topic] = (chk_include, chk_derivative, chk_smooth)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def selected_topics(self) -> List[str]:
        out = []
        for topic, controls in self.topic_controls.items():
            chk_include, _, _ = controls
            if chk_include.isChecked():
                out.append(topic)
        return out

    def derivative_topics(self) -> List[str]:
        out = []
        for topic, controls in self.topic_controls.items():
            chk_include, chk_derivative, _ = controls
            if chk_include.isChecked() and chk_derivative.isChecked():
                out.append(topic)
        return out

    def derivative_smoothing_topics(self) -> List[str]:
        out = []
        for topic, controls in self.topic_controls.items():
            chk_include, chk_derivative, chk_smooth = controls
            if chk_include.isChecked() and chk_derivative.isChecked() and chk_smooth.isChecked():
                out.append(topic)
        return out

    def derivative_smoothing_window(self) -> int:
        value = int(self.spin_smooth_samples.value())
        return max(1, value)

    def _prompt_schema_definition(self, type_name: str, error_text: str) -> str | None:
        dlg = MsgSchemaDialog(type_name, error_text, self)
        if dlg.exec():
            val = dlg.value()
            return val or None
        return None

    def open_multifield_mapping_dialog_and_save(self, type_name: str, msg):
        leaf_paths = list_leaf_paths(msg)
        if not leaf_paths:
            QMessageBox.warning(
                self,
                "No numeric fields",
                f"No numeric scalar/array field found in custom type: {type_name}",
            )
            return None
        dlg = MappingDialog(type_name, leaf_paths, self)
        if dlg.exec():
            mapping = dlg.result_mapping()
            if mapping.get("fields"):
                return mapping
        return None

    def _load_frames(self, bag: Path, topics: List[str]) -> Dict[str, pd.DataFrame]:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

        def progress(done: int, total: int):
            max_total = max(1, total)
            if self.progress.maximum() != max_total:
                self.progress.setRange(0, max_total)
            self.progress.setValue(min(done, max_total))

        frames = self.processor.load_frames(
            bag,
            topics,
            progress_cb=progress,
            request_schema_cb=self._prompt_schema_definition,
            request_mapping_cb=self.open_multifield_mapping_dialog_and_save,
        )
        self.progress.setValue(self.progress.maximum())
        return frames

    def _load_selected_bag_frames(self) -> tuple[Path, Dict[str, pd.DataFrame], List[str]]:
        bag = self.selected_bag()
        if not bag:
            raise RuntimeError("Select a bag first.")
        topics = self.selected_topics()
        frames = self._load_frames(bag, topics)
        if not frames:
            raise RuntimeError("No decodable numeric data for selected topics.")
        self.current_bag = bag
        self.topic_frames = frames
        return bag, frames, topics

    def plot_selected(self):
        try:
            bag, frames, _ = self._load_selected_bag_frames()
            derivative_set = set(self.derivative_topics())
            derivative_smooth_set = set(self.derivative_smoothing_topics())
            smooth_window = self.derivative_smoothing_window()
            fig = build_combined_figure(
                frames,
                derivative_topics=derivative_set,
                derivative_smoothing_topics=derivative_smooth_set,
                derivative_smoothing_window=smooth_window,
            )
            self.current_fig = fig
            out = save_html(fig, bag, "all_topics_plot.html")

            if self.chk_per_topic_html.isChecked():
                for topic, df in frames.items():
                    fig_t = build_per_topic_figure(
                        topic,
                        df,
                        include_derivatives=(topic in derivative_set),
                        smooth_derivatives=(topic in derivative_smooth_set),
                        smooth_window=smooth_window,
                    )
                    name = topic.strip("/").replace("/", "__") + ".html"
                    save_html(fig_t, bag, name)

            if self.chk_open.isChecked() and not self._open_html_file(out):
                QMessageBox.information(
                    self,
                    "Saved",
                    f"HTML saved at:\n{out}\n\nNo browser launcher is available in this runtime.",
                )

            QMessageBox.information(self, "Done", f"Plots saved in: {bag / 'plots'}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def export_csv_selected(self):
        try:
            bag, frames, _ = self._load_selected_bag_frames()
            export_csv(frames, bag)
            QMessageBox.information(self, "Done", f"CSV exported in: {bag / 'csv'}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def export_image_selected(self, ext: str):
        try:
            bag, frames, _ = self._load_selected_bag_frames()
            fig = build_combined_figure(
                frames,
                derivative_topics=set(self.derivative_topics()),
                derivative_smoothing_topics=set(self.derivative_smoothing_topics()),
                derivative_smoothing_window=self.derivative_smoothing_window(),
            )
            self.current_fig = fig
            save_image(fig, bag, "all_topics_plot", ext, topic_frames=frames)
            QMessageBox.information(self, "Done", f"{ext.upper()} saved in: {bag / 'plots'}")
        except RuntimeError as e:
            QMessageBox.warning(self, "Image export unavailable", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def batch_export_all(self):
        bags = Ros2BagReader.discover_bag_folders(self.root_dir)
        if not bags:
            QMessageBox.information(self, "Info", "No bag folders found.")
            return

        try:
            image_export_enabled = True
            image_error: str | None = None
            derivative_set = set(self.derivative_topics())
            derivative_smooth_set = set(self.derivative_smoothing_topics())
            smooth_window = self.derivative_smoothing_window()
            for bag in bags:
                frames = self._load_frames(bag, topics=[])
                if not frames:
                    continue
                export_csv(frames, bag)
                fig = build_combined_figure(
                    frames,
                    derivative_topics=derivative_set,
                    derivative_smoothing_topics=derivative_smooth_set,
                    derivative_smoothing_window=smooth_window,
                )
                save_html(fig, bag, "all_topics_plot.html")
                if image_export_enabled:
                    try:
                        save_image(fig, bag, "all_topics_plot", "png", topic_frames=frames)
                        save_image(fig, bag, "all_topics_plot", "svg", topic_frames=frames)
                    except RuntimeError as e:
                        image_export_enabled = False
                        image_error = str(e)
                if self.chk_per_topic_html.isChecked():
                    for topic, df in frames.items():
                        fig_t = build_per_topic_figure(
                            topic,
                            df,
                            include_derivatives=(topic in derivative_set),
                            smooth_derivatives=(topic in derivative_smooth_set),
                            smooth_window=smooth_window,
                        )
                        save_html(fig_t, bag, topic.strip("/").replace("/", "__") + ".html")
            if image_error:
                QMessageBox.warning(
                    self,
                    "Batch export completed",
                    "CSV/HTML export completed for all bags.\n"
                    f"PNG/SVG export skipped: {image_error}",
                )
            else:
                QMessageBox.information(self, "Done", "Batch export completed for all bags.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
