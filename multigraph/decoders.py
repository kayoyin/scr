"""
Adapted from https://github.com/smartschat/cort
"""

class MultigraphDecoder:
    def __init__(self, multigraph_creator, graph=True):
        self.coref_multigraph_creator = multigraph_creator
        self.graph = graph

    def decode(self, corpus):
        for doc in corpus:
            doc.antecedent_decisions = {}
            for mention in doc.system_mentions:
                mention.attributes["set_id"] = None

            # discard dummy mention
            self.decode_for_one_document(doc.system_mentions[1:])

    def decode_for_one_document(self, mentions):
        multigraph = \
            self.coref_multigraph_creator.construct_graph_from_mentions(
                mentions)

        for mention in mentions:
            antecedent = self.compute_antecedent(mention, multigraph, self.graph)

            if antecedent is not None:
                if self.graph:
                    if antecedent.attributes["set_id"] is None:
                        antecedent.attributes["set_id"] = \
                            mentions.index(antecedent)

                    mention.attributes["set_id"] = antecedent.attributes["set_id"]
                    mention.document.antecedent_decisions[mention.span] = \
                        antecedent.span

                else:
                    min_set_id = min([ante.attributes["set_id"] if ante.attributes["set_id"] else mentions.index(ante) for ante in antecedent])
                    for ante in antecedent:
                        ante.attributes["set_id"] = min_set_id
                    
                    mention.attributes["set_id"] = min_set_id
                    mention.document.antecedent_decisions[mention.span] = \
                        mentions[min_set_id].span

    @staticmethod
    def compute_antecedent(mention, multigraph, graph):
        weights = []
        for antecedent in multigraph.edges[mention]:
            weights.append(
                (multigraph.get_weight(mention, antecedent), antecedent))
        
        # get antecedent with highest positive weight, break ties by distance
        if len(weights) > 0 and sorted(weights)[-1][0] > 0:
            if graph:
                return sorted(weights)[-1][1]
            else:
                pos_weights = [w[1] for w in weights if w[0] > 0]
                if len(pos_weights) > 0:
                    return pos_weights