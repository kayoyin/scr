"""
Adapted from https://github.com/smartschat/cort
"""


class CorefMultigraph:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

    def get_weight(self, anaphor, antecedent):
        weight = 0.0
        for relation in self.edges[anaphor][antecedent]:
            weight += relation
        return weight

class CorefMultigraphCreator:
    def __init__(self, features):
        self.features = features

    def construct_graph_from_mentions(self, mentions):
        nodes = []
        edges = {}

        for i in range(0, len(mentions)):
            anaphor = mentions[i]

            nodes.append(anaphor)

            edges[anaphor] = self.construct_for_one_mention(mentions, i)

        return CorefMultigraph(nodes,
                               edges)

    def construct_for_one_mention(self, mentions, i):
        anaphor = mentions[i]

        edges = {}

        # do not include dummy mention
        for j in range(i-1, 0, -1):
            antecedent = mentions[j]
            edges[antecedent] = self.get_edge_relations(anaphor, antecedent)

        return edges

    def get_edge_relations(self, anaphor, antecedent):
        relations = []
        for r in self.features:
            relations.append(r(anaphor, antecedent))

        return relations


