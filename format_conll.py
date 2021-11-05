import argparse
import json
from bs4 import BeautifulSoup

def format_answer(data):
    with open(args.data, "r") as file:
        data = file.readlines()

    soups = [BeautifulSoup(d, 'html.parser') for d in data]

    is_first = True
    doc_id = -1
    sent_id = 0
    for soup in soups:
        sent_id += 1
        for gloss_id, mention in enumerate(soup.find_all('mention')):
            if mention["id"] == "0":
                entity_map = {}
                doc_id += 1
                if is_first:
                    print(f"#begin document ({mention['document_id']}); ")
                    is_first = False
                else:
                    print("#end document")
                    sent_id = 1
                    print(f"#begin document ({mention['document_id']}); ")
            try:
                entity = mention['entity']
                if entity in entity_map:
                    entity = entity_map[entity]
                else:
                    entity_map[entity] = len(entity_map)
                    entity = entity_map[entity]
                print(f"test{sent_id}	{doc_id}	{gloss_id}	{mention.text}	({entity})")
            except:
                print(f"test{sent_id}	{doc_id}	{gloss_id}	{mention.text}	-")
        print()
    print("#end document")
            
    


def format_key(data):
    data = json.load(open(data, "r"))
    for i, (vid_id, vid_data) in enumerate(data.items()):
        print(f"#begin document ({vid_id}); ")
        entity_map = {}
        num_sents = len(vid_data["glosses"])

        for sent_id, sent in enumerate(vid_data["glosses"]):
            for gloss_id, gloss in enumerate(sent):
                entity = gloss.get("entity")
                if entity is not None:
                    if entity in entity_map:
                        entity = entity_map[entity]
                    else:
                        entity_map[entity] = len(entity_map)
                        entity = entity_map[entity]
                    print(f"test{sent_id + 1}	{i}	{gloss_id}	{gloss['Lexeme_Sign']}	({entity})")
                else:
                    print(f"test{sent_id + 1}	{i}	{gloss_id}	{gloss['Lexeme_Sign']}	-")
            #if sent_id != num_sents -1:
            print()
  
        print("#end document")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--key", default=False, action="store_true")
    args = parser.parse_args()

    if args.key:
        format_key(args.data)
    else:
        format_answer(args.data)
