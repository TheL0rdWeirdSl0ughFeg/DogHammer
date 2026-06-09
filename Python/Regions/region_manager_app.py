import subprocess
import sys

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView

from config.server_config import load_server_config, save_server_config

from Regions.region_tools import (
    get_users,
    view_storage_assignments,
    create_storage_assignment,
    update_storage_assignment,
    set_storage_enabled,
    create_user_storage_directory,
    list_user_storage_directory
)


class RegionManager(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.server_process = None
        self.server_config = load_server_config()
        self.selected_username = None

        self.status = Label(
            text="Region Manager loaded",
            size_hint_y=None,
            height=50
        )
        self.add_widget(self.status)

        self.build_server_controls()

        self.body = BoxLayout(orientation="horizontal")
        self.add_widget(self.body)

        self.user_panel = BoxLayout(orientation="vertical", size_hint_x=0.3)
        self.assignment_panel = BoxLayout(orientation="vertical", size_hint_x=0.7)

        self.body.add_widget(self.user_panel)
        self.body.add_widget(self.assignment_panel)

        self.build_user_panel()
        self.build_assignment_panel()
        self.refresh_all()

    def build_server_controls(self):
        controls = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=50,
            spacing=5
        )

        controls.add_widget(Label(text="Host", size_hint_x=None, width=60))

        self.host_input = TextInput(
            text=str(self.server_config.get("host", "0.0.0.0")),
            multiline=False,
            size_hint_x=None,
            width=220
        )
        controls.add_widget(self.host_input)

        controls.add_widget(Label(text="Port", size_hint_x=None, width=60))

        self.port_input = TextInput(
            text=str(self.server_config.get("port", 8000)),
            multiline=False,
            size_hint_x=None,
            width=120
        )
        controls.add_widget(self.port_input)

        save_button = Button(text="Save Server Config", size_hint_x=None, width=180)
        save_button.bind(on_press=lambda _: self.save_server_settings())

        start_button = Button(text="Start Server", size_hint_x=None, width=140)
        start_button.bind(on_press=lambda _: self.start_server())

        stop_button = Button(text="Stop Server", size_hint_x=None, width=140)
        stop_button.bind(on_press=lambda _: self.stop_server())

        controls.add_widget(save_button)
        controls.add_widget(start_button)
        controls.add_widget(stop_button)

        self.add_widget(controls)

    def save_server_settings(self):
        try:
            port = int(self.port_input.text)
        except ValueError:
            self.status.text = "Port must be a number"
            return

        host = self.host_input.text.strip()

        if not host:
            self.status.text = "Host cannot be blank"
            return

        save_server_config(host, port)
        self.server_config = load_server_config()
        self.status.text = f"Server config saved: {host}:{port}"

    def start_server(self):
        if self.server_process is not None:
            if self.server_process.poll() is None:
                self.status.text = "Server already running"
                return

        self.server_process = None

        self.save_server_settings()

        host = self.host_input.text.strip()
        port = self.port_input.text.strip()

        try:
            self.server_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "API.api:app",
                    "--host",
                    host,
                    "--port",
                    port
                ]
            )

            self.status.text = f"Server started on {host}:{port}"

        except OSError as err:
            self.server_process = None
            self.status.text = f"SERVER_START_ERROR: {err}"

    def stop_server(self):
        if self.server_process is None:
            self.status.text = "Server is not running from this app"
            return

        if self.server_process.poll() is not None:
            self.server_process = None
            self.status.text = "Server already stopped"
            return

        self.server_process.terminate()
        self.server_process = None
        self.status.text = "Server stopped"

    def build_user_panel(self):
        self.user_panel.add_widget(Label(text="Users", size_hint_y=None, height=40))

        self.user_list = GridLayout(cols=1, size_hint_y=None)
        self.user_list.bind(minimum_height=self.user_list.setter("height"))

        scroll = ScrollView()
        scroll.add_widget(self.user_list)
        self.user_panel.add_widget(scroll)

        refresh_button = Button(text="Refresh", size_hint_y=None, height=45)
        refresh_button.bind(on_press=lambda _: self.refresh_all())
        self.user_panel.add_widget(refresh_button)

    def build_assignment_panel(self):
        self.assignment_panel.add_widget(
            Label(text="FILES Region Assignments", size_hint_y=None, height=40)
        )

        form = GridLayout(cols=2, size_hint_y=None, height=180)

        form.add_widget(Label(text="Volume"))
        self.volume_input = TextInput(text="D", multiline=False)
        form.add_widget(self.volume_input)

        form.add_widget(Label(text="Region Root"))
        self.region_root_input = TextInput(text="RegionStorage", multiline=False)
        form.add_widget(self.region_root_input)

        form.add_widget(Label(text="Filepath"))
        self.filepath_input = TextInput(text="", multiline=False)
        form.add_widget(self.filepath_input)

        self.assignment_panel.add_widget(form)

        buttons = GridLayout(cols=5, size_hint_y=None, height=45)

        create_button = Button(text="Create")
        create_button.bind(on_press=lambda _: self.create_assignment())

        update_button = Button(text="Update")
        update_button.bind(on_press=lambda _: self.update_assignment())

        enable_button = Button(text="Enable")
        enable_button.bind(on_press=lambda _: self.set_enabled(True))

        disable_button = Button(text="Disable")
        disable_button.bind(on_press=lambda _: self.set_enabled(False))

        contents_button = Button(text="View Contents")
        contents_button.bind(on_press=lambda _: self.view_folder_contents())

        buttons.add_widget(create_button)
        buttons.add_widget(update_button)
        buttons.add_widget(enable_button)
        buttons.add_widget(disable_button)
        buttons.add_widget(contents_button)

        self.assignment_panel.add_widget(buttons)

        self.assignment_list = GridLayout(cols=1, size_hint_y=None)
        self.assignment_list.bind(minimum_height=self.assignment_list.setter("height"))

        assignment_scroll = ScrollView()
        assignment_scroll.add_widget(self.assignment_list)
        self.assignment_panel.add_widget(assignment_scroll)

        self.assignment_panel.add_widget(
            Label(text="Selected User Folder Contents", size_hint_y=None, height=40)
        )

        self.folder_list = GridLayout(cols=1, size_hint_y=None)
        self.folder_list.bind(minimum_height=self.folder_list.setter("height"))

        folder_scroll = ScrollView()
        folder_scroll.add_widget(self.folder_list)
        self.assignment_panel.add_widget(folder_scroll)

    def refresh_all(self):
        self.load_users()
        self.load_assignments()

    def load_users(self):
        self.user_list.clear_widgets()

        result = get_users()

        if not result.get("success"):
            self.status.text = str(result)
            return

        for user in result["users"]:
            label = f"{user['username']} ({user['role']})"

            button = Button(text=label, size_hint_y=None, height=40)
            button.bind(
                on_press=lambda _, username=user["username"]: self.select_user(username)
            )

            self.user_list.add_widget(button)

    def load_assignments(self):
        self.assignment_list.clear_widgets()

        result = view_storage_assignments()

        if not result.get("success"):
            self.status.text = str(result)
            return

        for assignment in result["assignments"]:
            text = (
                f"{assignment['username']} | "
                f"{assignment['user_path']} | "
                f"enabled={assignment['enabled']}"
            )

            self.assignment_list.add_widget(
                Label(text=text, size_hint_y=None, height=35)
            )

    def select_user(self, username: str):
        self.selected_username = username
        self.filepath_input.text = f"Users\\{username}"
        self.status.text = f"Selected user: {username}"
        self.view_folder_contents()

    def create_assignment(self):
        if not self.selected_username:
            self.status.text = "Select a user first"
            return

        result = create_storage_assignment(
            username=self.selected_username,
            volume=self.volume_input.text,
            region_root=self.region_root_input.text,
            filepath=self.filepath_input.text
        )

        if not result.get("success"):
            self.status.text = str(result)
            self.refresh_all()
            return

        directory_result = create_user_storage_directory(self.selected_username)

        if not directory_result.get("success"):
            self.status.text = str(directory_result)
            self.refresh_all()
            return

        self.status.text = f"Created assignment and directory: {directory_result['user_path']}"

        self.refresh_all()
        self.view_folder_contents()

    def update_assignment(self):
        if not self.selected_username:
            self.status.text = "Select a user first"
            return

        result = update_storage_assignment(
            username=self.selected_username,
            volume=self.volume_input.text,
            region_root=self.region_root_input.text,
            filepath=self.filepath_input.text
        )

        if not result.get("success"):
            self.status.text = str(result)
            self.refresh_all()
            return

        directory_result = create_user_storage_directory(self.selected_username)

        if not directory_result.get("success"):
            self.status.text = str(directory_result)
            self.refresh_all()
            return

        self.status.text = f"Updated assignment and directory: {directory_result['user_path']}"

        self.refresh_all()
        self.view_folder_contents()

    def set_enabled(self, enabled: bool):
        if not self.selected_username:
            self.status.text = "Select a user first"
            return

        result = set_storage_enabled(
            username=self.selected_username,
            enabled=enabled
        )

        self.status.text = str(result)
        self.refresh_all()

    def view_folder_contents(self):
        self.folder_list.clear_widgets()

        if not self.selected_username:
            self.status.text = "Select a user first"
            return

        result = list_user_storage_directory(self.selected_username)

        if not result.get("success"):
            self.folder_list.add_widget(
                Label(text=str(result), size_hint_y=None, height=35)
            )
            self.status.text = str(result)
            return

        self.status.text = f"Viewing: {result['user_path']}"

        entries = result["entries"]

        if not entries:
            self.folder_list.add_widget(
                Label(text="Folder is empty", size_hint_y=None, height=35)
            )
            return

        for entry in entries:
            text = f"{entry['type']} | {entry['name']} | size={entry['size']}"

            self.folder_list.add_widget(
                Label(text=text, size_hint_y=None, height=35)
            )


class RegionManagerApp(App):
    def build(self):
        return RegionManager()


if __name__ == "__main__":
    RegionManagerApp().run()