import copy
import random
import networkx as nx

from model.data_classes import TournamentPlayer, PlayerBye, Match, initialize_field_of_participants


class Tournament:
    def __init__(self, win_condition, players, with_handicaps):
        self._win_condition = win_condition
        self._with_handicaps = with_handicaps
        self._round_count = 0
        self._finished_matches = []
        self._round_matches = []

        self._players = initialize_field_of_participants(players, add_bye=True)

    def get_running_matches(self):
        return self._round_matches

    def get_current_round(self):
        return self._round_count

    def get_max_number_of_rounds(self):
        return len(self._players) - 1

    def generate_first_round(self):
        self._round_count = 1

        # sort players by TTR and seat the upper half, lower half is randomly assigned
        sorted_players = sorted(self._players, key=lambda p: p.ttr, reverse=True)

        seated_players = sorted_players[:len(sorted_players)//2]
        players_to_assign = sorted_players[len(sorted_players)//2:]

        # create matches
        for first_player in seated_players:
            index = random.randint(0, len(players_to_assign) - 1)

            second_player = players_to_assign[index]
            del players_to_assign[index]

            match = self._generate_match(first_player, second_player)

            self._round_matches.append(match)


    def generate_next_round(self):
        if self._round_count == 0:
            self.generate_first_round()
            return

        self._finished_matches.append(self._round_matches)

        # ensure that finished matches are reflected in the win-lose relationships of the players
        self.update_player_statistics(self._round_matches)

        # match generation via solving a graph based optimization problem
        # --> node: player
        # --> edge: two players have not yet played against each other
        graph = self.generate_graph()

        # we need to keep track of the original graph as the connectivity has to be tested with all
        # edges
        original_graph = copy.deepcopy(graph)

        # Note: due to the greedy behaviour of the swiss system it is not guaranteed that it will converge
        #       towards round robin if the recommended number of rounds is exceeded
        #       --> to enforce that convergence we try it multiple times (and ignore weights if necessary)
        pairings = {}
        for attempt in range(3):
            # generate the pairings
            pairings = dict(nx.min_weight_matching(graph))

            # from matplotlib import pyplot as plt
            # plt.figure()
            # plt.title(f"Round {self._round_count + 1}, attempt: {attempt}")
            # nx.draw(graph, with_labels=True)
            # plt.show()

            if 1 < self.get_max_number_of_rounds() - self._round_count <= 3:
                # check if we would still be able to find valid pairings in the next round
                next_round_graph = copy.deepcopy(original_graph)
                for p1, p2 in pairings.items():
                    next_round_graph.remove_edge(p1, p2)

                if not nx.is_connected(next_round_graph):
                    # ignore weights + try again
                    if attempt == 0:
                        graph = self.generate_graph(ignore_weights=True)
                    else:
                        # remove first pairing and try again
                        for p1, p2 in pairings.items():
                            graph.remove_edge(p1, p2)
                            break

                    continue

            # if reached the attempt was successful
            break

        if len(pairings.keys()) != len(self._players) / 2:
            # should not be reached, otherwise we simply offer to launch the generation of the next round once again

            # for graph in self._graphs:
            #     nx.draw(graph)
            #     from matplotlib import pyplot as plt
            #     plt.show()
            # import sys
            # sys.exit(0)
            return

        # create the proposed matches
        matches = []

        for p1_id, p2_id in pairings.items():
            # bye player should always be listed as second player
            if p1_id > p2_id:
                p2_id, p1_id = (p1_id, p2_id)

            p1 = self._players[p1_id]
            p2 = self._players[p2_id]

            match = self._generate_match(p1, p2)
            matches.append(match)

        self._round_matches = matches
        self._round_count += 1

    def generate_graph(self, ignore_weights: bool=False):
        graph = nx.Graph()

        for player in self._players:
            graph.add_node(player.id)

        for player in self._players:
            for opponent in self._players:
                if player == opponent or player.has_played_against(opponent.id) \
                        or graph.has_edge(player.id, opponent.id):
                    continue

                if player == opponent or player.has_played_against(opponent.id):
                    continue

                if graph.has_edge(player.id, opponent.id):
                    continue

                if ignore_weights:
                    edge_weight = 1
                else:
                    diff_wins = abs(len(player.wins) - len(opponent.wins))

                    if self._with_handicaps:
                        additional_diff = abs(player.handicap - opponent.handicap) * 1000
                    else:
                        additional_diff = min(abs(player.ttr - opponent.ttr), 1000)

                    edge_weight = (diff_wins ** 2) * 10000 + additional_diff

                graph.add_edge(player.id, opponent.id, weight=edge_weight)

        return graph


    def update_player_statistics(self, matches):
        for match in matches:
            p1 = self._players[match.first_player_id]
            p2 = self._players[match.second_player_id]

            for (player_id, list) in [(p1.id, p2.wins), (p1.id, p2.losses), (p2.id, p1.wins), (p2.id, p1.losses)]:
                if player_id in list:
                    list.remove(player_id)

            if not match.is_finished():
                continue

            # check whether the match is already correctly reflected as win / loss within the player data structure
            if match.sets_won() > match.sets_lost():
                winner = p1
                loser = p2
            else:
                winner = p2
                loser = p1

            if not loser.id in winner.wins:
                winner.wins.add(loser.id)

            if not winner.id in loser.losses:
                loser.losses.add(winner.id)

    def get_ranking(self):
        self.update_player_statistics(self._round_matches)

        min_wins = min([len(p.wins) for p in self._players if not p.is_bye()])

        # update buchholz values for "fine" ranking
        for p in self._players:
            p.buchholz = 0
            for loser_id in p.wins:
                loser = self._players[loser_id]
                if loser.is_bye():
                    p.buchholz += min_wins
                else:
                    p.buchholz += len(loser.wins)

        players_without_freilos = [p for p in self._players if not p.is_bye()]

        return sorted(players_without_freilos)

    def get_all_matches(self):
        return self._finished_matches + [self._round_matches]

    def get_players(self):
        return self._players

    def num_sets_for_win(self):
        return int(self._win_condition)

    def _generate_match(self, p1, p2):
        if self._with_handicaps:
            start_offset = p1.handicap - p2.handicap
        else:
            start_offset = 0

        match = Match(game_mode=self._win_condition, first_player=p1, second_player=p2,
                      start_offset=start_offset)

        if p2.is_bye():
            p1.hadByeInRound = self._round_count

            idx = 0
            while not match.is_finished():
                match.update_set_result(idx, 0)
                idx += 1

        return match
