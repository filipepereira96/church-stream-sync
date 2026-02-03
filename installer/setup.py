"""
Graphical setup wizard for the system.

This module provides a PyQt5-based setup wizard that guides users through
the initial configuration of the Church Stream Sync system.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from src.core import logger
from src.core.config import AudioPCConfig, NetworkConfig, UIConfig, get_config
from src.core.network import NetworkChecker
from src.core.validators import (
    normalize_mac,
    validate_ip,
    validate_mac,
    validate_username,
)
from src.utils.windows import WindowsTaskManager


if TYPE_CHECKING:
    from src.core.config import Config


class TestConnectionThread(QThread):
    """Thread to test connection without blocking UI."""

    finished_signal = pyqtSignal(bool, str)

    def __init__(self, ip: str, username: str, password: str) -> None:
        super().__init__()
        self.ip = ip
        self.username = username
        self.password = password

    def run(self) -> None:
        """Test connection to the Audio PC."""
        try:
            # Test ping
            pingable, latency = NetworkChecker.ping(self.ip, 2000)

            if not pingable:
                self.finished_signal.emit(False, "PC de Áudio não responde a ping")
                return

            # Test PowerShell Remoting (port 5985)
            port_open = NetworkChecker.check_port(self.ip, 5985, 3000)

            if not port_open:
                self.finished_signal.emit(False, "Porta WinRM (5985) não está aberta")
                return

            self.finished_signal.emit(True, f"Conexão OK (latência: {latency}ms)")

        except Exception as e:
            self.finished_signal.emit(False, f"Erro: {e!s}")


class WelcomePage(QWizardPage):
    """Welcome page."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Bem-vindo ao Church Stream Sync")
        self.setSubTitle(
            "Este assistente irá configurar a sincronização automática "
            "entre o PC OBS e o PC de Áudio."
        )

        layout = QVBoxLayout()

        # Explanatory text
        info_text = QLabel(
            "<h3>O que este sistema faz?</h3>"
            "<p>Sincroniza automaticamente dois computadores usados na transmissão ao vivo:</p>"
            "<ul>"
            "<li><b>PC OBS:</b> Computador principal (onde está o OBS Studio)</li>"
            "<li><b>PC de Áudio:</b> Computador conectado à mesa de som</li>"
            "</ul>"
            "<p><b>Como funciona:</b></p>"
            "<ul>"
            "<li>Ao ligar o PC OBS → PC de Áudio liga automaticamente</li>"
            "<li>Ao desligar o PC OBS → PC de Áudio desliga junto</li>"
            "</ul>"
            "<p>Clique em 'Próximo' para começar a configuração.</p>"
        )
        info_text.setWordWrap(True)
        layout.addWidget(info_text)

        layout.addStretch()
        self.setLayout(layout)


class AudioPCConfigPage(QWizardPage):
    """Audio PC configuration page."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Configuração do PC de Áudio")
        self.setSubTitle("Insira as informações do computador conectado à mesa de som.")
        self.test_thread: TestConnectionThread | None = None

        layout = QFormLayout()

        # Friendly name
        self.name_edit = QLineEdit("PC Áudio")
        layout.addRow("Nome do PC de Áudio:", self.name_edit)

        # IP
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("Ex: 192.168.1.100")
        layout.addRow("Endereço IP:", self.ip_edit)

        # MAC Address
        self.mac_edit = QLineEdit()
        self.mac_edit.setPlaceholderText("Ex: 00-11-22-33-44-55")
        layout.addRow("Endereço MAC:", self.mac_edit)

        # Button to help find MAC
        mac_help = QPushButton("Como encontrar o MAC?")
        mac_help.clicked.connect(self._show_mac_help)
        layout.addRow("", mac_help)

        # Username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Ex: Administrador")
        layout.addRow("Usuário (com admin):", self.username_edit)

        # Password (optional)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(
            "(opcional - deixe vazio se conta sem senha)"
        )
        layout.addRow("Senha:", self.password_edit)

        # Test button
        self.test_button = QPushButton("Testar Conexão")
        self.test_button.clicked.connect(self._test_connection)
        layout.addRow("", self.test_button)

        # Test result
        self.test_result = QLabel("")
        layout.addRow("", self.test_result)

        self.setLayout(layout)

        # Register fields (* = required)
        self.registerField("audio_pc_name*", self.name_edit)
        self.registerField("audio_pc_ip*", self.ip_edit)
        self.registerField("audio_pc_mac*", self.mac_edit)
        self.registerField("audio_pc_username*", self.username_edit)
        self.registerField("audio_pc_password", self.password_edit)  # Optional

    def validatePage(self) -> bool:
        """Validate fields before advancing."""
        # Validate IP
        if not validate_ip(self.ip_edit.text()):
            QMessageBox.warning(
                self, "IP Inválido", "Por favor, insira um endereço IP válido."
            )
            return False

        # Validate MAC
        if not validate_mac(self.mac_edit.text()):
            QMessageBox.warning(
                self,
                "MAC Inválido",
                "Por favor, insira um endereço MAC válido.\n"
                "Formatos aceitos: XX-XX-XX-XX-XX-XX ou XX:XX:XX:XX:XX:XX",
            )
            return False

        # Validate username
        if not validate_username(self.username_edit.text()):
            QMessageBox.warning(
                self, "Usuário Inválido", "Nome de usuário contém caracteres inválidos."
            )
            return False

        return True

    def _show_mac_help(self) -> None:
        """Show help for finding MAC address."""
        help_text = (
            "Para encontrar o MAC Address no PC de Áudio:\n\n"
            "1. Abra o Prompt de Comando (cmd)\n"
            "2. Digite: ipconfig /all\n"
            "3. Procure por 'Endereço Físico' na placa de rede ativa\n"
            "4. O formato será algo como: 00-1A-2B-3C-4D-5E\n\n"
            "Ou use o PowerShell:\n"
            "Get-NetAdapter | Select-Object Name, MacAddress"
        )

        QMessageBox.information(self, "Como Encontrar o MAC Address", help_text)

    def _test_connection(self) -> None:
        """Test connection to the Audio PC."""
        ip = self.ip_edit.text()
        username = self.username_edit.text()
        password = self.password_edit.text()

        if not ip or not username:
            QMessageBox.warning(
                self,
                "Campos Incompletos",
                "Preencha IP e usuário antes de testar.\n(Senha é opcional para contas sem senha)",
            )
            return

        self.test_button.setEnabled(False)
        self.test_result.setText("Testando...")

        self.test_thread = TestConnectionThread(ip, username, password)
        self.test_thread.finished_signal.connect(self._on_test_finished)
        self.test_thread.start()

    def _on_test_finished(self, success: bool, message: str) -> None:
        """Callback for connection test."""
        self.test_button.setEnabled(True)

        if success:
            self.test_result.setText(f"✅ {message}")
            self.test_result.setStyleSheet("color: green;")
        else:
            self.test_result.setText(f"❌ {message}")
            self.test_result.setStyleSheet("color: red;")


class AdvancedConfigPage(QWizardPage):
    """Advanced configuration page."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Configurações Avançadas")
        self.setSubTitle("Ajuste parâmetros opcionais (valores padrão funcionam bem).")

        layout = QVBoxLayout()

        # Network group
        network_group = QGroupBox("Parâmetros de Rede")
        network_layout = QFormLayout()

        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 20)
        self.max_retries.setValue(10)
        network_layout.addRow("Máximo de tentativas:", self.max_retries)

        self.retry_interval = QSpinBox()
        self.retry_interval.setRange(5, 60)
        self.retry_interval.setValue(15)
        self.retry_interval.setSuffix(" segundos")
        network_layout.addRow("Intervalo entre tentativas:", self.retry_interval)

        network_group.setLayout(network_layout)
        layout.addWidget(network_group)

        # Interface group
        ui_group = QGroupBox("Interface do Usuário")
        ui_layout = QVBoxLayout()

        self.show_startup = QCheckBox("Mostrar janela ao iniciar")
        self.show_startup.setChecked(True)
        ui_layout.addWidget(self.show_startup)

        self.show_notifications = QCheckBox("Mostrar notificações")
        self.show_notifications.setChecked(True)
        ui_layout.addWidget(self.show_notifications)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        layout.addStretch()
        self.setLayout(layout)

        # Register fields
        self.registerField("max_retries", self.max_retries)
        self.registerField("retry_interval", self.retry_interval)
        self.registerField("show_startup", self.show_startup)
        self.registerField("show_notifications", self.show_notifications)


class SummaryPage(QWizardPage):
    """Summary and confirmation page."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Resumo da Configuração")
        self.setSubTitle("Revise as configurações antes de finalizar.")

        layout = QVBoxLayout()

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)

        self.setLayout(layout)

    def initializePage(self) -> None:
        """Update summary when page is displayed."""
        mac_normalized = normalize_mac(str(self.field("audio_pc_mac")))
        summary = "<h3>Configurações:</h3>"
        summary += "<table cellpadding='5'>"
        summary += f"<tr><td><b>PC de Áudio:</b></td><td>{self.field('audio_pc_name')}</td></tr>"
        summary += f"<tr><td><b>IP:</b></td><td>{self.field('audio_pc_ip')}</td></tr>"
        summary += f"<tr><td><b>MAC:</b></td><td>{mac_normalized}</td></tr>"
        summary += f"<tr><td><b>Usuário:</b></td><td>{self.field('audio_pc_username')}</td></tr>"
        summary += f"<tr><td><b>Max Tentativas:</b></td><td>{self.field('max_retries')}</td></tr>"
        summary += f"<tr><td><b>Intervalo:</b></td><td>{self.field('retry_interval')}s</td></tr>"
        show_startup = "Sim" if self.field("show_startup") else "Não"
        show_notif = "Sim" if self.field("show_notifications") else "Não"
        summary += f"<tr><td><b>Janela Inicial:</b></td><td>{show_startup}</td></tr>"
        summary += f"<tr><td><b>Notificações:</b></td><td>{show_notif}</td></tr>"
        summary += "</table>"

        self.summary_text.setHtml(summary)


class SetupWizard(QWizard):
    """Setup wizard."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Church Stream Sync - Instalador")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setFixedSize(700, 500)

        # Add pages
        self.addPage(WelcomePage())
        self.addPage(AudioPCConfigPage())
        self.addPage(AdvancedConfigPage())
        self.addPage(SummaryPage())

        # Connect signals
        self.finished.connect(self._on_finished)

    def _on_finished(self, result: int) -> None:
        """Called when wizard is completed."""
        if result == QWizard.Accepted:
            self._save_configuration()

    def _save_configuration(self) -> None:
        """Save the configuration."""
        try:
            config: Config = get_config()

            # Audio PC configuration
            mac_normalized = normalize_mac(str(self.field("audio_pc_mac")))
            config.audio_pc = AudioPCConfig(
                name=str(self.field("audio_pc_name")),
                ip_address=str(self.field("audio_pc_ip")),
                mac_address=mac_normalized or "",
                username=str(self.field("audio_pc_username")),
                password=str(self.field("audio_pc_password")),
            )

            # Network configuration
            config.network = NetworkConfig(
                max_retries=int(self.field("max_retries")),
                retry_interval=int(self.field("retry_interval")),
            )

            # UI configuration
            config.ui = UIConfig(
                show_startup_window=bool(self.field("show_startup")),
                show_notifications=bool(self.field("show_notifications")),
            )

            # Save
            if config.save():
                logger.info("Configuration saved successfully")

                # Create scheduled tasks (startup and shutdown)
                self._create_scheduled_tasks()
            else:
                QMessageBox.critical(
                    self, "Erro", "Não foi possível salvar a configuração."
                )

        except Exception as e:
            logger.exception("Error saving configuration")
            QMessageBox.critical(self, "Erro", f"Erro ao salvar configuração:\n{e!s}")

    def _create_scheduled_tasks(self) -> None:
        """Create Windows scheduled tasks (startup and shutdown)."""

        try:
            # Determine executable paths
            exe_path = Path(sys.executable)

            if exe_path.name.lower() == "python.exe":
                # In development - use Python scripts
                base_path = Path(__file__).parent.parent
                startup_exe = f'"{sys.executable}" "{base_path / "src" / "main.py"}"'
                shutdown_exe = (
                    f'"{sys.executable}" "{base_path / "src" / "shutdown.py"}"'
                )
            else:
                # Compiled executable
                base_path = exe_path.parent
                startup_exe = str(base_path / "ChurchStreamSync.exe")
                shutdown_exe = str(base_path / "ChurchShutdown.exe")

            messages = []

            # Create startup task
            logger.info("Creating startup task...")
            success, msg = WindowsTaskManager.create_startup_task(startup_exe)
            if success:
                messages.append("✓ Inicialização automática configurada")
            else:
                messages.append(f"⚠ Startup: {msg}")

            # Create shutdown task
            logger.info("Creating shutdown task...")
            success, msg = WindowsTaskManager.create_shutdown_task(shutdown_exe)
            if success:
                messages.append("✓ Desligamento automático configurado")
            else:
                messages.append(f"⚠ Shutdown: {msg}")

            # Check task status
            status = WindowsTaskManager.check_tasks()

            if status["startup"] and status["shutdown"]:
                logger.info("Both tasks created successfully")
                QMessageBox.information(
                    self,
                    "Instalação Concluída",
                    "O sistema foi configurado com sucesso!\n\n"
                    + "\n".join(messages)
                    + "\n\n"
                    + "IMPORTANTE:\n"
                    + "• Ao fazer LOGIN → PC de Áudio liga automaticamente\n"
                    + "• Ao fazer LOGOFF/SHUTDOWN → PC de Áudio desliga junto\n\n"
                    + "Faça logout e login novamente para ativar o sistema.",
                )
            elif status["startup"]:
                logger.warning("Only startup task was created")
                QMessageBox.warning(
                    self,
                    "Configuração Parcial",
                    "O sistema foi parcialmente configurado:\n\n"
                    + "\n".join(messages)
                    + "\n\n"
                    + "O PC de Áudio irá ligar automaticamente,\n"
                    + "mas pode ser necessário desligá-lo manualmente.\n\n"
                    + "Execute o instalador novamente com privilégios de administrador.",
                )
            else:
                logger.error("Failed to create tasks")
                QMessageBox.critical(
                    self,
                    "Erro de Configuração",
                    "Não foi possível configurar as tarefas automáticas:\n\n"
                    + "\n".join(messages)
                    + "\n\n"
                    + "Execute o instalador como Administrador.",
                )

        except Exception as e:
            logger.exception("Error creating scheduled tasks")
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao configurar tarefas automáticas:\n{e!s}\n\n"
                + "Execute o instalador como Administrador.",
            )


def main() -> None:
    """Main function for the installer."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    wizard = SetupWizard()
    wizard.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
