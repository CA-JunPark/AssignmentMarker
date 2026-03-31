import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTreeView, 
    QTableView, QPushButton, QLineEdit, QLabel, QInputDialog, 
    QMessageBox, QSplitter, QHeaderView, QMenu, QDialog, QListWidget, QListWidgetItem,
    QApplication, QStyledItemDelegate, QStyleOptionButton, QStyle
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
from src.app_state import AppState

class CopyButtonDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pressed_row = -1
        
    def paint(self, painter, option, index):
        btn_opt = QStyleOptionButton()
        # Add some padding
        rect = option.rect.adjusted(4, 4, -4, -4)
        btn_opt.rect = rect
        btn_opt.text = "Copy"
        
        if self.pressed_row == index.row():
            btn_opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Sunken
        else:
            btn_opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised
            
        QApplication.style().drawControl(QStyle.ControlElement.CE_PushButton, btn_opt, painter)
            
    def editorEvent(self, event, model, option, index):
        rect = option.rect.adjusted(4, 4, -4, -4)
        
        if event.type() == event.Type.MouseButtonPress:
            if rect.contains(event.pos()):
                self.pressed_row = index.row()
                self.parent().viewport().update()
                return True
            
        elif event.type() == event.Type.MouseButtonRelease:
            if self.pressed_row != -1:
                is_clicked = self.pressed_row == index.row() and rect.contains(event.pos())
                self.pressed_row = -1
                self.parent().viewport().update()
                
                if is_clicked:
                    table_view = self.parent()
                    window = table_view.window()
                    source_index = model.mapToSource(index)
                    window.copy_student_data(source_index.row())
                return True
                
        return False

class SpreadsheetModel(QAbstractTableModel):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.assignment = None
        self.headers = ["Action", "Student Name", "Total", "Note"]
        self.marking_schemes = []

    def update_data(self):
        self.beginResetModel()
        self.assignment = self.app_state.selected_assignment
        self.headers = ["Action", "Student Name"]
        if self.assignment:
            self.marking_schemes = self.assignment.marking_schemes
            for scheme in self.marking_schemes:
                self.headers.append(scheme.name)
        self.headers.extend(["Total", "Note"])
        self.endResetModel()

    def rowCount(self, parent=None):
        if not self.assignment: return 0
        return len(self.assignment.students)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not self.assignment:
            return None

        student = self.assignment.students[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return "" # Button drawn by delegate
            if col == 1:
                group_name = next((g.name for g in self.app_state.groups if g.id == student.group_id), None)
                return student.name + (f" ({group_name})" if group_name else "")
            
            # Note column
            if col == len(self.headers) - 1:
                if self.marking_schemes:
                    grade = self.app_state.get_grade(student.id, self.marking_schemes[0].id)
                    return grade.note if grade else ""
                return ""
                
            # Total column
            if col == len(self.headers) - 2:
                total = self.app_state.get_total_grade(student.id, self.assignment.id)
                return f"{int(total) if total.is_integer() else total}"
            
            # Grade columns
            scheme_idx = col - 2
            if 0 <= scheme_idx < len(self.marking_schemes):
                grade = self.app_state.get_grade(student.id, self.marking_schemes[scheme_idx].id)
                if grade and grade.score is not None:
                    return f"{int(grade.score) if grade.score.is_integer() else grade.score}"
                return ""

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or not self.assignment:
            return False

        if role == Qt.ItemDataRole.EditRole:
            student = self.assignment.students[index.row()]
            col = index.column()
            
            # Edit Grade
            if 2 <= col < 2 + len(self.marking_schemes):
                scheme = self.marking_schemes[col - 2]
                try:
                    score = float(value) if value.strip() else None
                    grade = self.app_state.get_grade(student.id, scheme.id)
                    note = grade.note if grade else ""
                    self.app_state.update_grade(student.id, scheme.id, score, note)
                    tl = self.index(0, 2)
                    br = self.index(self.rowCount() - 1, self.columnCount() - 1)
                    self.dataChanged.emit(tl, br)
                    return True
                except ValueError:
                    return False
                    
            # Edit Note
            if col == len(self.headers) - 1:
                if self.marking_schemes:
                    scheme = self.marking_schemes[0]
                    grade = self.app_state.get_grade(student.id, scheme.id)
                    score = grade.score if grade else None
                    self.app_state.update_grade(student.id, scheme.id, score, value)
                    tl = self.index(0, 2)
                    br = self.index(self.rowCount() - 1, self.columnCount() - 1)
                    self.dataChanged.emit(tl, br)
                    return True

        return False

    def flags(self, index):
        default = super().flags(index)
        col = index.column()
        if 2 <= col < 2 + len(self.marking_schemes) or col == len(self.headers) - 1:
            return default | Qt.ItemFlag.ItemIsEditable
        return default

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if section < len(self.headers):
                return self.headers[section]
        return None

class NumericSortProxyModel(QSortFilterProxyModel):
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        if left.column() == 0:
            return False # Don't sort copy buttons

        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)
        
        try:
            return float(left_data) < float(right_data)
        except (ValueError, TypeError):
            return str(left_data or "").lower() < str(right_data or "").lower()

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        if column == 0:
            return # Disable sorting for Action column
        super().sort(column, order)

class ManageGroupsDialog(QDialog):
    def __init__(self, parent, app_state: AppState):
        super().__init__(parent)
        self.app_state = app_state
        self.setWindowTitle("Manage Groups")
        self.resize(300, 400)
        self.layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.update_list()
        self.layout.addWidget(self.list_widget)
        
        btn_delete = QPushButton("Delete Selected Group")
        btn_delete.clicked.connect(self.delete_group)
        self.layout.addWidget(btn_delete)
        
    def update_list(self):
        self.list_widget.clear()
        for g in self.app_state.groups:
            item = QListWidgetItem(g.name)
            item.setData(Qt.ItemDataRole.UserRole, g.id)
            self.list_widget.addItem(item)
            
    def delete_group(self):
        item = self.list_widget.currentItem()
        if not item: return
        g_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Confirm", f"Are you sure you want to delete group '{item.text()}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.app_state.delete_group(g_id)
            self.update_list()
            pw = self.parent()
            if hasattr(pw, 'table_model'):
                pw.table_model.update_data()

class MainWindow(QMainWindow):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.setWindowTitle("Assignment Marker")
        self.resize(1050, 700)
        self.setup_ui()
        self.update_ui()

    def setup_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sidebar
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Classes"])
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.clicked.connect(self.on_tree_clicked)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_sidebar_menu)
        
        btn_add_class = QPushButton("Add Class")
        btn_add_class.clicked.connect(self.add_class)
        self.btn_add_assignment = QPushButton("Add Assignment")
        self.btn_add_assignment.clicked.connect(self.add_assignment)
        self.btn_add_assignment.setEnabled(False)

        sidebar_layout.addWidget(btn_add_class)
        sidebar_layout.addWidget(self.btn_add_assignment)
        sidebar_layout.addWidget(self.tree_view)
        
        # Main Area
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        self.lbl_selected_context = QLabel("Please select a class and assignment to begin.")
        self.lbl_selected_context.setStyleSheet("font-size: 20px; font-weight: bold; color: #6200EE;")
        main_layout.addWidget(self.lbl_selected_context)
        
        top_controls = QHBoxLayout()
        self.student_input = QLineEdit()
        self.student_input.setPlaceholderText("Add Students (comma separated)")
        self.student_input.returnPressed.connect(self.add_students)
        btn_add_students = QPushButton("Add Students")
        btn_add_students.clicked.connect(self.add_students)
        
        btn_import_folder = QPushButton("Import from Folder")
        btn_import_folder.clicked.connect(self.import_students_from_folder)
        
        self.scheme_input = QLineEdit()
        self.scheme_input.setPlaceholderText("New Marking Scheme Name")
        self.scheme_input.returnPressed.connect(self.add_marking_scheme)
        btn_add_scheme = QPushButton("Add Column")
        btn_add_scheme.clicked.connect(self.add_marking_scheme)
        
        top_controls.addWidget(self.student_input)
        top_controls.addWidget(btn_add_students)
        top_controls.addWidget(btn_import_folder)
        top_controls.addWidget(self.scheme_input)
        top_controls.addWidget(btn_add_scheme)
        
        main_layout.addLayout(top_controls)
        
        # Table View with Proxy for Sorting
        self.table_model = SpreadsheetModel(self.app_state)
        self.proxy_model = NumericSortProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Custom size for Copy column
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_view.setColumnWidth(0, 80)
        self.table_view.setAlternatingRowColors(True)
        
        # Set Delegate for Copy Button
        self.copy_delegate = CopyButtonDelegate(self.table_view)
        self.table_view.setItemDelegateForColumn(0, self.copy_delegate)

        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self.show_header_menu)
        self.table_view.selectionModel().currentChanged.connect(self.on_table_selection_changed)
        
        main_layout.addWidget(self.table_view)

        self.setStyleSheet("""
            QTableView {
                selection-background-color: #6200EE;
            }
        """)

        splitter.addWidget(sidebar_widget)
        splitter.addWidget(main_widget)
        splitter.setSizes([250, 800])
        self.setCentralWidget(splitter)

    def update_ui(self):
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(["Classes"])
        root = self.tree_model.invisibleRootItem()
        
        for cls in self.app_state.classrooms:
            cls_item = QStandardItem(cls.name)
            cls_item.setData(cls.id, Qt.ItemDataRole.UserRole)
            cls_item.setEditable(False)
            
            for ast in cls.assignments:
                ast_item = QStandardItem(ast.name)
                ast_item.setData((cls.id, ast.id), Qt.ItemDataRole.UserRole)
                ast_item.setEditable(False)
                cls_item.appendRow(ast_item)
                
            root.appendRow(cls_item)
            
        self.tree_view.expandAll()
        
        self.btn_add_assignment.setEnabled(bool(self.app_state.selected_classroom))
        
        self.table_model.update_data()
        self.table_view.setColumnWidth(0, 80) # Keep button width fixed
        
        self.update_title_label()

    def update_title_label(self):
        cls = self.app_state.selected_classroom
        ast = self.app_state.selected_assignment
        if cls and ast:
            base_text = f"{cls.name} > {ast.name}"
            sel_model = self.table_view.selectionModel()
            current = sel_model.currentIndex() if sel_model else QModelIndex()
            if current.isValid():
                source_index = self.proxy_model.mapToSource(current)
                col = source_index.column()
                header_text = self.table_model.headerData(col, Qt.Orientation.Horizontal)
                if header_text:
                    self.lbl_selected_context.setText(f"{base_text} > {header_text}")
                else:
                    self.lbl_selected_context.setText(base_text)
            else:
                self.lbl_selected_context.setText(base_text)
        elif cls:
            self.lbl_selected_context.setText(f"{cls.name} (Select an assignment)")
        else:
            self.lbl_selected_context.setText("Please select a class and assignment to begin.")

    def on_table_selection_changed(self, current: QModelIndex, previous: QModelIndex):
        self.update_title_label()

    def on_tree_clicked(self, index: QModelIndex):
        item = self.tree_model.itemFromIndex(index)
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if isinstance(data, str):
            cls = next((c for c in self.app_state.classrooms if c.id == data), None)
            self.app_state.select_classroom(cls)
        elif isinstance(data, tuple):
            c_id, a_id = data
            cls = next((c for c in self.app_state.classrooms if c.id == c_id), None)
            self.app_state.select_classroom(cls)
            if self.app_state.selected_classroom:
                ast = next((a for a in self.app_state.selected_classroom.assignments if a.id == a_id), None)
                self.app_state.select_assignment(ast)
                
        self.update_ui()

    def add_class(self):
        name, ok = QInputDialog.getText(self, "Add Class", "Class Name:")
        if ok and name.strip():
            try:
                self.app_state.add_classroom(name.strip())
                self.update_ui()
            except ValueError as e:
                QMessageBox.critical(self, "Duplicate Error", str(e))

    def add_assignment(self):
        cls = self.app_state.selected_classroom
        if not cls: return
        name, ok = QInputDialog.getText(self, "Add Assignment", "Assignment Name:")
        if ok and name.strip():
            try:
                self.app_state.add_assignment(cls.id, name.strip())
                self.update_ui()
            except ValueError as e:
                QMessageBox.critical(self, "Duplicate Error", str(e))

    def add_students(self):
        ast = self.app_state.selected_assignment
        if not ast: return
        names = self.student_input.text()
        try:
            self.app_state.add_students(ast.id, names)
            self.student_input.clear()
            self.update_ui()
        except ValueError as e:
            QMessageBox.critical(self, "Duplicate Error", str(e))

    def import_students_from_folder(self):
        import os
        from PySide6.QtWidgets import QFileDialog
        
        ast = self.app_state.selected_assignment
        if not ast: return
        
        folder_path = QFileDialog.getExistingDirectory(self, "Select Submissions Folder")
        if not folder_path: return
        
        names_to_add = []
        try:
            for entry in os.scandir(folder_path):
                if entry.is_dir():
                    parts = entry.name.split("_")
                    if len(parts) >= 2:
                        student_name = parts[0].strip()
                        if student_name:
                            names_to_add.append(student_name)
                            
            if not names_to_add:
                QMessageBox.information(self, "Import", "No valid student folders found.")
                return
                
            comma_separated_names = ",".join(names_to_add)
            self.app_state.add_students(ast.id, comma_separated_names)
            self.student_input.clear()
            self.update_ui()
            QMessageBox.information(self, "Import Successful", f"Successfully imported {len(names_to_add)} students.")
            
        except ValueError as e:
            QMessageBox.critical(self, "Duplicate Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import students: {e}")

    def add_marking_scheme(self):
        ast = self.app_state.selected_assignment
        if not ast: return
        name = self.scheme_input.text()
        if name.strip():
            try:
                self.app_state.add_marking_scheme(ast.id, name.strip())
                self.scheme_input.clear()
                self.update_ui()
            except ValueError as e:
                QMessageBox.critical(self, "Duplicate Error", str(e))

    def confirm_delete(self, message: str) -> bool:
        reply = QMessageBox.question(
            self, "Confirm Delete", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def show_sidebar_menu(self, pos):
        index = self.tree_view.indexAt(pos)
        if not index.isValid(): return
        
        item = self.tree_model.itemFromIndex(index)
        data = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu()
        if isinstance(data, str):
            action = QAction("Delete Class", self)
            action.triggered.connect(lambda checked, d=data, n=item.text(): self.delete_class(d, n))
            menu.addAction(action)
        elif isinstance(data, tuple):
            c_id, a_id = data
            action = QAction("Delete Assignment", self)
            action.triggered.connect(lambda checked, c=c_id, a=a_id, n=item.text(): self.delete_assignment(c, a, n))
            menu.addAction(action)
            
        menu.exec(self.tree_view.viewport().mapToGlobal(pos))

    def delete_class(self, classroom_id: str, name: str):
        if self.confirm_delete(f"Are you sure you want to delete class '{name}'?"):
            self.app_state.delete_classroom(classroom_id)
            self.update_ui()

    def delete_assignment(self, c_id: str, a_id: str, name: str):
        if self.confirm_delete(f"Are you sure you want to delete assignment '{name}'?"):
            self.app_state.delete_assignment(c_id, a_id)
            self.update_ui()

    def show_context_menu(self, pos):
        proxy_index = self.table_view.indexAt(pos)
        if not proxy_index.isValid() or not self.app_state.selected_assignment:
            return
            
        source_index = self.proxy_model.mapToSource(proxy_index)
        row = source_index.row()
        student = self.app_state.selected_assignment.students[row]
        
        menu = QMenu()
        
        copy_action = QAction("Copy Student Data", self)
        copy_action.triggered.connect(lambda checked, r=row: self.copy_student_data(r))
        menu.addAction(copy_action)
        
        menu.addSeparator()

        create_group_action = QAction("Create New Group", self)
        create_group_action.triggered.connect(lambda checked, s_id=student.id: self.create_group(s_id))
        menu.addAction(create_group_action)
        
        manage_groups_action = QAction("Manage Groups...", self)
        manage_groups_action.triggered.connect(lambda checked: self.manage_groups())
        menu.addAction(manage_groups_action)

        if self.app_state.groups:
            menu.addSeparator()
            for group in self.app_state.groups:
                action = QAction(f"Add to '{group.name}'", self)
                action.triggered.connect(lambda checked, s_id=student.id, g_id=group.id: self.add_to_group(s_id, g_id))
                menu.addAction(action)
                
        if student.group_id:
            menu.addSeparator()
            rm_group_action = QAction("Remove from Group", self)
            rm_group_action.triggered.connect(lambda checked, s_id=student.id: self.remove_from_group(s_id))
            menu.addAction(rm_group_action)

        menu.addSeparator()
        delete_student_action = QAction("Delete Student", self)
        delete_student_action.triggered.connect(lambda checked, s_id=student.id, n=student.name: self.delete_student(s_id, n))
        menu.addAction(delete_student_action)
                
        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def copy_student_data(self, source_row: int):
        if not self.app_state.selected_assignment: return
        
        lines = []
        for col in range(1, self.table_model.columnCount()): # Skip 0 since it's "Copy"
            header = self.table_model.headerData(col, Qt.Orientation.Horizontal)
            index = self.table_model.index(source_row, col)
            val = self.table_model.data(index)
            lines.append(f"{header}: {val or ''}")
            
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)

    def create_group(self, student_id: str):
        name, ok = QInputDialog.getText(self, "Create Group", "Group Name:")
        if ok and name.strip():
            try:
                self.app_state.create_group(name.strip(), [student_id])
                self.table_model.update_data()
            except ValueError as e:
                QMessageBox.critical(self, "Duplicate Error", str(e))

    def add_to_group(self, student_id: str, group_id: str):
        self.app_state.add_student_to_group(student_id, group_id)
        self.table_model.update_data()

    def remove_from_group(self, student_id: str):
        self.app_state.remove_student_from_group(student_id)
        self.table_model.update_data()

    def manage_groups(self):
        dlg = ManageGroupsDialog(self, self.app_state)
        dlg.exec()
        
    def delete_student(self, student_id: str, name: str):
        if self.confirm_delete(f"Are you sure you want to delete student '{name}'?"):
            self.app_state.delete_student(self.app_state.selected_assignment.id, student_id)
            self.table_model.update_data()

    def show_header_menu(self, pos):
        col = self.table_view.horizontalHeader().logicalIndexAt(pos)
        if not self.app_state.selected_assignment: return
        schemes = self.app_state.selected_assignment.marking_schemes
        if 2 <= col < 2 + len(schemes):
            scheme = schemes[col - 2]
            menu = QMenu()
            action = QAction(f"Delete Column '{scheme.name}'", self)
            action.triggered.connect(lambda checked, s_id=scheme.id, n=scheme.name: self.delete_scheme(s_id, n))
            menu.addAction(action)
            menu.exec(self.table_view.horizontalHeader().viewport().mapToGlobal(pos))

    def delete_scheme(self, scheme_id: str, name: str):
        if self.confirm_delete(f"Are you sure you want to delete column '{name}'?"):
            self.app_state.delete_marking_scheme(self.app_state.selected_assignment.id, scheme_id)
            self.table_model.update_data()
