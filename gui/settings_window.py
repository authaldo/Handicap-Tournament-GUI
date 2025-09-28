import math
import os
import json

from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.clock import Clock

from plyer import filechooser

from settings import GameMode, Settings
from model.data_classes import Player


def request_access_to_all_files():
    # copied from https://stackoverflow.com/a/79419422
    from jnius import autoclass

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Environment = autoclass('android.os.Environment')
    Uri = autoclass('android.net.Uri')
    Intent = autoclass('android.content.Intent')
    Settings = autoclass('android.provider.Settings')
    mActivity = PythonActivity.mActivity
    if not Environment.isExternalStorageManager():  # Checks if already Managing stroage
        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
        intent.setData(Uri.parse(f"package:{mActivity.getPackageName()}"))  # package:package.domain.package.name
        mActivity.startActivity(intent)


class SettingsWindow(Screen):
    player_path_label = ObjectProperty(None)
    scroll_view = ObjectProperty(None)
    player_count_label = ObjectProperty(None)
    round_label = ObjectProperty(None)
    continue_button = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(SettingsWindow, self).__init__(**kwargs)

        # relevant settings for the tournament view are bundled to be easier shareable
        self._settings = Settings()

        # additional state
        self._player_database_path = None
        self._all_players = None
        self._player_toggle_buttons = []

        # set up a folder for storing information between different app runs
        if os.path.exists('/storage/self/'):
            # seems to be an android system
            self._settings.storage_path = '/storage/self/primary/Documents/handicap_tournament'

            # necessary to be able to write to documents
            request_access_to_all_files()
        else:
            self._settings.storage_path = './runtime_storage'

        os.makedirs(self._settings.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self._settings.storage_path, 'players'), exist_ok=True)
        os.makedirs(os.path.join(self._settings.storage_path, 'tournaments'), exist_ok=True)

        # has to be delayed as otherwise the connection to the kv labels is not yet available
        Clock.schedule_once(self.initial_loading, 0)

    def initial_loading(self, _):
        # try loading the first player file
        path = os.path.join(self._settings.storage_path, 'players')

        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        if len(files) > 0:
            self.load([os.path.abspath(os.path.join(path, files[0]))])

    def get_settings(self):
        return self._settings

    def show_load(self):
        filechooser.open_file(on_selection=self.load, path=self._settings.storage_path)

    def load(self, paths):
        if len(paths) == 0:
            return

        path = paths[0]

        if not os.path.isfile(path):
            print("Warning: path invalid")
            return

        with open(path, 'r') as file:
            json_players = json.load(file)

        players = []
        for player in json_players:
            players.append(Player(**player))

        self._all_players = sorted(players, key=lambda p: p.ttr, reverse=True)
        self._player_database_path = path

        # try to shorten the path
        common_prefix = os.path.commonprefix([self._settings.storage_path, path])
        relative_path = os.path.relpath(path, common_prefix)

        self.player_path_label.text = f"[size=20]{relative_path}[/size]"

        self.update_player_selection()

    def save_settings(self):
        self.get_root_window().manager.current = 'tournament'

    def update_handicap_buttons(self, toggled_button, connected_button, state):
        # we want to ignore clicks that toggle a button from 'down' back to 'normal' as this should be triggered by
        # clicking on the other button
        if toggled_button.state == 'normal':
            toggled_button.state = 'down'
            connected_button.state = 'normal'
        else:
            connected_button.state = 'normal'

        self._settings.handicap_enabled = state
        self.update_player_selection()

    def update_match_mode_buttons(self, toggled_button, connected_button, num_sets):
        # we want to ignore clicks that toggle a button from 'down' back to 'normal' as this should be triggered by
        # clicking on the other button
        if toggled_button.state == 'normal':
            toggled_button.state = 'down'
            connected_button.state = 'normal'
        else:
            connected_button.state = 'normal'

        self._settings.match_mode = GameMode(num_sets)

    def update_system_buttons(self, toggled_button, connected_button, system):
        # we want to ignore clicks that toggle a button from 'down' back to 'normal' as this should be triggered by
        # clicking on the other button
        if toggled_button.state == 'normal':
            toggled_button.state = 'down'
            connected_button.state = 'normal'
        else:
            connected_button.state = 'normal'

        self.update_selected_players(None)

    def update_player_selection(self):
        spacing = 0
        row_height = 100
        num_rows = math.ceil(len(self._all_players) / 2)
        self.scroll_view.clear_widgets()
        self._player_toggle_buttons = []
        grid_layout = GridLayout(cols=4, rows=num_rows, spacing=spacing, size_hint_y=None, size_hint_x=1,
                                 height=(row_height + spacing) * num_rows,
                                 padding=0)

        for i, p in enumerate(self._all_players):
            if self._settings.handicap_enabled:
                value_str = f"{p.handicap}"
                if p.handicap > 0:
                    value_str = '+' + value_str
            else:
                value_str = f"{p.ttr}"

            toggle_button = ToggleButton(text=f"[size=25]{p.name} ({value_str})[/size]", markup=True, size_hint=(1, None),
                                         height=row_height, halign='center',
                                         valign='middle', on_release=self.update_selected_players,
                                         state='normal')

            self._player_toggle_buttons.append(toggle_button)

            if i % 2 == 0:
                grid_layout.add_widget(Label(text='', size_hint=(None, None)))
                grid_layout.add_widget(toggle_button)
            else:
                grid_layout.add_widget(toggle_button)
                grid_layout.add_widget(Label(text='', size_hint=(None, None)))

        self.scroll_view.add_widget(grid_layout)

        self.update_selected_players(None)

    def update_selected_players(self, dummy):
        self._settings.players = []

        for i, button in enumerate(self._player_toggle_buttons):
            if button.state == 'down':
                self._settings.players.append(self._all_players[i])

        self.player_count_label.text = f'[size=25]Anzahl Spieler: {len(self._settings.players)}[/size]'

        if len(self._settings.players) >= 3:
            self.continue_button.disabled = False

            min_round_suggestion = math.ceil(math.log2(len(self._settings.players)))
            max_round_suggestion = min(min_round_suggestion + 2, len(self._settings.players) - 1)

            if min_round_suggestion == max_round_suggestion:
                self.round_label.text = f'[size=25]Rundenempfehlung: {min_round_suggestion}[/size]'
            else:
                self.round_label.text = f'[size=25]Rundenempfehlung: {min_round_suggestion} - {max_round_suggestion}[/size]'
        else:
            self.continue_button.disabled = True
            self.round_label.text = f'[size=25]Rundenempfehlung: 0[/size]'