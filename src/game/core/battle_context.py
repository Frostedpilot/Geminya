class BattleContext:
    def __init__(self, team_one=None, team_two=None, round_number=1):
        self.team_one = team_one if team_one is not None else []
        self.team_two = team_two if team_two is not None else []
        self.round_number = round_number
