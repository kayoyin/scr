"""
Adapted from https://github.com/smartschat/cort
"""

""" Represent and manipulate text collections as a list of documents."""

from collections import defaultdict
import json
from multigraph.documents import Document

class Corpus:
    """Represents a text collection (a corpus) as a list of documents.

    Such a text collection can also be read from data, and be supplemented with
    antecedent information.

    Attributes:
        description(str): A human-readable description of the corpus.
        documents (list(Document)): A list of CoNLL documents.
    """

    def __init__(self, description, corpus_documents):
        """Construct a Corpus from a description and a list of documents.

        Args:
            description (str): A human-readable description of the corpus.
            documents (list(Document)): A list of documents.
        """
        self.description = description
        self.documents = corpus_documents

    def __iter__(self):
        """Return an iterator over documents in the corpus.

        Returns:
            An iterator over CoNLLDocuments.
        """
        return iter(self.documents)

    @staticmethod
    def from_file(description, coref_file):
        """Construct a new corpus from a description and a file.

        The file must contain documents in the format for the CoNLL shared
        tasks on coreference resolution, see
        http://conll.cemantix.org/2012/data.html.

        Args:
            description (str): A human-readable description of the corpus.
            coref_file (file): A text file of documents in the CoNLL format.

        Returns:
            Corpus: A corpus consisting of the documents described in
            coref_file
        """

        if coref_file is None:
            return []
        
        corpus = json.load(open(coref_file, "r"))

        documents = [Document(vid_id, data) for vid_id, data in corpus.items()]

        return Corpus(description, sorted(documents))

    def write_to_file(self, file):
        """Write a string representation of the corpus to a file,

        Args:
            file (file): The file the corpus should be written to.
        """
        for document in self.documents:
            file.write(document.to_simple_output())

    def write_antecedent_decisions_to_file(self, file):
        """Write antecedent decisions in the corpus to a file.

        For the format, have a look at the documenation for
        read_antecedent_decisions in this class.

        Args:
            file (file): The file the antecedent decisions should be written
                to.
        """
        for document in self.documents:
            document.write_antecedent_decisions_to_file(file)
