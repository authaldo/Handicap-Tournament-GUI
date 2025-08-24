from dataclasses import dataclass
from model.data_classes import GameMode

@dataclass
class Settings:
    match_mode = GameMode.BEST_OF_THREE
    handicap_enabled = True
    players = []
    storage_path = None