import math
import os

from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.properties import ObjectProperty

from model.swiss_system import Tournament
from model.data_classes import GameMode, Score

from datetime import datetime


class SetResultInput(TextInput):
    def __init__(self, parent, **kwargs):
        super(SetResultInput, self).__init__(multiline=False, write_tab=False, input_type='number', **kwargs)
        self.bind(on_text_validate=self.validate_text)
        self._parent = parent

    def insert_text(self, substring, from_undo=False):
        res = "".join([char for char in substring if char.isdigit() or char in ['-']])
        return super().insert_text(res, from_undo=from_undo)

    def on_focus(self, instance, value):
        if not value:  # defocused
            self.validate_text(instance)

    def validate_text(self, input):
        if len(input.text) == 0:
            input.text = ''
            return

        try:
            if ':' in input.text:
                val = Score.from_str(input.text)

                if val is None:
                    input.text = ''
                    return
            else:
                    val = float(input.text)

                    if val > 30 or val < -30:
                        input.text = ''
                        return
        except:
            input.text = ''
            return

        # replace with full string
        input.text = Score.to_str(val)

        self._parent.update()


class MatchWidget(BoxLayout):
    def __init__(self, parent, match):
        super(MatchWidget, self).__init__(orientation='vertical', padding=0, spacing=0)
        self._parent = parent
        self._match = match

        self._placeholder_path = 'resources/trophy_image_placeholder.png'
        self._trophy_path = 'resources/trophy_image.png'
        self._set_size = 60
        self._name_size = 30

        self._left_image_path = self._placeholder_path
        self._right_image_path = self._placeholder_path

        if self._match.start_offset >= 0:
            initial_set_str = f'{self._match.start_offset} : 0'
        else:
            initial_set_str = f'0 : {-1 * self._match.start_offset}'

        self._top_layout = GridLayout(rows=1, cols=3, size_hint=(1, 0.15))
        self._center_layout = GridLayout(rows=1, cols=3, size_hint=(1, 0.3))
        self._versus_label = Label(text=f'[b][size={self._name_size}]vs.[/size][/b]', markup=True,
                                 size_hint=(0.05, None), height=50)
        self._p1_label = Label(text=f'[size={self._name_size}][b]{match.first_player_display_name}[/b][/size]', markup=True,
                                 size_hint=(1.0, None), height=50)
        self._p2_label = Label(text=f'[size={self._name_size}][b]{match.second_player_display_name}[/b][/size]', markup=True,
                               size_hint=(1.0, None), height=50)
        self._left_image = Image(source='resources/trophy_image_placeholder.png')
        self._right_image = Image(source='resources/trophy_image_placeholder.png')
        self._set_label = Label(text=f'[size={self._set_size}]' + initial_set_str + '[/size]', markup=True, size_hint=(1, None),
                                 height=70, halign='center', valign='top')
        self._top_layout.add_widget(self._p1_label)
        self._top_layout.add_widget(self._versus_label)
        self._top_layout.add_widget(self._p2_label)
        self._center_layout.add_widget(self._left_image)
        self._center_layout.add_widget(self._set_label)
        self._center_layout.add_widget(self._right_image)

        self._top_spacer = Label(text='', size_hint=(1, 0.03))
        self._spacer = Label(text='', size_hint=(1, 0.03))
        self._bottom_spacer = Label(text='', size_hint=(1, 0.1))
        self._left_spacer = Label(text='', size_hint=(0.05, 0.05), width=5)
        self._right_spacer = Label(text='', size_hint=(0.05, 0.05), width=5)
        self._box_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.12), height=50)
        self._text_inputs = []

        num_sets = 2 if self._match.game_mode == GameMode.BEST_OF_TWO else 3
        num_inputs = 2 * num_sets - 1

        self._box_layout.add_widget(self._left_spacer)

        for i in range(num_inputs):
            input = SetResultInput(self, font_size=25, halign='center')

            # handles 'bye' matches were the results is immediately known
            if self._match.set_results[i] is not None:
                input.text = Score.to_str(self._match.set_results[i])

            if i == 0:
                input.disabled = False
            else:
                input.disabled = True

            self._text_inputs.append(input)
            self._box_layout.add_widget(input)
        self._box_layout.add_widget(self._right_spacer)

        # add all to the layout
        self.add_widget(self._top_spacer)
        self.add_widget(self._top_layout)
        self.add_widget(self._center_layout)
        self.add_widget(self._bottom_spacer)
        self.add_widget(self._box_layout)
        self.add_widget(self._spacer)

        if self._match.sets_won() > 0:
            self.update()

            for elem in self._text_inputs:
                elem.disabled = 'True'

    def is_match_finished(self):
        return self._match.is_finished()

    def update(self):
        # update match instance
        was_finished = self._match.is_finished()

        for i in range(len(self._text_inputs)):
            self._match.update_set_result(i, Score.from_str(self._text_inputs[i].text))

        self._left_image_path = self._placeholder_path
        self._right_image_path = self._placeholder_path

        if not self._match.is_finished():
            # unblock until first empty
            for i in range(len(self._text_inputs)):
                if self._text_inputs[i].text == "":
                    self._text_inputs[i].disabled = False
                    break
        else:
            # check who won
            if self._match.sets_won() > self._match.sets_lost():
                self._left_image_path = self._trophy_path
                self._right_image_path = self._placeholder_path
            else:
                self._right_image_path = self._trophy_path
                self._left_image_path = self._placeholder_path

        # reload image only if necessary
        for image, path in [(self._left_image, self._left_image_path), (self._right_image, self._right_image_path)]:
            if image.source != path:
                image.source = path
                image.reload()

        # update set score
        sets_won = self._match.sets_won()
        sets_lost = self._match.sets_lost()

        self._set_label.text = f'[size={self._set_size}]{sets_won} : {sets_lost}[/size]'

        self._parent.check_for_updates(match_finished=self.is_match_finished() or was_finished)


class TournamentWindow(Screen):
    round_label = ObjectProperty(None)
    match_scroll_view = ObjectProperty(None)
    ranking_scroll_view = ObjectProperty(None)
    next_round_button = ObjectProperty(None)
    game_overview_button = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(TournamentWindow, self).__init__(**kwargs)
        self._settings = None
        self._tournament = None
        self._grid_layout = None
        self._ranking_layout = None
        self._file_path = None
        self._player_string = None
        self._finished_matches_string = ""
        self._ranking_string = ""
        self._settings_string = ""
        self._max_player_name_len = 0

    def on_pre_enter(self):
        if self._settings is None:
            self._settings = self.parent.ids['settings_window'].get_settings()
            self._tournament = Tournament(self._settings.match_mode, self._settings.players,
                                          self._settings.handicap_enabled)
            self._tournament.generate_next_round()

            # file for storing the tournament data
            self._file_path = os.path.join(self._settings.storage_path,
                                           f"tournaments/{datetime.today().strftime('%Y-%m-%d')}.txt")

            self._max_player_name_len = max(len(p.name) for p in self._settings.players)

            self._player_string = "\nTeilnehmer:\n"
            for p in self._settings.players:
                self._player_string += f"{p.name.ljust(self._max_player_name_len)}, TTR: {p.ttr}, {p.handicap}\n"

            self._settings_string = f"Handicap: {self._settings.handicap_enabled}\n"

            self.update_visualization()


    def generate_next_round(self):
        # check if all games are finished
        for match in self._tournament.get_running_matches():
            if not match.is_finished():
                # shouldn't occur as button is only enabled once all games have been finished
                return

        self.game_overview_button.disabled = False

        # add finished matches to the pre-generated string for updating the text output
        self._finished_matches_string += f"\nRunde: {self._tournament.get_current_round()}\n"

        for m in self._tournament.get_running_matches():
            self._finished_matches_string += f" - {m.first_player_name.ljust(self._max_player_name_len)} vs. {m.second_player_name.ljust(self._max_player_name_len)} | {m.sets_won()}:{m.sets_lost()} | "
            for result in m.set_results:
                if result is None:
                    break

                self._finished_matches_string += f" {Score.to_str(result).replace(' ', '')}"

            self._finished_matches_string += '\n'

        self._tournament.generate_next_round()
        self.update_visualization()

        self.next_round_button.disabled = True

    def check_for_updates(self, match_finished):
        if match_finished:
            self.update_ranking_visualization()

        # check whether we can enable the button for the next round
        all_finished = True
        for widget in self._grid_layout.children:
            if not widget.is_match_finished():
                all_finished = False
                break

        # with n players we can play at most n-1 round if not pairing should occur twice...
        if self._tournament.get_current_round() < self._tournament.get_max_number_of_rounds():
            self.next_round_button.disabled = not all_finished
        else:
            self.next_round_button.disabled = True

        # store current state in text file
        open_matches_string = f"\nRunde: {self._tournament.get_current_round()}\n"

        for m in self._tournament.get_running_matches():
            open_matches_string += f" - {m.first_player_name.ljust(self._max_player_name_len)} vs. {m.second_player_name.ljust(self._max_player_name_len)} | {m.sets_won()}:{m.sets_lost()} | "
            for result in m.set_results:
                if result is None:
                    break

                open_matches_string += f" {Score.to_str(result).replace(' ', '')}"

            open_matches_string += '\n'

        with open(self._file_path, 'w') as file:
            file.write(self._settings_string)
            file.write(self._player_string)
            file.write(self._finished_matches_string)
            file.write(open_matches_string)
            file.write(self._ranking_string)

    def update_match_visualization(self):
        spacing = 1
        num_matches = len(self._tournament.get_running_matches())
        num_cols = 2
        num_rows = int(math.ceil(num_matches / num_cols))
        row_height = min(max(self.get_root_window().height * 0.8 / num_rows, 175), 250)

        self.match_scroll_view.clear_widgets()
        self._grid_layout = GridLayout(cols=num_cols, rows=num_rows, spacing=spacing, size_hint_y=None, size_hint_x=1,
                                       height=row_height * num_rows + num_rows * spacing)

        for m in self._tournament.get_running_matches():
            self._grid_layout.add_widget(MatchWidget(parent=self, match=m))

        self.match_scroll_view.add_widget(self._grid_layout)

    def update_ranking_visualization(self):
        # constants
        spacing = 0
        row_height = 40
        text_size = 30

        self._ranking_string = "\nRanking:\n"

        ranking = self._tournament.get_ranking()

        self.ranking_scroll_view.clear_widgets()
        layout = GridLayout(cols=3, rows=len(ranking) + 1, spacing=spacing, size_hint_y=None, size_hint_x=1,
                            height=(row_height + spacing) * (len(ranking) + 1))

        layout.add_widget(Label(text=f'[b][size={text_size}][/size][/b]', markup=True, halign='left', valign='bottom',
                                size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]Spieler[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))
        layout.add_widget(Label(text=f'[b][size={text_size}]Bilanz[/size][/b]', markup=True, halign='left',
                                valign='bottom', size_hint=(1, None), height=row_height))

        for i, p in enumerate(ranking, 1):
            layout.add_widget(Label(text=f'[size={text_size}]{i}[/size]', markup=True, halign='left', valign='bottom',
                                    size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{p.display_name}[/size]', markup=True, halign='left',
                                    valign='bottom', size_hint=(1, None), height=row_height))
            layout.add_widget(Label(text=f'[size={text_size}]{len(p.wins)} : {len(p.losses)}[/size]', markup=True,
                                    halign='left', valign='bottom', size_hint=(1, None), height=row_height))

            self._ranking_string += f"{i}. \t {p.name.ljust(self._max_player_name_len)} {len(p.wins)}:{len(p.losses)} (B: {p.buchholz})\n"

        self.ranking_scroll_view.add_widget(layout)

    def update_visualization(self):
        self.round_label.text = f'[size=25]Runde: {self._tournament.get_current_round()}[/size]'

        self.update_match_visualization()

        self.update_ranking_visualization()

    def get_played_games(self):
        return self._tournament.get_all_matches()
