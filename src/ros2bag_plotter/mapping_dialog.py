from __future__ import annotations
from typing import List, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialogButtonBox,
    QMessageBox,
)


class MappingDialog(QDialog):
    def __init__(self, type_name: str, leaf_paths: List[Tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Custom mapping: {type_name}")
        self.resize(900, 520)
        self._leaf_paths = leaf_paths
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Select one or more numeric message fields to plot/export for this custom type."))

        self.lst_paths = QListWidget()
        for path, kind in self._leaf_paths:
            item = QListWidgetItem(f"{path} [{kind}]")
            item.setData(256, {"path": path, "kind": kind})
            self.lst_paths.addItem(item)
        lay.addWidget(self.lst_paths)

        row = QHBoxLayout()
        self.txt_alias = QLineEdit()
        self.txt_alias.setPlaceholderText("Alias (optional, default uses path)")
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["scalar", "array_channels"])
        btn_add = QPushButton("Add Field")
        btn_add.clicked.connect(self._add_selected_field)
        row.addWidget(self.txt_alias)
        row.addWidget(self.cmb_mode)
        row.addWidget(btn_add)
        lay.addLayout(row)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Path", "Alias", "Mode"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        lay.addWidget(self.tbl)

        btn_remove = QPushButton("Remove Selected Mapping")
        btn_remove.clicked.connect(self._remove_selected_mapping)
        lay.addWidget(btn_remove)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept_with_validation)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add_selected_field(self):
        item = self.lst_paths.currentItem()
        if item is None:
            return

        data = item.data(256)
        path = data["path"]
        kind = data["kind"]
        alias = self.txt_alias.text().strip() or path.replace(".", "_")
        mode = self.cmb_mode.currentText()
        if kind == "array" and mode == "scalar":
            mode = "array_channels"

        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self.tbl.setItem(row, 0, QTableWidgetItem(path))
        self.tbl.setItem(row, 1, QTableWidgetItem(alias))
        self.tbl.setItem(row, 2, QTableWidgetItem(mode))
        self.txt_alias.clear()

    def _remove_selected_mapping(self):
        row = self.tbl.currentRow()
        if row >= 0:
            self.tbl.removeRow(row)

    def _accept_with_validation(self):
        if self.tbl.rowCount() == 0:
            QMessageBox.warning(self, "Missing mapping", "Add at least one field mapping.")
            return
        self.accept()

    def result_mapping(self):
        fields = []
        for i in range(self.tbl.rowCount()):
            path_item = self.tbl.item(i, 0)
            alias_item = self.tbl.item(i, 1)
            mode_item = self.tbl.item(i, 2)
            path = path_item.text().strip() if path_item else ""
            alias = alias_item.text().strip() if alias_item else ""
            mode = mode_item.text().strip() if mode_item else "scalar"
            if not path:
                continue
            fields.append(
                {
                    "path": path,
                    "alias": alias or path.replace(".", "_"),
                    "mode": mode,
                }
            )
        return {"fields": fields}
