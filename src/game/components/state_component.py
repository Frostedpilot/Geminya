class StateComponent:
    def __init__(self, current_hp, max_hp, action_gauge=0, is_alive=True):
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.action_gauge = action_gauge
        self.is_alive = is_alive
