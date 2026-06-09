README


This file is intended to walk the server owner through operating the DogHammer Service Gateway software.

Currently, the software requires the server host to have installed within their environment: Python 3, Kivy, bcrypt, passlib, fastapo, ivocorn, mysql-connector-python, python-multipart, requests. For window systems, pylance is also required. For Linux, pillow, pygments, and docutils are necessary.

Once the necessary packages are installed in the environment, define the environment variables listed in the relevant text file, within the devkit folder. It is recommended that you enabled these via your operating system rather than a virtual environment.

Once environment variables are defined, build the SQL database. This is done with "server SQL.sql" on windows, and "linux sql.sql" on Linux, using MySQL Workbench or MariaDB respectively. These are found within the SQL folder under the Project file.

Once the database is created, run the user creation tool via your terminal, using the command python -m Regions.user_manager_app. This must be done from the Python directory using venv.

create as many users as you like.

When giving users access to your server, you need to distribute the client.exe file found in the devkit folder, found within the Python folder.

Admin powers require escalation from base user permissions. Superadmin powers require escalation from Admin powers. Currently the definition of the passwords for this process requires running pass_secure.py via the terminal, then manual entry into the SQL database. If you would like an easy creation process for a superadmin account, there is a manage_server_data.sql file that you can run, along with credentials in the admin auth pass.sql file. A simpler method is in development.