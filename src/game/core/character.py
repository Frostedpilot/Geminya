class Character:
    def __init__(self, character_id, components=None):
        self.character_id = character_id
        self.components = components if components is not None else {}
        self.team = None
        self.position = None
        self.name = None
