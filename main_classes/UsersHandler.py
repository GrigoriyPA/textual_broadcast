import sqlite3
from main_classes.Graph import Graph
from client_classes.VkClient import VkClient
from client_classes.TelegramClient import TelegramClient
from client_classes.DiscordClient import DiscordClient


class UsersHandler:
    def __init__(self, graph_storage_name, users_information_db_name, error_log_name=None):
        self.error_log_name = error_log_name
        self.graph = Graph(graph_storage_name)
        self.select_chat = {"chat_name": None, "chat_id": (None, None)}

        self.vk_client = VkClient(self.compute_message)
        self.discord_client = DiscordClient(self.compute_message)
        self.telegram_client = TelegramClient(self.compute_message)

        self.users_information_db_name = users_information_db_name
        conn = sqlite3.connect(users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, is_admin INT);")
        conn.commit()

    def __add_user(self, id):
        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id='" + id + "';")
        if cursor.fetchone() is None:
            entry = (id, 0)
            cursor.execute("INSERT INTO users VALUES(?, ?);", entry)
            conn.commit()

    def __is_admin(self, msg):
        if msg.is_owner:
            return True

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id='" + msg.get_author_id() + str(msg.from_id[0]) + "';")
        return cursor.fetchone()[2]

    def __add_error_to_log(self, text):
        if self.error_log_name is not None:
            error_log = open(self.error_log_name, "a")
            error_log.write(text + "\n\n")
            error_log.close()

    def __send(self, id, text, to_chat=True, photo=[]):
        try:
            if id[1] == "VK":
                self.vk_client.send_msg(id[0], text, photo, to_chat)
            elif id[1] == "DS":
                self.discord_client.send_msg(id[0], text, photo)
            elif id[1] == "TG":
                self.telegram_client.send_msg(id[0], text, photo)
            else:
                self.__add_error_to_log("Error: Unknown system to send message.")
        except Exception as error:
            self.__add_error_to_log("Error: Unknown error while sending the message.\nDescription:\n" + str(error))

    def __compute_command_select(self, msg):
        if not self.__is_admin(msg):
            return self.__send(msg.from_id, "Error: You must be an administrator to use this command.")

        self.orient = False
        self.select_chat["chat_id"] = msg.from_id
        self.select_chat["chat_name"] = msg.chat_name
        self.__send(msg.from_id, "Chat is selected.")

    def __compute_command_connect(self, msg):
        if not self.__is_admin(msg):
            return self.__send(msg.from_id, "Error: You must be an administrator to use this command.")

        select_id = self.select_chat["chat_id"]
        if select_id == (None, None):
            self.__send(msg.from_id, "Error: No selected chat.")
        elif select_id == msg.from_id:
            self.__send(msg.from_id, "Error: Attempting to connect a chat with itself.")
        elif select_id in self.graph.adjacency_list[msg.from_id]:
            self.__send(msg.from_id, "Error: Chats already connected.")
        else:
            self.graph.add_edge(select_id, msg.from_id)
            self.__send(msg.from_id, select_id[1] + " chat with name " + self.select_chat["chat_name"] + " is connected.")
            self.__send(select_id, msg.from_id[1] + " chat with name " + msg.chat_name + " is connected.")

    def __compute_command_disconnect(self, msg):
        if not self.__is_admin(msg):
            return self.__send(msg.from_id, "Error: You must be an administrator to use this command.")

        select_id = self.select_chat["chat_id"]
        if select_id == (None, None):
            self.__send(msg.from_id, "Error: No selected chat.")
        elif not (select_id in self.graph.adjacency_list[msg.from_id]):
            self.__send(msg.from_id, "Error: Chats are not connected.")
        else:
            self.graph.erase_edge(msg.from_id, select_id)
            self.__send(msg.from_id, select_id[1] + " chat with name " + self.select_chat["chat_name"] + " is disconnected.")
            self.__send(select_id, msg.from_id[1] + " chat with name " + msg.chat_name + " is disconnected.")

    def __compute_command_get_id(self, msg):
        self.__send(msg.from_id, "User id: " + msg.get_author_id(), to_chat=msg.chat_name is not None)

    def __compute_command_set_admin(self, msg):
        if not msg.is_owner:
            return self.__send(msg.from_id, "Error: You must be an owner to use this command.")

        command = msg.get_chat_command().split()
        if len(command) == 2:
            return self.__send(msg.from_id, "Error: An user id is required.")
        user_id = " ".join(command[2:])
        self.__add_user(user_id + str(msg.from_id[0]))

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id='" + user_id + str(msg.from_id[0]) + "';")
        if cursor.fetchone()[2]:
            return self.__send(msg.from_id, "Error: The account with id '" + user_id + "' already has administrator rights.")

        cursor.execute("UPDATE users SET is_admin=1 WHERE id='" + user_id + str(msg.from_id[0]) + "';")
        conn.commit()
        self.__send(msg.from_id, "The account with id '" + user_id + "' has been granted administrative rights.")

    def __compute_command_delete_admin(self, msg):
        if not msg.is_owner:
            return self.__send(msg.from_id, "Error: You must be an owner to use this command.")

        command = msg.get_chat_command().split()
        if len(command) == 2:
            return self.__send(msg.from_id, "Error: An user id is required.")
        user_id = " ".join(command[2:])
        self.__add_user(user_id + str(msg.from_id[0]))

        conn = sqlite3.connect(self.users_information_db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id='" + user_id + str(msg.from_id[0]) + "';")
        if not cursor.fetchone()[2]:
            return self.__send(msg.from_id, "Error: The account with id '" + user_id + "' does not have administrative rights.")

        cursor.execute("UPDATE users SET is_admin=0 WHERE id='" + user_id + str(msg.from_id[0]) + "';")
        conn.commit()
        self.__send(msg.from_id, "The account with id '" + user_id + "' no longer has administrative rights.")

    def __compute_chat_command(self, msg):
        command = msg.get_chat_command().split()
        if len(command) >= 1 and command[0].lower() == "select":
            self.__compute_command_select(msg)
        elif len(command) >= 1 and command[0].lower() == "connect":
            self.__compute_command_connect(msg)
        elif len(command) >= 1 and command[0].lower() == "disconnect":
            self.__compute_command_disconnect(msg)
        elif len(command) >= 2 and command[0].lower() == "set" and command[1].lower() == "admin":
            self.__compute_command_set_admin(msg)
        elif len(command) >= 2 and command[0].lower() == "delete" and command[1].lower() == "admin":
            self.__compute_command_delete_admin(msg)
        elif len(command) >= 2 and command[0].lower() == "get" and command[1].lower() == "id":
            self.__compute_command_get_id(msg)
        else:
            self.__send(msg.from_id, "Error: Unknown instruction.")

    def __compute_user_command(self, msg):
        command = msg.text.split()
        if len(command) >= 2 and command[0].lower() == "get" and command[1].lower() == "id":
            self.__compute_command_get_id(msg)
        else:
            self.__send(msg.from_id, "Error: Unknown instruction.", to_chat=False)

    def run(self, vk_token=None, vk_group_id=None, telegram_token=None, discord_token=None):
        if vk_token is not None and vk_group_id is not None:
            self.vk_client.run(vk_token, vk_group_id)
        if telegram_token is not None:
            self.telegram_client.run(telegram_token)
        if discord_token is not None:
            self.discord_client.run(discord_token)

    def compute_message(self, msg):
        if msg.chat_name is None:
            return self.__compute_user_command(msg)

        self.__add_user(msg.get_author_id() + str(msg.from_id[0]))
        self.graph.add_vertex(msg.from_id)
        if msg.is_chat_command():
            return self.__compute_chat_command(msg)

        for send_id in self.graph.get_reachable_vertices(msg.from_id, msg.text):
            self.__send(send_id, msg.text, photo=msg.photos)
