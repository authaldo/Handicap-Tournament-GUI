import functools
import math

from typing import List
from enum import IntEnum


class GameMode(IntEnum):
    BEST_OF_TWO = 2
    BEST_OF_THREE = 3


class Player(dict):
    """ Representation of a player as provided within the input json file. """
    name: str
    nickname: str
    ttr: int
    handicap: int

    def __init__(self, name: str, ttr: int, handicap: int, nickname=None):
        dict.__init__(self, name=name, ttr=ttr, handicap=handicap, nickname=nickname)
        self.name = name
        self.ttr = ttr
        self.handicap = handicap
        self.nickname = nickname

@functools.total_ordering
class TournamentPlayer(Player):
    """ Representation of a player extended with the tournament information (e.g. previous opponents, results, ...). """
    def __init__(self, identifier: int, name: str, display_name: str, ttr: int, handicap: int = 0, nickname: str = None):
        super().__init__(name, ttr, handicap, nickname)
        self.display_name = display_name
        self.id = identifier
        self.hadByeInRound = -1
        self.wins = set()
        self.losses = set()

        # accumulation of the number of wins across each opponent this player has won against
        self.buchholz = 0

    def has_played_against(self, other: int):
        return other in self.wins or other in self.losses

    def has_won_against(self, other: int):
        return other in self.wins

    def had_bye(self):
        return self.hadByeInRound > 0

    def is_bye(self):
        return False

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __lt__(self, other):
        if len(self.wins) > len(other.wins):
            return True
        if len(self.wins) < len(other.wins):
            return False
        if self.buchholz > other.buchholz:
            return True
        if self.buchholz < other.buchholz:
            return False
        if self.has_played_against(other.id):
            if self.has_won_against(other.id):
                return True
            return False
        if self.ttr < other.ttr:
            return True
        if self.ttr > other.ttr:
            return False
        if self.__eq__(other):
            return False
        return False

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

class PlayerBye(TournamentPlayer):
    """ Added to the list of players in case there is an uneven number of players. """

    def __init__(self, id):
        super().__init__(id, "Freilos", "Freilos", -999999, 0)

    def is_bye(self):
        return True


class Score:
    @staticmethod
    def from_str(val: str) -> [float, None]:
        if not ':' in val:
            return None

        split = val.split(':')

        if len(split) != 2:
            return None

        # try catch since parsing the split could go wrong
        try:
            points_1 = int(split[0])
            points_2 = int(split[1])

            # case 1: 11:X or X:11
            for p1, p2, sign in [(points_1, points_2, 1.0), (points_2, points_1, -1.0)]:
                if p1 == 11 and p2 <= 9:
                    return sign * min(p1, p2)

            # case 2: set has been won in overtime
            for p1, p2, sign in [(points_1, points_2, 1.0), (points_2, points_1, -1.0)]:
                if p1 >= 10 and p2 >= 10 and p1 - p2 == 2:
                    return sign * min(p1, p2)

            return None
        except:
            return None

    @staticmethod
    def to_str(val: float) -> str:
        # edge case: -0 (direct comparison to -0.0 is not possible since -0.0 == 0 == 0.0)
        sign = math.copysign(1, val)
        if val == 0.0 and sign < 0:
            return "0 : 11"

        abs_val = abs(int(val))

        if 0 <= abs_val <= 9:
            points_1 = 11
            points_2 = abs_val
        else:
            points_1 = abs_val + 2
            points_2 = abs_val

        if val < 0:
            points_1, points_2 = points_2, points_1

        return f'{points_1} : {points_2}'


class Match:
    def __init__(self, game_mode: GameMode, first_player: TournamentPlayer, second_player: TournamentPlayer,
                 start_offset: int = 0):
        self.game_mode = game_mode
        self.first_player_id: int = first_player.id
        self.first_player_name: str = first_player.name
        self.first_player_display_name: str = first_player.display_name
        self.second_player_id: int = second_player.id
        self.second_player_name: str = second_player.name
        self.second_player_display_name: str = second_player.display_name

        # stored as float since we need the negative zero as well...
        self.set_results: List[float or None] = [None] * (2*int(self.game_mode) - 1)
        self.start_offset: int = start_offset # necessary for tournaments with handicaps

    def sets_won(self) -> int:
        sets_won = 0
        for res in self.set_results:
            if res is None:
                continue

            # special comparison needed for 11:0 and 0:11
            sign = math.copysign(1, res)
            if sign > 0:
                sets_won += 1

        return sets_won

    def sets_lost(self) -> int:
        sets_lost = 0
        for res in self.set_results:
            if res is None:
                continue

            # special comparison needed for 11:0 and 0:11
            sign = math.copysign(1, res)
            if sign < 0:
                sets_lost += 1

        return sets_lost

    def is_finished(self) -> bool:
        sets_won = 0
        sets_lost = 0

        for res in self.set_results:
            if res is None:
                continue
            elif res > 0:
                sets_won += 1

        sets_won = self.sets_won()
        sets_lost =  self.sets_lost()

        if self.game_mode == GameMode.BEST_OF_TWO:
            required_sets = 2
        else:
            required_sets = 3

        return (sets_won == required_sets) or (sets_lost == required_sets)

    def update_set_result(self, index: int, result: int or None):
        self.set_results[index] = result

# utility functions
def initialize_field_of_participants(players: List[Player], add_bye: bool=True, use_nicknames=True):
    def levenshtein_distance(a, b):
        a = a.lower()
        b = b.lower()

        n = len(a)
        m = len(b)

        # without numpy since buildozer had some problems with it...
        lev_matrix = []
        for i in range(0, n+1):
            lev_matrix.append([0] * (m+1))

        for i in range(0, n + 1):
            lev_matrix[i][0] = i

        for i in range(0, m + 1):
            lev_matrix[0][i] = i

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                insertion = lev_matrix[i - 1][j] + 1
                deletion = lev_matrix[i][j - 1] + 1
                substitution = lev_matrix[i - 1][j - 1] + (1 if a[i - 1] != b[j - 1] else 0)
                lev_matrix[i][j] = min(insertion, deletion, substitution)

        return lev_matrix[n][m]

    def get_display_name(player, level, use_nicknames):
        # levels define length of name
        # 0 -> only prename
        # 1 -> prename + first letter of name
        # 2 -> full name

        # assumes that nicknames are usually distinguishable
        if use_nicknames and player.nickname is not None:
            return player.nickname

        split = player.name.split(' ')

        if level == 0:
            return split[0]
        elif level == 1:
            if len(split) == 2:
                return f"{split[0]} {split[-1][0]}."

        return player.name

    def check_for_colliding_display_names(players, levels, use_nicknames):
        colliding_display_names = set()

        for i, p1 in enumerate(players):
            for k, p2 in enumerate(players):
                if i == k:
                    continue

                p1_name = get_display_name(p1, levels[i], use_nicknames=use_nicknames)
                p2_name = get_display_name(p2, levels[k], use_nicknames=use_nicknames)

                # Levenshtein distance is intended for cases like 'Stephan' vs. 'Stefan'
                if p1_name == p2_name or levenshtein_distance(p1_name, p2_name) <= 2:
                    colliding_display_names.add(i)
                    colliding_display_names.add(k)

        return colliding_display_names

    # shorten names for a cleaner visualization
    name_levels = [0] * len(players)

    # three levels of name length:
    # 0 -> only prename
    # 1 -> prename + first letter of name
    # 2 -> full name
    for _ in range(3):
        colliding_names = check_for_colliding_display_names(players, name_levels, use_nicknames)

        if len(colliding_names) > 0:
            for index in colliding_names:
                name_levels[index] += 1
        else:
            break

    display_names = [get_display_name(player, level, use_nicknames) for player, level in zip(players, name_levels)]

    # create field of participants
    tournament_players = []
    for i, p in enumerate(players):
        tournament_players.append(TournamentPlayer(i, **p, display_name=display_names[i]))

    if add_bye and len(tournament_players) % 2 != 0:
        tournament_players.append(PlayerBye(len(tournament_players)))

    return tournament_players
