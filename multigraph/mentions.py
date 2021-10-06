from multigraph.spans import Span

__author__ = 'smartschat'

class Mention:
    """ A mention is an expression in a document which is potentially referring.
    Attributes:
        document (CoNLLDocument): The document the mention belongs to.
        span (Span): The span of the mention in its document. If for example
            the span is (3, 4), then the mention starts at the 3rd token in
            the document and ends at the 4th (inclusive).
        attributes (dict(str, object)): A mapping of attribute names to
            attribute values. 
    """
    def __init__(self, document, span, attributes):
        """ Initialize a mention in a document.
        Args:
            document (CoNLLDocument): The document the mention belongs to.
            span (Span): The span of the mention in its document.
            attributes (dict(str, object)): A mapping of attribute names to
                attribute values (see the class documentation for more
                information).
        """
        self.document = document
        self.span = span
        self.attributes = attributes

    @staticmethod
    def dummy_from_document(document):

        return Mention(document, None, {
            "is_dummy": True,
            "annotated_set_id": None,
            "tokens": [],
            "first_in_gold_entity": True
        })

    def is_dummy(self):
        return "is_dummy" in self.attributes and self.attributes["is_dummy"]


    @staticmethod
    def from_document(span, document, first_in_gold_entity=False):
        """
        Create a mention from a span in a document.
        All attributes of the mention are computed from the linguistic
        information found in the document. For information about the
        attributes, see the class documentation.
        Args:
            document (CoNLLDocument): The document the mention belongs to.
            span (Span): The span of the mention in the document.
        Returns:
            Mention: A mention extracted from the input span in the input
            document.
        """

        i, sentence_span = document.get_sentence_id_and_span(span)

        try:
            attributes = {
                "tokens": document.tokens[span.begin:span.end + 1],
                "sentence_id": i,
                "speaker": document.speakers[span.begin:span.end + 1],
                "antecedent": None,
                "set_id": None,
                "first_in_gold_entity": first_in_gold_entity,
                "mcp": document.mcp[span.begin:span.end + 1],
                "tip": document.tip[span.begin:span.end + 1]
            }
        except:
            attributes = {
            "tokens": document.tokens[span.begin:span.end + 1],
            "sentence_id": i,
            "antecedent": None,
            "set_id": None,
            "first_in_gold_entity": first_in_gold_entity,
        }

        if span in document.coref:
            attributes["annotated_set_id"] = document.coref[span]
        else:
            attributes["annotated_set_id"] = None

        return Mention(document, span, attributes)

    @staticmethod
    def _get_ancestry(dep_tree, index, level=0):
        if level >= 2:
            return ""
        else:
            governor_id = dep_tree[index].head - 1

            direction = "L"

            if governor_id > index:
                direction = "R"

            if governor_id == -1:
                return  "-" + direction + "-NONE"
            else:
                return "-" + direction + "-" + dep_tree[governor_id].pos + \
                    Mention._get_ancestry(dep_tree, governor_id, level+1)



    def __lt__(self, other):
        """ Check whether this mention is less than another mention.
        ``self < other`` if and only if ``self.span < other.span``, that is,
            - this mention has span None (is a dummy mention), and the other
              mention has a span which is not None, or
            - this mentions begins before the other mention, or
            - the mentions begin at the same position, but this mention ends
              before the other mention.
        Args:
            other (Mention): A mention.
        Returns:
            True if this mention is less than other, False otherwise.
        """

        if self.span is None:
            return other.span is not None
        elif other.span is None:
            return False
        else:
            return self.span < other.span

    def __eq__(self, other):
        """ Check for equality.
        Two mentions are equal if they are in the same document and have the
        same span.
        Args:
            other (Mention): A mention.
        Returns:
            True if the mentions are in the same document and have the same
            span.
        """
        if isinstance(other, self.__class__):
            return self.span == other.span and self.document == other.document
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        if self.document is None:
            return hash((self.span.begin, self.span.end))
        elif self.span is None:
            return hash(self.document.identifier)
        else:
            return hash((self.document.identifier,
                         self.span.begin,
                         self.span.end))

    def __str__(self):
        return (repr(self.document) +
                ", " +
                str(self.span) +
                ": "
                + " ".join(self.attributes["tokens"]))

    def __repr__(self):
        return (repr(self.document) +
                ", " +
                str(self.span) +
                ": " +
                str(self.attributes["tokens"]))

    def get_context(self, window):
        """ Get the context in a window around the mention.
        Args:
            window (int): An integer specifying the size of the window.
        Returns:
            list(str): The tokens in a window of around the mention.
            In particular, get ``window`` tokens to the right or left of the
            mention,, depending on the sign of ``window``: if the sign is +,
            then to the right, if the sign is -, then to the left. Return
            None if the window is not contained in the document.
        """
        if window < 0 <= window + self.span.begin:
            return self.document.tokens[
                self.span.begin + window:self.span.begin]
        elif (window > 0 and self.span.end + window + 1
                <= len(self.document.tokens)):
            return self.document.tokens[
                self.span.end + 1:self.span.end + window + 1]

    def is_coreferent_with(self, m):
        """ Return whether this mention is coreferent with another mention.
        Args:
            m (Mention): Another mention.
        Returns:
            True if m and this mention are coreferent (are in the same document
            and have the same annotated set id), False otherwise.
        """

        self_set_id = self.attributes['annotated_set_id']
        m_set_id = m.attributes['annotated_set_id']

        if self.document is None and m.document is None:
            return self_set_id is not None and self_set_id == m_set_id
        elif self.is_dummy():
            return m.is_dummy()
        elif m.is_dummy():
            return self.is_dummy()
        else:
            return self.document == m.document \
                and self_set_id is not None \
                and self_set_id == m_set_id

    def decision_is_consistent(self, m):
        """ Return whether the decision to put this mention and m into the
        same entity is consistent with the gold annotation.
        The decision is consistent if one of the following conditions holds:
            - the mentions are coreferent,
            - one of the mentions is the dummy mention, and the other mention
              does not have a preceding mention that it is coreferent with.
        Args:
            m (Mention): Another mention.
        Returns:
            True if m and this mention are consistent according to the
            definition above, False otherwise.
        """

        if self.is_coreferent_with(m):
            return True
        elif self.is_dummy():
            return m.attributes['annotated_set_id'] is None \
                   or m.attributes["first_in_gold_entity"]
        elif m.is_dummy():
            return self.attributes['annotated_set_id'] is None \
                   or self.attributes["first_in_gold_entity"]
        else:
            return False
