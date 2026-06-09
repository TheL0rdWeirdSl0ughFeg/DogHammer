import os
import requests

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView

from config.server_config import load_client_config, save_client_config


def get_api_base():
    config = load_client_config()
    return config["server_url"]


API_BASE = get_api_base()


class ClientAppLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.session_id = None
        self.role = None
        self.privilege_level = None
        self.selected_file = None
        self.active_service = None

        self.status = Label(text="Not logged in", size_hint_y=None, height=40)
        self.add_widget(self.status)

        self.screen = BoxLayout(orientation="vertical")
        self.add_widget(self.screen)

        self.build_login_screen()

    def open_server_settings_popup(self):
        config = load_client_config()

        layout = BoxLayout(orientation="vertical")

        server_input = TextInput(
            text=config["server_url"],
            multiline=False
        )
        layout.add_widget(server_input)

        save_button = Button(
            text="Save",
            size_hint_y=None,
            height=45
        )
        layout.add_widget(save_button)

        popup = Popup(
            title="Server Settings",
            content=layout,
            size_hint=(0.8, 0.4)
        )

        save_button.bind(
            on_press=lambda _: self.save_server_settings(
                server_input.text,
                popup
            )
        )

        popup.open()

    def save_server_settings(self, server_url: str, popup: Popup):
        global API_BASE

        save_client_config(server_url)
        API_BASE = server_url

        self.status.text = f"Server set to {server_url}"
        popup.dismiss()

    def api_post(self, endpoint: str, payload: dict):
        try:
            response = requests.post(
                f"{API_BASE}{endpoint}",
                json=payload,
                timeout=10
            )
            return response.json()
        except requests.RequestException as err:
            return {"success": False, "error": "REQUEST_ERROR", "detail": str(err)}
        except ValueError:
            return {"success": False, "error": "INVALID_RESPONSE"}

    def clear_screen(self):
        self.screen.clear_widgets()

    def build_login_screen(self):
        self.clear_screen()

        form = GridLayout(cols=2, size_hint_y=None, height=120)

        form.add_widget(Label(text="Username"))
        self.username_input = TextInput(multiline=False)
        form.add_widget(self.username_input)

        form.add_widget(Label(text="Password"))
        self.password_input = TextInput(password=True, multiline=False)
        form.add_widget(self.password_input)

        self.screen.add_widget(form)

        login_button = Button(text="Login", size_hint_y=None, height=45)
        login_button.bind(on_press=lambda _: self.login())
        self.screen.add_widget(login_button)

        settings_button = Button(
            text="Server Settings",
            size_hint_y=None,
            height=45
        )
        settings_button.bind(
            on_press=lambda _: self.open_server_settings_popup()
        )
        self.screen.add_widget(settings_button)

    def login(self):
        result = self.api_post(
            "/login",
            {
                "username": self.username_input.text,
                "password": self.password_input.text
            }
        )

        if not result.get("success"):
            self.status.text = str(result)
            return

        self.session_id = result["portal_session_id"]
        self.role = result["role"]
        self.privilege_level = None
        self.selected_file = None
        self.active_service = None

        self.status.text = f"Logged in as {self.role}"
        self.build_main_screen()

    def build_main_screen(self):
        self.clear_screen()

        top_buttons = GridLayout(cols=4, size_hint_y=None, height=45)

        service_button = Button(text="Select Service")
        service_button.bind(on_press=lambda _: self.open_service_popup())

        clear_button = Button(text="Clear Service")
        clear_button.bind(on_press=lambda _: self.clear_service())

        logout_button = Button(text="Logout")
        logout_button.bind(on_press=lambda _: self.logout())

        top_buttons.add_widget(service_button)
        top_buttons.add_widget(self.build_privilege_button())
        top_buttons.add_widget(clear_button)
        top_buttons.add_widget(logout_button)

        self.screen.add_widget(top_buttons)

        if self.active_service == "FILES":
            self.build_files_screen()

        if self.privilege_level in ("ADMIN", "BACKEND"):
            self.build_admin_tools()

    def build_privilege_button(self):
        if self.role in ("ADMIN", "SUPERADMIN") and self.privilege_level is None:
            button = Button(text="Admin Login")
            button.bind(on_press=lambda _: self.open_admin_login_popup())
            return button

        if self.role == "SUPERADMIN" and self.privilege_level == "ADMIN":
            button = Button(text="Superadmin Login")
            button.bind(on_press=lambda _: self.open_superadmin_login_popup())
            return button

        return Label(text="")

    def open_service_popup(self):
        layout = BoxLayout(orientation="vertical")

        files_button = Button(text="FILES", size_hint_y=None, height=45)
        layout.add_widget(files_button)

        popup = Popup(
            title="Select Service",
            content=layout,
            size_hint=(0.6, 0.4)
        )

        files_button.bind(on_press=lambda _: self.select_files_service(popup))
        popup.open()

    def select_files_service(self, popup: Popup):
        popup.dismiss()
        self.request_files_service()

    def request_files_service(self):
        result = self.api_post(
            "/request_service",
            {
                "session_id": self.session_id,
                "service_type": "REGION",
                "service_name": "FILES"
            }
        )

        self.status.text = str(result)

        if result.get("success"):
            self.active_service = "FILES"
            self.selected_file = None
            self.build_main_screen()
            self.list_files()

    def build_files_screen(self):
        self.screen.add_widget(
            Label(text="FILES Region", size_hint_y=None, height=35)
        )

        file_buttons = GridLayout(cols=4, size_hint_y=None, height=45)

        list_button = Button(text="Refresh Files")
        list_button.bind(on_press=lambda _: self.list_files())

        upload_button = Button(text="Upload")
        upload_button.bind(on_press=lambda _: self.open_upload_popup())

        download_button = Button(text="Download")
        download_button.bind(on_press=lambda _: self.download_selected_file())

        delete_button = Button(text="Delete")
        delete_button.bind(on_press=lambda _: self.delete_selected_file())

        file_buttons.add_widget(list_button)
        file_buttons.add_widget(upload_button)
        file_buttons.add_widget(download_button)
        file_buttons.add_widget(delete_button)

        self.screen.add_widget(file_buttons)

        self.file_list = GridLayout(cols=1, size_hint_y=None)
        self.file_list.bind(minimum_height=self.file_list.setter("height"))

        scroll = ScrollView(size_hint_y=0.45)
        scroll.add_widget(self.file_list)
        self.screen.add_widget(scroll)

    def open_admin_login_popup(self):
        self.open_password_popup(
            title="Admin Login",
            hint_text="Admin password",
            callback=self.admin_login
        )

    def open_superadmin_login_popup(self):
        self.open_password_popup(
            title="Superadmin Login",
            hint_text="Superadmin password",
            callback=self.superadmin_login
        )

    def open_password_popup(self, title: str, hint_text: str, callback):
        layout = BoxLayout(orientation="vertical")

        password_input = TextInput(
            password=True,
            multiline=False,
            hint_text=hint_text
        )

        layout.add_widget(password_input)

        submit_button = Button(text="Submit", size_hint_y=None, height=45)
        layout.add_widget(submit_button)

        popup = Popup(
            title=title,
            content=layout,
            size_hint=(0.7, 0.4)
        )

        submit_button.bind(
            on_press=lambda _: callback(password_input.text, popup)
        )

        popup.open()

    def admin_login(self, password: str, popup: Popup):
        result = self.api_post(
            "/privilege/admin",
            {
                "session_id": self.session_id,
                "admin_password": password
            }
        )

        self.status.text = str(result)
        popup.dismiss()

        if result.get("success") or result.get("result") in (
            "SERVICE_GRANTED",
            "SERVICE_SCOPE_GRANTED",
            "ADMIN_PRIVILEGE_GRANTED"
        ):
            self.privilege_level = "ADMIN"
            self.active_service = None
            self.build_main_screen()

    def superadmin_login(self, password: str, popup: Popup):
        result = self.api_post(
            "/privilege/superadmin",
            {
                "session_id": self.session_id,
                "superadmin_password": password
            }
        )

        self.status.text = str(result)
        popup.dismiss()

        if result.get("success"):
            self.privilege_level = "BACKEND"
            self.active_service = None
            self.build_main_screen()

    def list_files(self):
        result = self.api_post(
            "/region/files/list",
            {
                "session_id": self.session_id
            }
        )

        if not hasattr(self, "file_list"):
            return

        self.file_list.clear_widgets()

        if not result.get("success"):
            self.status.text = str(result)
            return

        self.status.text = "FILES loaded"

        for entry in result["entries"]:
            button = Button(
                text=f"{entry['name']} | {entry['size']} bytes",
                size_hint_y=None,
                height=40
            )

            button.bind(
                on_press=lambda _, filename=entry["name"]: self.select_file(filename)
            )

            self.file_list.add_widget(button)

    def select_file(self, filename: str):
        self.selected_file = filename
        self.status.text = f"Selected file: {filename}"

    def open_upload_popup(self):
        layout = BoxLayout(orientation="vertical")

        chooser = FileChooserListView()
        layout.add_widget(chooser)

        upload_button = Button(text="Upload Selected File", size_hint_y=None, height=45)
        layout.add_widget(upload_button)

        popup = Popup(
            title="Upload File",
            content=layout,
            size_hint=(0.9, 0.9)
        )

        upload_button.bind(
            on_press=lambda _: self.upload_file(chooser.selection, popup)
        )

        popup.open()

    def upload_file(self, selection, popup: Popup):
        if not selection:
            self.status.text = "No file selected"
            return

        file_path = selection[0]

        try:
            with open(file_path, "rb") as file_handle:
                files = {
                    "file": (
                        os.path.basename(file_path),
                        file_handle,
                        "application/octet-stream"
                    )
                }

                data = {"session_id": self.session_id}

                response = requests.post(
                    f"{API_BASE}/region/files/upload",
                    data=data,
                    files=files,
                    timeout=30
                )

            result = response.json()

        except requests.RequestException as err:
            result = {"success": False, "error": "REQUEST_ERROR", "detail": str(err)}
        except OSError as err:
            result = {"success": False, "error": "FILE_ERROR", "detail": str(err)}
        except ValueError:
            result = {"success": False, "error": "INVALID_RESPONSE"}

        self.status.text = str(result)
        popup.dismiss()

        if result.get("success"):
            self.list_files()

    def download_selected_file(self):
        if not self.selected_file:
            self.status.text = "Select a file first"
            return

        try:
            response = requests.post(
                f"{API_BASE}/region/files/download",
                json={
                    "session_id": self.session_id,
                    "filename": self.selected_file
                },
                timeout=30
            )

            if response.headers.get("content-type", "").startswith("application/json"):
                self.status.text = str(response.json())
                return

            download_path = os.path.join(
                os.path.expanduser("~"),
                "Downloads",
                self.selected_file
            )

            with open(download_path, "wb") as output_file:
                output_file.write(response.content)

            self.status.text = f"Downloaded to {download_path}"

        except requests.RequestException as err:
            self.status.text = str({
                "success": False,
                "error": "REQUEST_ERROR",
                "detail": str(err)
            })
        except OSError as err:
            self.status.text = str({
                "success": False,
                "error": "FILE_ERROR",
                "detail": str(err)
            })

    def delete_selected_file(self):
        if not self.selected_file:
            self.status.text = "Select a file first"
            return

        result = self.api_post(
            "/region/files/delete",
            {
                "session_id": self.session_id,
                "filename": self.selected_file
            }
        )

        self.status.text = str(result)

        if result.get("success"):
            self.selected_file = None
            self.list_files()

    def build_admin_tools(self):
        self.screen.add_widget(
            Label(text="Admin Tools", size_hint_y=None, height=35)
        )

        admin_buttons = GridLayout(cols=4, size_hint_y=None, height=90)

        buttons = [
            ("Peek Users", self.admin_peek_users),
            ("Peek Sessions", self.admin_peek_sessions),
            ("Peek Services", self.admin_peek_services),
            ("Peek Logs", self.admin_peek_logs),
            ("Kill Service", self.open_kill_service_popup),
            ("Kill User", self.open_kill_user_popup),
            ("Hammer", self.open_hammer_popup),
            ("Greenlight", self.open_greenlight_popup),
            ("Promote", self.open_promote_popup),
            ("Demote", self.open_demote_popup)
        ]

        for text, callback in buttons:
            button = Button(text=text)
            button.bind(on_press=lambda _, cb=callback: cb())
            admin_buttons.add_widget(button)

        self.screen.add_widget(admin_buttons)

        self.admin_output = GridLayout(cols=1, size_hint_y=None)
        self.admin_output.bind(minimum_height=self.admin_output.setter("height"))

        scroll = ScrollView(size_hint_y=0.45)
        scroll.add_widget(self.admin_output)
        self.screen.add_widget(scroll)

    def show_admin_result(self, result):
        self.status.text = str(result)

        if not hasattr(self, "admin_output"):
            return

        self.admin_output.clear_widgets()

        lines = str(result).split(", ")

        for line in lines:
            self.admin_output.add_widget(
                Label(text=line, size_hint_y=None, height=35)
            )

    def admin_peek_users(self):
        result = self.api_post(
            "/admin/peek_users",
            {"session_id": self.session_id}
        )
        self.show_admin_result(result)

    def admin_peek_sessions(self):
        result = self.api_post(
            "/admin/peek_sessions",
            {"session_id": self.session_id}
        )
        self.show_admin_result(result)

    def admin_peek_services(self):
        result = self.api_post(
            "/admin/peek_services",
            {"session_id": self.session_id}
        )
        self.show_admin_result(result)

    def admin_peek_logs(self):
        result = self.api_post(
            "/admin/peek_logs",
            {
                "session_id": self.session_id,
                "limit": 40
            }
        )
        self.show_admin_result(result)

    def open_target_session_popup(self, title: str, callback):
        layout = BoxLayout(orientation="vertical")

        target_input = TextInput(
            multiline=False,
            hint_text="target_session_id"
        )
        layout.add_widget(target_input)

        submit_button = Button(text="Submit", size_hint_y=None, height=45)
        layout.add_widget(submit_button)

        popup = Popup(
            title=title,
            content=layout,
            size_hint=(0.8, 0.4)
        )

        submit_button.bind(
            on_press=lambda _: callback(target_input.text, popup)
        )

        popup.open()

    def open_target_user_popup(self, title: str, callback):
        layout = BoxLayout(orientation="vertical")

        target_input = TextInput(
            multiline=False,
            hint_text="target_user_id"
        )
        layout.add_widget(target_input)

        submit_button = Button(text="Submit", size_hint_y=None, height=45)
        layout.add_widget(submit_button)

        popup = Popup(
            title=title,
            content=layout,
            size_hint=(0.8, 0.4)
        )

        submit_button.bind(
            on_press=lambda _: callback(target_input.text, popup)
        )

        popup.open()

    def open_kill_service_popup(self):
        self.open_target_session_popup("Kill Service", self.admin_kill_service)

    def open_kill_user_popup(self):
        self.open_target_session_popup("Kill User", self.admin_kill_user)

    def open_hammer_popup(self):
        self.open_target_user_popup("Hammer User", self.admin_hammer)

    def open_greenlight_popup(self):
        self.open_target_user_popup("Greenlight User", self.admin_greenlight)

    def open_promote_popup(self):
        self.open_target_user_popup("Promote User", self.admin_promote)

    def open_demote_popup(self):
        self.open_target_user_popup("Demote User", self.admin_demote)

    def admin_kill_service(self, target_session_id: str, popup: Popup):
        result = self.api_post(
            "/admin/kill_service",
            {
                "session_id": self.session_id,
                "target_session_id": target_session_id
            }
        )
        popup.dismiss()
        self.show_admin_result(result)

    def admin_kill_user(self, target_session_id: str, popup: Popup):
        result = self.api_post(
            "/admin/kill_user",
            {
                "session_id": self.session_id,
                "target_session_id": target_session_id
            }
        )
        popup.dismiss()
        self.show_admin_result(result)

    def admin_hammer(self, target_user_id: str, popup: Popup):
        result = self.api_post(
            "/admin/hammer",
            {
                "session_id": self.session_id,
                "target_user_id": int(target_user_id)
            }
        )
        popup.dismiss()
        self.show_admin_result(result)

    def admin_greenlight(self, target_user_id: str, popup: Popup):
        result = self.api_post(
            "/admin/greenlight",
            {
                "session_id": self.session_id,
                "target_user_id": int(target_user_id)
            }
        )
        popup.dismiss()
        self.show_admin_result(result)

    def admin_promote(self, target_user_id: str, popup: Popup):
        result = self.api_post(
            "/admin/promote",
            {
                "session_id": self.session_id,
                "target_user_id": int(target_user_id)
            }
        )
        popup.dismiss()
        self.show_admin_result(result)

    def admin_demote(self, target_user_id: str, popup: Popup):
        result = self.api_post(
            "/admin/demote",
            {
                "session_id": self.session_id,
                "target_user_id": int(target_user_id)
            }
        )
        popup.dismiss()
        self.show_admin_result(result)

    def clear_service(self):
        result = self.api_post(
            "/clear_service",
            {"session_id": self.session_id}
        )

        self.status.text = str(result)

        if result.get("success"):
            self.privilege_level = None
            self.active_service = None
            self.selected_file = None
            self.build_main_screen()

    def logout(self):
        result = self.api_post(
            "/logout",
            {"session_id": self.session_id}
        )

        self.status.text = str(result)
        self.session_id = None
        self.role = None
        self.privilege_level = None
        self.selected_file = None
        self.active_service = None
        self.build_login_screen()


class ClientApp(App):
    def build(self):
        return ClientAppLayout()


if __name__ == "__main__":
    ClientApp().run()