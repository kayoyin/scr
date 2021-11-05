#!/usr/bin/env python

import argparse
import logging
import json

from multigraph import multigraphs, features, decoders, \
    corpora, mentions

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

parser = argparse.ArgumentParser(description='Run the multigraph coreference '
                                             'resolution system..')
parser.add_argument('-in',
                    required=True,
                    dest='input_filename',
                    help='The input file.')
parser.add_argument('-out',
                    dest='output_filename',
                    required=True,
                    help='The output file.')
parser.add_argument("--model",
                    default="multigraph",
                    type=str)

args = parser.parse_args()

logging.info("Reading in corpus")

corpus = corpora.Corpus.from_file("my corpus",
                                  args.input_filename)

logging.info("Extracting system mentions")
for doc in corpus:
    doc.system_mentions = [mentions.Mention.dummy_from_document(doc)] + [mentions.Mention.from_document(span, doc)
                       for span in doc.spans]

if args.model == "multigraph":
    # features = [features.not_me_or_you, features.me_or_you, features.spatially_close, features.prev_ante_is_noun, \
    #             features.third_person, features.spatially_far]
    features = [features.not_me_or_you, features.me_or_you, features.spatially_close, features.prev_ante_is_noun]
    graph = True
elif args.model == "baseline":
    features = [features.base_me_or_you, features.temporally_close, features.prev_ante_is_noun]
    graph = False
else:
    raise ValueError

cmc = multigraphs.CorefMultigraphCreator(features)

logging.info("Decoding")

decoder = decoders.MultigraphDecoder(cmc, graph)

decoder.decode(corpus)

logging.info("Writing coreference to file")

corpus.write_to_file(open(args.output_filename, 'w'))

logging.info("Finished")