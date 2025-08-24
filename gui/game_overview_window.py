from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.properties import ObjectProperty
from model.data_classes import Score


class FinishedMatchWidget(BoxLayout):
    def __init__(self, match):
        super(FinishedMatchWidget, self).__init__(orientation='horizontal', padding=0, spacing=0)
        self._match = match

        self._placeholder_path = 'resources/trophy_image_placeholder.png'
        self._trophy_path = 'resources/trophy_image.png'

        self._set_size = 30
        self._name_size = 30

        self._versus_label = Label(text=f'[size={self._name_size}]vs.[/size]', markup=True,
                                 size_hint=(1, None), height=50)
        self._p1_label = Label(text=f'[size={self._name_size}]{match.first_player_name}[/size]', markup=True,
                                 size_hint=(1, None), height=50)
        self._p2_label = Label(text=f'[size={self._name_size}]{match.second_player_name}[/size]', markup=True,
                               size_hint=(1, None), height=50)

        if match.is_finished():
            if match.sets_won() > match.sets_lost():
                self._left_image = Image(source='resources/trophy_image.png', size_hint=(1, None), height=50)
                self._right_image = Image(source='resources/trophy_image_placeholder.png', size_hint=(1, None),
                                          height=50)
            else:
                self._left_image = Image(source='resources/trophy_image_placeholder.png', size_hint=(1, None),
                                         height=50)
                self._right_image = Image(source='resources/trophy_image.png', size_hint=(1, None), height=50)
        else:
            self._left_image = Image(source='resources/trophy_image_placeholder.png', size_hint=(1, None), height=50)
            self._right_image = Image(source='resources/trophy_image_placeholder.png', size_hint=(1, None), height=50)

        self._set_label = Label(text=f'[size={self._set_size}]' + f'{match.sets_won()} : {match.sets_lost()}' + '[/size]', markup=True, size_hint=(0.5, None),
                                height=50, halign='center', valign='middle')

        self._separator = Label(text=f'[size={self._set_size}] | [/size]', markup=True,
                                size_hint=(0.5, None), height=50, halign='center', valign='middle')

        self.add_widget(self._left_image)
        self.add_widget(self._p1_label)
        self.add_widget(self._versus_label)
        self.add_widget(self._p2_label)
        self.add_widget(self._right_image)
        self.add_widget(self._set_label)
        self.add_widget(self._separator)

        for set in self._match.set_results:
            if set is not None:
                label = Label(text=f'[size={self._set_size}] {Score.to_str(set)} [/size]', markup=True,
                              size_hint=(0.5, None), height=50, halign='center', valign='middle')
            else:
                label = Label(text='', markup=True,
                              size_hint=(0.5, None), height=50)
            self.add_widget(label)


class GameOverviewWindow(Screen):
    scroll_view = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(GameOverviewWindow, self).__init__(**kwargs)
        self._games = None
        self._label_size = 35
        self._spacing = 5
        self._row_height = 70

    def on_pre_enter(self):
        self._games = self.parent.ids['tournament_window'].get_played_games()
        self.update_visualization()

    def update_visualization(self):
        num_rounds = len(self._games)

        if num_rounds == 0:
            return

        total_num_games = 0
        for round_games in self._games:
            total_num_games += len(round_games)

        self.scroll_view.clear_widgets()
        grid_layout = GridLayout(rows=num_rounds + total_num_games, cols=1,
                                 spacing=self._spacing, size_hint_y=None, size_hint_x=1,
                                 height=(self._row_height + self._spacing) * (num_rounds + total_num_games))

        for round, matches in enumerate(self._games, 1):
            round_label = Label(text=f'[b][size={self._label_size}]Runde {round}[/size][/b]', markup=True,
                                halign='left', valign='bottom', size_hint=(1, None))
            grid_layout.add_widget(round_label)

            for match in matches:
                grid_layout.add_widget(FinishedMatchWidget(match))

        self.scroll_view.add_widget(grid_layout)

