from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

# may seem unused but are required as usage is only hidden in the '.kv' file
from gui.settings_window import SettingsWindow
from gui.tournament_window import TournamentWindow
from gui.game_overview_window import GameOverviewWindow

class WindowManager(ScreenManager):
    pass


class TournamentApp(App):
    pass


if __name__ == '__main__':
    TournamentApp().run()