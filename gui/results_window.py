import functools
import math
import glob
import os
import string

from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

# only first five players are awared with points
CONSIDERED_RANKS = 5


@dataclass
class PlayerStatistics:
    sets_won: int = 0
    sets_lost: int = 0

    points_won: int = 0
    points_lost: int = 0

    # accumulated point difference within sets (ignoring bye)
    acc_point_diff_won: int = 0
    acc_point_diff_lost: int = 0

    has_played_bye: bool = False

@dataclass
@functools.total_ordering
class SeasonRanking:
    total_points: int = 0

    placement_histogram: List[int] = field(default_factory=list)

    def __lt__(self, other):
        return self.total_points < other.total_points

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.total_points == other.total_points


class ResultsWindow(Screen):
    grid_layout = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ResultsWindow, self).__init__(**kwargs)
        self._games = None
        self._label_size = 35
        self._spacing = 5
        self._row_height = 70
        self._tournament = None

    def on_pre_enter(self):
        self._tournament = self.parent.ids['tournament_window'].get_tournament()
        self._storage_path = self.parent.ids['tournament_window'].get_tournament_storage_path()
        self.update_visualization()
        pass

    def _extract_statistics(self):
        statistics = {}

        # create a statistics entry for each player
        bye_id = None
        for p in self._tournament.get_players():
            if p.is_bye():
                bye_id = p.id

            statistics[p.id] = PlayerStatistics()

        # iterate over all matches and extract statistics
        for round in self._tournament.get_all_matches():
            for match in round:
                p1 = match.first_player_id
                p2 = match.second_player_id

                for res in match.set_results:
                    if res is None:
                        break

                    sign = math.copysign(1, res) # needed for 11:0 and 0:11 edge case

                    abs_res = abs(res)

                    set_difference = int(11 - abs_res if abs_res <= 9 else 2)
                    winner_points = int(max(11, abs_res + 2))
                    loser_points = int(abs_res)

                    # the average set difference is intended to give an impression whether the handicaps
                    # are fairly distributed, hence, it ignores any 'bye' matches
                    if match.second_player_id == bye_id:
                        statistics[p1].has_played_bye = True
                        set_difference = 0

                    if sign > 0:
                        statistics[p1].sets_won += 1
                        statistics[p1].points_won += winner_points
                        statistics[p1].points_lost += loser_points
                        statistics[p1].acc_point_diff_won += set_difference

                        statistics[p2].sets_lost += 1
                        statistics[p2].points_won += loser_points
                        statistics[p2].points_lost += winner_points
                        statistics[p2].acc_point_diff_lost += set_difference
                    else:
                        statistics[p1].sets_lost += 1
                        statistics[p1].points_won += loser_points
                        statistics[p1].points_lost += winner_points
                        statistics[p1].acc_point_diff_lost += set_difference

                        statistics[p2].sets_won += 1
                        statistics[p2].points_won += winner_points
                        statistics[p2].points_lost += loser_points
                        statistics[p2].acc_point_diff_won += set_difference

        return statistics

    def _extract_season_ranking(self):
        # determine valid date range
        cur_date = datetime.today()

        threshold_date = datetime.strptime(f"{cur_date.year}-09-01", '%Y-%m-%d')

        if cur_date < threshold_date:
            start_date = datetime.strptime(f"{cur_date.year - 1}-09-01", '%Y-%m-%d')
            end_date = datetime.strptime(f"{cur_date.year}-08-31", '%Y-%m-%d')
        else:
            start_date = datetime.strptime(f"{cur_date.year}-09-01", '%Y-%m-%d')
            end_date = datetime.strptime(f"{cur_date.year + 1}-08-31", '%Y-%m-%d')

        # extract ranking from the stored tournament history
        season_ranking = {}
        for file in glob.glob(self._storage_path + '/*.txt'):
            file_date = datetime.strptime(os.path.basename(file).rstrip(".txt"), '%Y-%m-%d')

            if file_date < start_date or file_date > end_date:
                continue

            with open(file, 'r') as tournament:
                ranking_found = False
                rank = 1
                for line in tournament:
                    # skip all lines before the ranking
                    if not ranking_found and not line.startswith('Ranking'):
                        continue

                    ranking_found = True

                    if line[0].isdigit():
                        # extract name (a bit more complicated since the text files have initially only been intended
                        # as backup with a focus on human readability)
                        player_name = line.split('.')[-1].lstrip().split(':')[0].rstrip(string.digits).rstrip()
                        if player_name not in season_ranking:
                            season_ranking[player_name] = SeasonRanking()
                            season_ranking[player_name].placement_histogram = [0] * CONSIDERED_RANKS

                        if rank <= 5:
                            season_ranking[player_name].total_points += CONSIDERED_RANKS + 1 - rank
                            season_ranking[player_name].placement_histogram[rank - 1] += 1

                        rank += 1

        # sort the dict based on total points
        sorted_dict = OrderedDict(sorted(season_ranking.items(), key=lambda elem: elem[1].total_points, reverse=True))

        return sorted_dict


    def update_visualization(self):
        # constants
        spacing = 0
        row_height = 40
        text_size = 30
        heading_text_size = 35

        ranking = self._tournament.get_ranking()

        # extract more detailed information not included in the ranking
        player_statistics = self._extract_statistics()

        self.box_layout.clear_widgets()
        self.box_layout.add_widget(Label(text=f'[b][size={heading_text_size}]Heutiges Turnier[/size][/b]', markup=True,
                                         halign='left', valign='bottom', size_hint=(1, None), height=row_height))
        self.box_layout.add_widget(Label(text=f'[b][size={heading_text_size}][/size][/b]', markup=True,
                                         halign='left', valign='bottom', size_hint=(1, None), height=row_height))
        
        
        layout = GridLayout(cols=8, rows=len(ranking) + 1, spacing=spacing, size_hint_y=None, size_hint_x=1,
                                      height=(row_height + spacing) * (len(ranking) + 1))

        layout.add_widget(
            Label(text=f'[b][size={text_size}][/size][/b]', markup=True, halign='left', valign='bottom',
                  size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]Spieler[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]Bilanz[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]Sätze[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]Bälle[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]BHZ[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]mittl. Diff. +[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]mittl. Diff. -[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))

        bye_offset = self._tournament.num_sets_for_win()

        for i, p in enumerate(ranking, 1):
            statistics = player_statistics[p.id]

            avg_diff_won_str = "-"
            avg_diff_lost_str = "-"

            sets_won = statistics.sets_won - int(statistics.has_played_bye) * bye_offset
            sets_lost = statistics.sets_lost - int(statistics.has_played_bye) * bye_offset

            if sets_won > 0:
                sets_won = statistics.sets_won - int(statistics.has_played_bye) * bye_offset
                avg_diff_won = statistics.acc_point_diff_won / sets_won
                avg_diff_won_str = f"{avg_diff_won:.1f}"

            if sets_lost > 0:
                avg_diff_lost = statistics.acc_point_diff_lost / sets_lost
                avg_diff_lost_str = f"{avg_diff_lost:.1f}"


            layout.add_widget(
                Label(text=f'[size={text_size}]{i}[/size]', markup=True, halign='left', valign='bottom',
                      size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{p.display_name}[/size]', markup=True, halign='left',
                                    valign='bottom', size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{len(p.wins)} : {len(p.losses)}[/size]', markup=True,
                                    halign='left', valign='bottom', size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{statistics.sets_won} : {statistics.sets_lost}[/size]',
                                    markup=True, halign='left', valign='bottom', size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{statistics.points_won} : {statistics.points_lost}[/size]',
                                    markup=True, halign='left', valign='bottom', size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{p.buchholz}[/size]',  markup=True, halign='left',
                                    valign='bottom', size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{avg_diff_won_str}[/size]', markup=True, halign='left',
                                    valign='bottom', size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{avg_diff_lost_str}[/size]', markup=True, halign='left',
                                    valign='bottom', size_hint=(1, None), height=row_height))

        self.box_layout.add_widget(layout)

        # accumulated ranking over all tournaments in the current season (september - august of next year)
        # --> points are assigned for the first CONSIDERED_RANKS places (points = CONSIDERED_RANKS + 1 - place)
        season_ranking = self._extract_season_ranking()

        self.box_layout.add_widget(Label(text=f'[b][size={heading_text_size}][/size][/b]', markup=True,
                                         halign='left', valign='bottom', size_hint=(1, None), height=2*row_height))
        self.box_layout.add_widget(Label(text=f'[b][size={heading_text_size}]Saisonübersicht[/size][/b]', markup=True,
                                         halign='left', valign='bottom', size_hint=(1, None), height=row_height))
        self.box_layout.add_widget(Label(text=f'[b][size={heading_text_size}][/size][/b]', markup=True,
                                         halign='left', valign='bottom', size_hint=(1, None), height=row_height))

        season_layout = GridLayout(cols=8, rows=len(season_ranking) + 1, spacing=spacing, size_hint_y=None, size_hint_x=1,
                                   height=(row_height + spacing) * (len(ranking) + 1))

        season_layout.add_widget(
            Label(text=f'[b][size={text_size}][/size][/b]', markup=True, halign='left', valign='bottom',
                  size_hint=(1, None), height=row_height))
        season_layout.add_widget(Label(text=f'[b][size={text_size}]Spieler[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        season_layout.add_widget(Label(text=f'[b][size={text_size}]1. Platz[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        season_layout.add_widget(Label(text=f'[b][size={text_size}]2. Platz[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        season_layout.add_widget(Label(text=f'[b][size={text_size}]3. Platz[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        season_layout.add_widget(Label(text=f'[b][size={text_size}]4. Platz[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        season_layout.add_widget(Label(text=f'[b][size={text_size}]5. Platz[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        season_layout.add_widget(Label(text=f'[b][size={text_size}]Gesamtpunkte[/size][/b]', markup=True, halign='left',
                                       valign='bottom', size_hint=(1, None), height=row_height))

        for i, (name, season_stats) in enumerate(season_ranking.items(), 1):
            season_layout.add_widget(Label(text=f'[size={text_size}]{i}[/size]', markup=True, halign='left',
                                           valign='bottom', size_hint=(1, None), height=row_height))
            season_layout.add_widget(Label(text=f'[size={text_size}]{name}[/size]', markup=True, halign='left',
                                           valign='bottom', size_hint=(1, None), height=row_height))
            for r in range(5):
                season_layout.add_widget(Label(text=f'[size={text_size}]{season_stats.placement_histogram[r]}[/size]',
                                               markup=True, halign='left', valign='bottom', size_hint=(1, None),
                                               height=row_height))

            season_layout.add_widget(Label(text=f'[size={text_size}]{season_stats.total_points}[/size]',
                                           markup=True, halign='left', valign='bottom', size_hint=(1, None),
                                           height=row_height))

        self.box_layout.add_widget(season_layout)

        # spacer to ensure scroll view starts at the top
        self.box_layout.add_widget(Label(text=f'[b][size={heading_text_size}][/size][/b]', markup=True,
                                         halign='left', valign='bottom', size_hint=(1, 0.1), height=row_height))
