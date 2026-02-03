"""
Uninstaller for Church Stream Sync.

This module provides a graphical uninstaller that removes scheduled tasks,
configuration files, and logs created by the system.
"""

from __future__ import annotations

import shutil
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.core.config import Config
from src.utils.windows import WindowsTaskManager


class UninstallDialog(QDialog):
    """Uninstall dialog."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Desinstalar Church Stream Sync")
        self.setFixedSize(500, 400)

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Title
        title = QLabel("Desinstalar Church Stream Sync")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Este processo irá remover o sistema de sincronização automática.\n\n"
            "O que será removido:"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Removal options
        self.remove_tasks = QCheckBox("Tarefas agendadas (startup e shutdown)")
        self.remove_tasks.setChecked(True)
        layout.addWidget(self.remove_tasks)

        self.remove_config = QCheckBox("Configurações salvas")
        self.remove_config.setChecked(True)
        layout.addWidget(self.remove_config)

        self.remove_logs = QCheckBox("Arquivos de log")
        self.remove_logs.setChecked(False)
        layout.addWidget(self.remove_logs)

        # Warning
        warning = QLabel(
            "⚠️ ATENÇÃO: Esta ação não pode ser desfeita!\n"
            "Os executáveis não serão removidos automaticamente."
        )
        warning.setStyleSheet(
            "color: #D83B01; padding: 10px; background-color: #FFF4CE;"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        # Result
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(100)
        self.result_text.hide()
        layout.addWidget(self.result_text)

        # Buttons
        button_layout = QVBoxLayout()

        self.uninstall_button = QPushButton("Desinstalar")
        self.uninstall_button.setStyleSheet("""
            QPushButton {
                background-color: #D83B01;
                color: white;
                padding: 10px;
                font-size: 11pt;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #A52A00;
            }
        """)
        self.uninstall_button.clicked.connect(self._uninstall)
        button_layout.addWidget(self.uninstall_button)

        self.close_button = QPushButton("Cancelar")
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                padding: 10px;
                font-size: 11pt;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #C0C0C0;
            }
        """)
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _uninstall(self) -> None:
        """Execute the uninstall process."""
        # Confirmation
        reply = QMessageBox.question(
            self,
            "Confirmar Desinstalação",
            "Tem certeza de que deseja desinstalar o Church Stream Sync?\n\n"
            "Esta ação não pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        self.result_text.show()
        self.result_text.clear()
        self.uninstall_button.setEnabled(False)

        results = []

        # Remove scheduled tasks
        if self.remove_tasks.isChecked():
            self.result_text.append("Removendo tarefas agendadas...")
            QApplication.processEvents()

            success, msg = WindowsTaskManager.remove_tasks()

            if success:
                results.append("✓ Tarefas removidas")
                self.result_text.append(f"  ✓ {msg}")
            else:
                results.append("✗ Erro ao remover tarefas")
                self.result_text.append(f"  ✗ {msg}")

        # Remove configuration
        if self.remove_config.isChecked():
            self.result_text.append("\nRemovendo configurações...")
            QApplication.processEvents()

            try:
                config = Config()
                if config.CONFIG_FILE.exists():
                    config.CONFIG_FILE.unlink()
                    results.append("✓ Configurações removidas")
                    self.result_text.append("  ✓ Configurações removidas")
                else:
                    results.append("ℹ Configurações não encontradas")
                    self.result_text.append("  ℹ Nenhuma configuração encontrada")
            except Exception as e:
                results.append(f"✗ Erro ao remover configurações: {e}")
                self.result_text.append(f"  ✗ Erro: {e}")

        # Remove logs
        if self.remove_logs.isChecked():
            self.result_text.append("\nRemovendo logs...")
            QApplication.processEvents()

            try:
                config = Config()
                if config.log_dir.exists():
                    shutil.rmtree(config.log_dir)
                    results.append("✓ Logs removidos")
                    self.result_text.append("  ✓ Logs removidos")
                else:
                    results.append("ℹ Logs não encontrados")
                    self.result_text.append("  ℹ Nenhum log encontrado")
            except Exception as e:
                results.append(f"✗ Erro ao remover logs: {e}")
                self.result_text.append(f"  ✗ Erro: {e}")

        # Try to remove config folder if empty
        try:
            config = Config()
            if config.CONFIG_DIR.exists() and not any(config.CONFIG_DIR.iterdir()):
                config.CONFIG_DIR.rmdir()
                self.result_text.append("\n  ✓ Pasta de configuração removida")
        except Exception:
            pass

        # Show final result
        self.result_text.append("\n" + "=" * 50)
        self.result_text.append("\nDesinstalação concluída!")
        self.result_text.append("\n".join(results))
        self.result_text.append("\n" + "=" * 50)

        # Update buttons
        self.uninstall_button.hide()
        self.close_button.setText("Fechar")

        # Final message
        QMessageBox.information(
            self,
            "Desinstalação Concluída",
            "O Church Stream Sync foi desinstalado.\n\n"
            "LEMBRE-SE:\n"
            "• Os executáveis não foram removidos automaticamente\n"
            "• Você pode deletá-los manualmente se desejar\n"
            "• Faça logout e login para aplicar as mudanças",
        )


def main() -> None:
    """Main function for the uninstaller."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dialog = UninstallDialog()
    result = dialog.exec_()

    sys.exit(result)


if __name__ == "__main__":
    main()
