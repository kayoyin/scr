import re
import numpy as np

I_SIGNS = ["I1","I2"]
YOU_SIGNS = ["YOU", "YOU1"]
INDEX_SIGNS = ["INDEX1", "INDEX2", "INDEX4", "INDEX-AREA", "INDEX-ORAL"]
dist_threshold = 50

def normalize(gloss):
    return gloss.strip("$^*")

def dist(loc1, loc2):
    a,b = loc1
    x,y = loc2
    return np.sqrt((a-x)**2 + (b-y)**2)

# Multigraph features

def me_or_you(anaphor, antecedent):

    anaphor_gloss = normalize(anaphor.attributes["tokens"][0])
    anaphor_signer = anaphor.attributes["speaker"][0]
    antecedent_gloss = normalize(antecedent.attributes["tokens"][0])
    antecedent_signer = antecedent.attributes["speaker"][0]

    if anaphor_signer == antecedent_signer:
        if (anaphor_gloss in YOU_SIGNS and antecedent_gloss in YOU_SIGNS) or (anaphor_gloss in I_SIGNS and antecedent_gloss in I_SIGNS):
            return 0.5
    else:
        if (anaphor_gloss in YOU_SIGNS and antecedent_gloss in I_SIGNS) or (anaphor_gloss in I_SIGNS and antecedent_gloss in YOU_SIGNS):
            return 0.5
    return 0

def not_me_or_you(anaphor, antecedent):

    anaphor_gloss = normalize(anaphor.attributes["tokens"][0])
    anaphor_signer = anaphor.attributes["speaker"][0]
    antecedent_gloss = normalize(antecedent.attributes["tokens"][0])
    antecedent_signer = antecedent.attributes["speaker"][0]

    if anaphor_signer == antecedent_signer:
        if (anaphor_gloss in YOU_SIGNS and antecedent_gloss in I_SIGNS) or (anaphor_gloss in I_SIGNS and antecedent_gloss in YOU_SIGNS):
            return -np.inf
    else:
        if (anaphor_gloss in YOU_SIGNS and antecedent_gloss in YOU_SIGNS) or (anaphor_gloss in I_SIGNS and antecedent_gloss in I_SIGNS):
            return -np.inf
    return 0

def spatially_close(anaphor, antecedent):
    if (anaphor.span.begin - antecedent.span.end) < 100 and anaphor.attributes["speaker"][0] == antecedent.attributes["speaker"][0] and normalize(anaphor.attributes["tokens"][0]) in INDEX_SIGNS and normalize(antecedent.attributes["tokens"][0]) in INDEX_SIGNS:
        distance = min(dist(anaphor.attributes["mcp"][0], antecedent.attributes["mcp"][0]), dist(anaphor.attributes["tip"][0], antecedent.attributes["tip"][0]))
        return max(0, 0.5 + (50 - distance) / 50)
    return 0

def prev_ante_is_noun(anaphor, antecedent):
    antecedent_gloss = normalize(antecedent.attributes["tokens"][0])
    if anaphor.attributes["speaker"][0] == antecedent.attributes["speaker"][0] and antecedent.span.end == anaphor.span.begin - 1 and normalize(anaphor.attributes["tokens"][0]) in INDEX_SIGNS and not antecedent_gloss.startswith("TO-") and not antecedent_gloss.startswith("GEST-") and antecedent_gloss not in INDEX_SIGNS: 
        return 0.5
    return 0
    
def third_person(anaphor, antecedent):
    anaphor_gloss = normalize(anaphor.attributes["tokens"][0])
    antecedent_gloss = normalize(antecedent.attributes["tokens"][0])
    if (anaphor_gloss in INDEX_SIGNS and antecedent_gloss in I_SIGNS + YOU_SIGNS) or (antecedent_gloss in INDEX_SIGNS and anaphor_gloss in I_SIGNS + YOU_SIGNS):
        return -np.inf
    return 0

def spatially_far(anaphor, antecedent):
    if normalize(anaphor.attributes["tokens"][0]) in INDEX_SIGNS and normalize(antecedent.attributes["tokens"][0]) in INDEX_SIGNS:
        distance = min(dist(anaphor.attributes["mcp"][0], antecedent.attributes["mcp"][0]), dist(anaphor.attributes["tip"][0], antecedent.attributes["tip"][0]))
        if distance > 100:
            return -np.inf
    return 0

    
# Baseline features 

def base_me_or_you(anaphor, antecedent):

    anaphor_gloss = normalize(anaphor.attributes["tokens"][0])
    anaphor_signer = anaphor.attributes["speaker"][0]
    antecedent_gloss = normalize(antecedent.attributes["tokens"][0])
    antecedent_signer = antecedent.attributes["speaker"][0]

    if anaphor_signer == antecedent_signer:
        if (anaphor_gloss in YOU_SIGNS and antecedent_gloss in YOU_SIGNS) or (anaphor_gloss in I_SIGNS and antecedent_gloss in I_SIGNS):
            return np.inf
    else:
        if (anaphor_gloss in YOU_SIGNS and antecedent_gloss in I_SIGNS) or (anaphor_gloss in I_SIGNS and antecedent_gloss in YOU_SIGNS):
            return np.inf
    return 0

def temporally_close(anaphor, antecedent):
    if (anaphor.span.begin - antecedent.span.end) < 100 and anaphor.attributes["speaker"][0] == antecedent.attributes["speaker"][0] and normalize(antecedent.attributes["tokens"][0]) in INDEX_SIGNS and normalize(anaphor.attributes["tokens"][0]) in INDEX_SIGNS:
        return np.inf
    return 0

