class Message:
    def __init__(self, from_id, text, author_id, chat_name=None, is_owner=None, photos=None):
        self.from_id = from_id
        self.text = text
        self.author_id = author_id
        self.chat_name = chat_name
        self.is_owner = is_owner
        self.photos = photos

    def is_chat_command(self):
        return len(self.text) > 0 and self.text[0] == "!"

    def get_chat_id(self):
        return str(self.from_id[0]) + self.from_id[1]

    def get_author_id(self):
        return str(self.author_id) + self.from_id[1]

    def get_chat_command(self):
        if not self.is_chat_command():
            return None
        return self.text[1:].strip()
