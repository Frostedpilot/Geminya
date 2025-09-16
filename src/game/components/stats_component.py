class StatsComponent:
    def __init__(self, base_stats):
        self.base_stats = base_stats
        self.modified_stats = base_stats.copy()

    def get_stat(self, stat_name):
        return self.base_stats.get(stat_name, 0)
