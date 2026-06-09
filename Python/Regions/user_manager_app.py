import mysql.connector

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

from Daemons.privilege_connector import get
from API.pass_secure import hash_pass


class UserManager(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.selected_user_id = None
        self.selected_username = None

        self.status = Label(text="User Manager loaded", size_hint_y=None, height=40)
        self.add_widget(self.status)

        self.body = BoxLayout(orientation="horizontal")
        self.add_widget(self.body)

        self.user_panel = BoxLayout(orientation="vertical", size_hint_x=0.4)
        self.edit_panel = BoxLayout(orientation="vertical", size_hint_x=0.6)

        self.body.add_widget(self.user_panel)
        self.body.add_widget(self.edit_panel)

        self.build_user_panel()
        self.build_edit_panel()
        self.load_users()

    def db_execute(self, query, params=None, fetch=False, commit=False):
        conn = None
        cursor = None

        try:
            conn = get()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())

            result = cursor.fetchall() if fetch else None

            if commit:
                conn.commit()

            return {"success": True, "result": result}

        except mysql.connector.Error as err:
            if conn:
                conn.rollback()
            return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def build_user_panel(self):
        self.user_panel.add_widget(Label(text="Users", size_hint_y=None, height=40))

        self.user_list = GridLayout(cols=1, size_hint_y=None)
        self.user_list.bind(minimum_height=self.user_list.setter("height"))

        scroll = ScrollView()
        scroll.add_widget(self.user_list)
        self.user_panel.add_widget(scroll)

        refresh_button = Button(text="Refresh", size_hint_y=None, height=45)
        refresh_button.bind(on_press=lambda _: self.load_users())
        self.user_panel.add_widget(refresh_button)

    def build_edit_panel(self):
        form = GridLayout(cols=2, size_hint_y=None, height=360)

        form.add_widget(Label(text="Username"))
        self.username_input = TextInput(multiline=False)
        form.add_widget(self.username_input)

        form.add_widget(Label(text="First Name"))
        self.firstname_input = TextInput(multiline=False)
        form.add_widget(self.firstname_input)

        form.add_widget(Label(text="Login Password"))
        self.password_input = TextInput(password=True, multiline=False)
        form.add_widget(self.password_input)

        form.add_widget(Label(text="Role"))
        self.role_input = Spinner(
            text="USER",
            values=("USER", "ADMIN", "SUPERADMIN")
        )
        form.add_widget(self.role_input)

        form.add_widget(Label(text="Admin Password"))
        self.admin_password_input = TextInput(password=True, multiline=False)
        form.add_widget(self.admin_password_input)

        form.add_widget(Label(text="Superadmin Password"))
        self.superadmin_password_input = TextInput(password=True, multiline=False)
        form.add_widget(self.superadmin_password_input)

        self.edit_panel.add_widget(form)

        buttons = GridLayout(cols=3, size_hint_y=None, height=90)

        create_button = Button(text="Create User")
        create_button.bind(on_press=lambda _: self.create_user())

        update_role_button = Button(text="Update Role")
        update_role_button.bind(on_press=lambda _: self.update_role())

        reset_password_button = Button(text="Reset Login Password")
        reset_password_button.bind(on_press=lambda _: self.reset_login_password())

        set_admin_button = Button(text="Set Admin Password")
        set_admin_button.bind(on_press=lambda _: self.set_admin_password())

        set_superadmin_button = Button(text="Set Superadmin Password")
        set_superadmin_button.bind(on_press=lambda _: self.set_superadmin_password())

        clear_button = Button(text="Clear Form")
        clear_button.bind(on_press=lambda _: self.clear_form())

        buttons.add_widget(create_button)
        buttons.add_widget(update_role_button)
        buttons.add_widget(reset_password_button)
        buttons.add_widget(set_admin_button)
        buttons.add_widget(set_superadmin_button)
        buttons.add_widget(clear_button)

        self.edit_panel.add_widget(buttons)

        state_buttons = GridLayout(cols=2, size_hint_y=None, height=45)

        enable_button = Button(text="Enable User")
        enable_button.bind(on_press=lambda _: self.set_enabled(True))

        disable_button = Button(text="Disable User")
        disable_button.bind(on_press=lambda _: self.set_enabled(False))

        state_buttons.add_widget(enable_button)
        state_buttons.add_widget(disable_button)

        self.edit_panel.add_widget(state_buttons)

    def load_users(self):
        self.user_list.clear_widgets()

        result = self.db_execute(
            """
            SELECT id, username, firstname, role, enabled
            FROM users
            ORDER BY username ASC
            """,
            fetch=True
        )

        if not result.get("success"):
            self.status.text = str(result)
            return

        for user in result["result"]:
            text = (
                f"{user['id']} | {user['username']} | "
                f"{user['role']} | enabled={bool(user['enabled'])}"
            )

            button = Button(text=text, size_hint_y=None, height=40)
            button.bind(
                on_press=lambda _, selected=user: self.select_user(selected)
            )

            self.user_list.add_widget(button)

    def select_user(self, user):
        self.selected_user_id = user["id"]
        self.selected_username = user["username"]

        self.username_input.text = user["username"]
        self.firstname_input.text = user["firstname"]
        self.role_input.text = user["role"]

        self.password_input.text = ""
        self.admin_password_input.text = ""
        self.superadmin_password_input.text = ""

        self.status.text = f"Selected user: {user['username']}"

    def create_user(self):
        username = self.username_input.text.strip()
        firstname = self.firstname_input.text.strip()
        password = self.password_input.text
        role = self.role_input.text

        if not username or not firstname or not password:
            self.status.text = "Username, first name, and login password are required"
            return

        result = self.db_execute(
            """
            INSERT INTO users (
                username,
                firstname,
                password_hash,
                role,
                enabled
            )
            VALUES (%s, %s, %s, %s, TRUE)
            """,
            (
                username,
                firstname,
                hash_pass(password),
                role
            ),
            commit=True
        )

        self.status.text = str(result)
        self.load_users()

    def update_role(self):
        if self.selected_user_id is None:
            self.status.text = "Select a user first"
            return

        result = self.db_execute(
            """
            UPDATE users
            SET role = %s
            WHERE id = %s
            """,
            (
                self.role_input.text,
                self.selected_user_id
            ),
            commit=True
        )

        self.status.text = str(result)
        self.load_users()

    def reset_login_password(self):
        if self.selected_user_id is None:
            self.status.text = "Select a user first"
            return

        password = self.password_input.text

        if not password:
            self.status.text = "Enter a new login password"
            return

        result = self.db_execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
            """,
            (
                hash_pass(password),
                self.selected_user_id
            ),
            commit=True
        )

        self.status.text = str(result)

    def set_admin_password(self):
        if self.selected_user_id is None:
            self.status.text = "Select a user first"
            return

        password = self.admin_password_input.text

        if not password:
            self.status.text = "Enter an admin password"
            return

        result = self.db_execute(
            """
            UPDATE admin_credentials
            SET admin_password_hash = %s
            WHERE user_id = %s
            """,
            (
                hash_pass(password),
                self.selected_user_id
            ),
            commit=True
        )

        self.status.text = str(result)

    def set_superadmin_password(self):
        if self.selected_user_id is None:
            self.status.text = "Select a user first"
            return

        password = self.superadmin_password_input.text

        if not password:
            self.status.text = "Enter a superadmin password"
            return

        result = self.db_execute(
            """
            UPDATE superadmin_credentials
            SET superadmin_password_hash = %s
            WHERE user_id = %s
            """,
            (
                hash_pass(password),
                self.selected_user_id
            ),
            commit=True
        )

        self.status.text = str(result)

    def set_enabled(self, enabled: bool):
        if self.selected_user_id is None:
            self.status.text = "Select a user first"
            return

        result = self.db_execute(
            """
            UPDATE users
            SET enabled = %s
            WHERE id = %s
            """,
            (
                enabled,
                self.selected_user_id
            ),
            commit=True
        )

        self.status.text = str(result)
        self.load_users()

    def clear_form(self):
        self.selected_user_id = None
        self.selected_username = None

        self.username_input.text = ""
        self.firstname_input.text = ""
        self.password_input.text = ""
        self.role_input.text = "USER"
        self.admin_password_input.text = ""
        self.superadmin_password_input.text = ""

        self.status.text = "Form cleared"


class UserManagerApp(App):
    def build(self):
        return UserManager()


if __name__ == "__main__":
    UserManagerApp().run()