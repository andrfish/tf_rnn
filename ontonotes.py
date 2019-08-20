import re
import os
import sys
import codecs
from collections import defaultdict

import numpy as np

sys.path.append("D:/School/BRNN/tf_rnn/load_conll_2012")
from load_conll import load_data
from pstree import PSTree

from rnn import Node

dataset = "ontonotes"
character_file = os.path.join(dataset, "character.txt")
word_file = os.path.join(dataset, "word.txt")
pos_file = os.path.join(dataset, "pos.txt")
ne_file = os.path.join(dataset, "ne.txt")
pretrained_word_file = os.path.join(dataset, "word.npy")
pretrained_embedding_file = os.path.join(dataset, "embedding.npy")

data_path_prefix = "D:/School/BRNN/conll-2012/v4/data"
test_auto_data_path_prefix = "D:/School/BRNN/conll-2012/v9/data"
data_path_suffix = "data/english/annotations"
    
glove_file = "D:/School/BRNN/glove.840B.300d/glove.840B.300d.txt"

senna_path = "D:/School/BRNN/senna/hash"
dbpedia_path = "/home/danniel/Desktop/dbpedia_lexicon"
lexicon_meta_list = [
    {"ne": "PERSON",      "encoding": "iso8859-15", "clean": os.path.join(dataset, "senna_PER.txt"),   "raw": os.path.join(senna_path, "ner.per.lst")}, 
    {"ne": "ORG",         "encoding": "iso8859-15", "clean": os.path.join(dataset, "senna_ORG.txt"),   "raw": os.path.join(senna_path, "ner.org.lst")},
    {"ne": "LOC",         "encoding": "iso8859-15", "clean": os.path.join(dataset, "senna_LOC.txt"),   "raw": os.path.join(senna_path, "ner.loc.lst")}
    #{"ne": "WORK_OF_ART", "encoding": "iso8859-15", "clean": os.path.join(dataset, "senna_WOR.txt"),   "raw": os.path.join(senna_path, "ner.misc.lst")},
    #{"ne": "PERSON",      "encoding": "utf8",       "clean": os.path.join(dataset, "dbpedia_PER.txt"), "raw": os.path.join(dbpedia_path, "dbpedia_person.txt")},
    #{"ne": "ORG",         "encoding": "utf8",       "clean": os.path.join(dataset, "dbpedia_ORG.txt"), "raw": os.path.join(dbpedia_path, "dbpedia_organisation.txt")},
    #{"ne": "LOC",         "encoding": "utf8",       "clean": os.path.join(dataset, "dbpedia_LOC.txt"), "raw": os.path.join(dbpedia_path, "dbpedia_place.txt")}
    #{"ne": "WORK_OF_ART", "encoding": "utf8",       "clean": os.path.join(dataset, "dbpedia_WOR.txt"), "raw": os.path.join(dbpedia_path, "dbpedia_work.txt")}
    ]

def log(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()
    return

def read_list_file(file_path, encoding="utf8"):
    log("Read %s..." % file_path)
    
    with codecs.open(file_path, "r", encoding=encoding) as f:
        line_list = f.read().splitlines()
    line_to_index = {line: index for index, line in enumerate(line_list)}
    
    log(" %d lines\n" % len(line_to_index))
    return line_list, line_to_index

def extract_vocabulary_and_alphabet():
    log("extract_vocabulary_and_alphabet()...")
    
    character_set = set()
    word_set = set()
    for split in ["train", "development", "test"]:
        full_path = os.path.join(data_path_prefix, split, data_path_suffix)
        config = {"file_suffix": "gold_conll", "dir_prefix": full_path}
        raw_data = load_data(config)
        for document in raw_data:
            for part in raw_data[document]:
                for index, sentence in enumerate(raw_data[document][part]["text"]):
                    for word in sentence: 
                        for character in word:
                            character_set.add(character)
                        word_set.add(word)
                        
    with codecs.open(word_file, "w", encoding="utf8") as f:
        for word in sorted(word_set):
            f.write(word + '\n')
    
    with codecs.open(character_file, "w", encoding="utf8") as f:
        for character in sorted(character_set):
            f.write(character + '\n')
    
    log(" done\n")
    return

def extract_glove_embeddings():
    log("extract_glove_embeddings()...")
    
    _, word_to_index = read_list_file(word_file)
    print(word_to_index)
    word_list = []
    embedding_list = []
    with open(glove_file, "r", errors='ignore') as f:
        try:
            for line in f:
                line = line.strip().split()
                word = line[0]
                if word not in word_to_index: continue
                embedding = np.array([float(i) for i in line[1:]])
                word_list.append(word)
                embedding_list.append(embedding)
        except:
            print("Error with", f)
    
    np.save(pretrained_word_file, word_list)
    np.save(pretrained_embedding_file, embedding_list)
    
    log(" %d pre-trained words\n" % len(word_list))
    return
    
def traverse_tree(tree, ner_raw_data, head_raw_data, text_raw_data, lexicon_list, span_set):
    pos = tree.label
    span = tree.span
    head = tree.head if hasattr(tree, "head") else head_raw_data[(span, pos)][1]
    ne = ner_raw_data[span] if span in ner_raw_data else "NONE"
    constituent = " ".join(text_raw_data[span[0]:span[1]]).lower()
    
    span_set.add(span)
    for index, lexicon in enumerate(lexicon_list):
        if constituent in lexicon:
            lexicon[constituent][0] += 1
            if ne == lexicon_meta_list[index]["ne"]:
                lexicon[constituent][1] += 1
    
    # Binarize children
    if len(tree.subtrees) > 2:
        side_child_pos = tree.subtrees[-1].label
        side_child_span = tree.subtrees[-1].span
        side_child_head = head_raw_data[(side_child_span, side_child_pos)][1]
        if side_child_head != head:
            sub_subtrees = tree.subtrees[:-1]
        else:
            sub_subtrees = tree.subtrees[1:]
        new_span = (sub_subtrees[0].span[0], sub_subtrees[-1].span[1])
        new_tree = PSTree(label=pos, span=new_span, subtrees=sub_subtrees)
        new_tree.head = head
        if side_child_head != head:
            tree.subtrees = [new_tree, tree.subtrees[-1]]
        else:
            tree.subtrees = [tree.subtrees[0], new_tree]
         
    # Process children
    for subtree in tree.subtrees:
        traverse_tree(subtree, ner_raw_data, head_raw_data, text_raw_data, lexicon_list, span_set)
    return

def traverse_pyramid(ner_raw_data, text_raw_data, lexicon_list, span_set):
    max_dense_span = 3
    # Start from bigram, since all unigrams are already covered by parses
    for span_length in range(2, 1+max_dense_span):
        for span_start in range(0, 1+len(text_raw_data)-span_length):
            span = (span_start, span_start+span_length)
            if span in span_set: continue
            ne = ner_raw_data[span] if span in ner_raw_data else "NONE"
            constituent = " ".join(text_raw_data[span[0]:span[1]]).lower()
            
            for index, lexicon in enumerate(lexicon_list):
                if constituent in lexicon:
                    lexicon[constituent][0] += 1
                    if ne == lexicon_meta_list[index]["ne"]:
                        lexicon[constituent][1] += 1
    return

def extract_clean_lexicon():
    lexicon_list = []
    
    print("\nReading raw lexicons...")
    for meta in lexicon_meta_list:
        lexicon_list.append(read_list_file(meta["raw"], encoding=meta["encoding"])[1])
    print("-"*50 + "\n   ne  phrases shortest\n" + "-"*50)
    for index, lexicon in enumerate(lexicon_list):
        for phrase in lexicon:
            lexicon[phrase] = [0.,0.]
        shortest_phrase = min(lexicon.iterkeys(), key=lambda phrase: len(phrase))
        print("%12s %8d %s" % (lexicon_meta_list[index]["ne"], len(lexicon), shortest_phrase))
    
    print("Reading training data...")
    data_split_list = ["train", "validate"]
    annotation_method_list = ["gold", "auto"]
    raw_data = {}
    for split in data_split_list:
        raw_data[split] = {}
        for method in annotation_method_list:
            if split == "validate":
                data_path_root = "development"
            else:
                data_path_root = split
            full_path = os.path.join(data_path_prefix, data_path_root, data_path_suffix)
            config = {"file_suffix": "%s_conll" % method, "dir_prefix": full_path}
            raw_data[split][method] = load_data(config)
    
    log("\nCleaning lexicon by training data...")
    for split in data_split_list:
        for document in raw_data[split]["auto"]:
            for part in raw_data[split]["auto"][document]:
                
                ner_raw_data = defaultdict(lambda: {})
                for k, v in raw_data[split]["gold"][document][part]["ner"].iteritems():
                    ner_raw_data[k[0]][(k[1], k[2])] = v
                
                for index, parse in enumerate(raw_data[split]["auto"][document][part]["parses"]):
                    text_raw_data = raw_data[split]["auto"][document][part]["text"][index]
                    
                    if parse.subtrees[0].label == "NOPARSE": continue
                    head_raw_data = raw_data[split]["auto"][document][part]["heads"][index]
                    
                    span_set = set()
                    traverse_tree(parse, ner_raw_data[index], head_raw_data, text_raw_data,
                        lexicon_list, span_set)
                    traverse_pyramid(ner_raw_data[index], text_raw_data, lexicon_list, span_set)
    log(" done\n")
       
    print("-"*50 + "\n   ne  phrases shortest\n" + "-"*50)
    for index, lexicon in enumerate(lexicon_list):
        for phrase, count in lexicon.items():
            if count[0]>0 and count[1]/count[0]<0.1:
                del lexicon[phrase]
        shortest_phrase = min(lexicon.iterkeys(), key=lambda phrase: len(phrase))
        print("%12s %8d %s" % (lexicon_meta_list[index]["ne"], len(lexicon), shortest_phrase))
        
    for index, lexicon in enumerate(lexicon_list):
        meta = lexicon_meta_list[index]
        with codecs.open(meta["clean"], "w", encoding=meta["encoding"]) as f:
            for phrase in sorted(lexicon.iterkeys()):
                f.write("%s\n" % phrase)
    return

def construct_node(node, tree, ner_raw_data, head_raw_data, text_raw_data,
        character_to_index, word_to_index, pos_to_index, lexicon_list,
        pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node, under_ne):
    pos = tree.label
    word = tree.word
    span = tree.span
    head = tree.head if hasattr(tree, "head") else head_raw_data[(span, pos)][1]
    ne = ner_raw_data[span] if span in ner_raw_data else "NONE"
    constituent = " ".join(text_raw_data[span[0]:span[1]]).lower()
    
    # Process pos info
    node.pos_index = pos_to_index[pos]
    pos_count[pos] += 1
    node.pos = pos #YOLO
    
    # Process word info
    node.word_split = [character_to_index[character] for character in word] if word else []
    node.word_index = word_to_index[word] if word else -1
    node.word = word if word else "" # YOLO
    
    # Process head info
    node.head_split = [character_to_index[character] for character in head]
    node.head_index = word_to_index[head]
    node.head = head # YOLO
    
    # Process ne info
    node.under_ne = under_ne
    node.ne = ne
    if ne != "NONE":
        under_ne = True
        if not node.parent or node.parent.span!=span:
            ne_count[ne] += 1
        pos_ne_count[pos] += 1
        """
        if hasattr(tree, "head"):
            print(" ".join(text_raw_data)
            print(" ".join(text_raw_data[span[0]:span[1]])
            print ne
            print node.parent.head
            raw_input()
        """
    # Process span info
    node.span = span
    node.span_length = span[1] - span[0]
    span_to_node[span] = node
    
    # Process lexicon info
    node.lexicon_hit = [0] * len(lexicon_list)
    hits = 0
    for index, lexicon in enumerate(lexicon_list):
        if constituent in lexicon:
            lexicon[constituent] += 1
            node.lexicon_hit[index] = 1
            hits = 1
    lexicon_hits[0] += hits
    
    # Binarize children
    if len(tree.subtrees) > 2:
        side_child_pos = tree.subtrees[-1].label
        side_child_span = tree.subtrees[-1].span
        side_child_head = head_raw_data[(side_child_span, side_child_pos)][1]
        if side_child_head != head:
            sub_subtrees = tree.subtrees[:-1]
        else:
            sub_subtrees = tree.subtrees[1:]
        new_span = (sub_subtrees[0].span[0], sub_subtrees[-1].span[1])
        new_tree = PSTree(label=pos, span=new_span, subtrees=sub_subtrees)
        new_tree.head = head
        if side_child_head != head:
            tree.subtrees = [new_tree, tree.subtrees[-1]]
        else:
            tree.subtrees = [tree.subtrees[0], new_tree]
         
    # Process children
    nodes = 1
    for subtree in tree.subtrees:
        child = Node()
        node.add_child(child)
        child_nodes = construct_node(child, subtree, ner_raw_data, head_raw_data, text_raw_data,
            character_to_index, word_to_index, pos_to_index, lexicon_list,
            pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node, under_ne)
        nodes += child_nodes
    return nodes

def create_dense_nodes(ner_raw_data, text_raw_data, pos_to_index, lexicon_list,
        pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node):
    node_list = []
    max_dense_span = 3
    # Start from bigram, since all unigrams are already covered by parses
    for span_length in range(2, 1+max_dense_span):
        for span_start in range(0, 1+len(text_raw_data)-span_length):
            span = (span_start, span_start+span_length)
            if span in span_to_node: continue
            pos = "NONE"
            ne = ner_raw_data[span] if span in ner_raw_data else "NONE"
            constituent = " ".join(text_raw_data[span[0]:span[1]]).lower()
            
            # span, child
            # TODO: sibling
            node = Node(family=1)
            node_list.append(node)
            node.span = span
            node.span_length = span_length
            span_to_node[span] = node
            node.child_list = [span_to_node[(span[0],span[1]-1)], span_to_node[(span[0]+1,span[1])]]
            
            # word, head, pos
            node.pos_index = pos_to_index[pos]
            pos_count[pos] += 1
            node.word_split = []
            node.word_index = -1
            node.head_split = []
            node.head_index = -1
            
            # ne
            node.ne = ne
            if ne != "NONE":
                ne_count[ne] += 1
                pos_ne_count[pos] += 1
            
            # lexicon
            node.lexicon_hit = [0] * len(lexicon_list)
            hits = 0
            for index, lexicon in enumerate(lexicon_list):
                if constituent in lexicon:
                    lexicon[constituent] += 1
                    node.lexicon_hit[index] = 1
                    hits = 1
            lexicon_hits[0] += hits
    
    return node_list
    
def get_tree_data(raw_data, character_to_index, word_to_index, pos_to_index, lexicon_list):
    log("get_tree_data()...")
    """ Get tree structured data from CoNLL 2012
    
    Stores into Node data structure
    """
    tree_pyramid_list = []
    ner_list = []
    word_count = 0
    pos_count = defaultdict(lambda: 0)
    ne_count = defaultdict(lambda: 0)
    pos_ne_count = defaultdict(lambda: 0)
    lexicon_hits = [0]
    
    for document in raw_data["auto"]:
        for part in raw_data["auto"][document]:
            
            ner_raw_data = defaultdict(lambda: {})
            for k, v in raw_data["gold"][document][part]["ner"].iteritems():
                ner_raw_data[k[0]][(k[1], k[2])] = v
            
            for index, parse in enumerate(raw_data["auto"][document][part]["parses"]):
                text_raw_data = raw_data["auto"][document][part]["text"][index]
                word_count += len(text_raw_data)
                
                if parse.subtrees[0].label == "NOPARSE": continue
                head_raw_data = raw_data["auto"][document][part]["heads"][index]
                
                root_node = Node()
                span_to_node = {}
                nodes = construct_node(
                   root_node, parse, ner_raw_data[index], head_raw_data, text_raw_data,
                   character_to_index, word_to_index, pos_to_index, lexicon_list,
                   pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node, False)
                root_node.nodes = nodes
                root_node.text_raw_data = text_raw_data #YOLO
                
                additional_node_list = []
                """
                additional_node_list = create_dense_nodes(
                    ner_raw_data[index], text_raw_data,
                    pos_to_index, lexicon_list,
                    pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node)
                """
                tree_pyramid_list.append((root_node, additional_node_list))
                ner_list.append(ner_raw_data[index])
                
    log(" %d sentences\n" % len(tree_pyramid_list))
    return (tree_pyramid_list, ner_list, word_count, pos_count, ne_count, pos_ne_count,
        lexicon_hits[0])

def label_tree_data(node, pos_to_index, ne_to_index):
    node.y = ne_to_index[node.ne]
    # node.y = ne_to_index[":".join(node.ner)]
        
    for child in node.child_list:
        label_tree_data(child, pos_to_index, ne_to_index)
    return
    
def read_dataset(data_split_list = ["train", "validate", "test"]):
    # Read all raw data
    annotation_method_list = ["gold", "auto"]
    raw_data = {}
    for split in data_split_list:
        raw_data[split] = {}
        for method in annotation_method_list:
            if split == "test" and method == "auto":
                full_path = os.path.join(test_auto_data_path_prefix, "test", data_path_suffix)
            else:
                if split == "validate":
                    data_path_root = "development"
                else:
                    data_path_root = split
                full_path = os.path.join(data_path_prefix, data_path_root, data_path_suffix)
            config = {"file_suffix": "%s_conll" % method, "dir_prefix": full_path}
            raw_data[split][method] = load_data(config)
    
    # Read lists of annotations
    character_list, character_to_index = read_list_file(character_file)
    word_list, word_to_index = read_list_file(word_file)
    pos_list, pos_to_index = read_list_file(pos_file)
    ne_list, ne_to_index = read_list_file(ne_file)
    
    pos_to_index["NONE"] = len(pos_to_index)
    
    # Read lexicon
    lexicon_list = []
    for meta in lexicon_meta_list:
        lexicon_list.append(read_list_file(meta["raw"], encoding=meta["encoding"])[1])
        #lexicon_list.append(read_list_file(meta["clean"], encoding=meta["encoding"])[1])
    
    for lexicon in lexicon_list:
        for phrase in lexicon:
            lexicon[phrase] = 0
    
    # Build a tree structure for each sentence
    data = {}
    word_count = {}
    pos_count = {}
    ne_count = {}
    pos_ne_count = {}
    lexicon_hits = {}
    for split in data_split_list:
        (tree_pyramid_list, ner_list,
            word_count[split], pos_count[split], ne_count[split], pos_ne_count[split],
            lexicon_hits[split]) = get_tree_data(raw_data[split],
                character_to_index, word_to_index, pos_to_index, lexicon_list)
        #data[split] = [tree_list, ner_list]
        data[split] = {"tree_pyramid_list": tree_pyramid_list, "ner_list": ner_list}
    
    for index, lexicon in enumerate(lexicon_list):
        with codecs.open("tmp_%d.txt" % index, "w", encoding="utf8") as f:
            for phrase, count in sorted(lexicon.iteritems(), key=lambda x: (-x[1], x[0])):
                if count == 0: break
                f.write("%9d %s\n" % (count, phrase))
    
    # Show statistics of each data split 
    print("-" * 80)
    print("%10s%10s%9s%9s%7s%12s%13s" % ("split", "sentence", "token", "node", "NE", "spanned_NE",
        "lexicon_hit"))
    print("-" * 80)
    for split in data_split_list:
        print("%10s%10d%9d%9d%7d%12d%13d" % (split,
            len(data[split]["tree_pyramid_list"]),
            word_count[split],
            sum(pos_count[split].itervalues()),
            sum(len(ner) for ner in data[split]["ner_list"]),
            sum(ne_count[split].itervalues()),
            lexicon_hits[split]))
    
    # Show POS distribution
    total_pos_count = defaultdict(lambda: 0)
    for split in data_split_list:
        for pos in pos_count[split]:
            total_pos_count[pos] += pos_count[split][pos]
    nodes = sum(total_pos_count.itervalues())
    print("\nTotal %d nodes" % nodes)
    print("-"*80 + "\n   POS   count  ratio\n" + "-"*80)
    for pos, count in sorted(total_pos_count.iteritems(), key=lambda x: x[1], reverse=True)[:10]:
        print("%6s %7d %5.1f%%" % (pos, count, count*100./nodes))
    
    # Show NE distribution in [train, validate]
    total_ne_count = defaultdict(lambda: 0)
    for split in data_split_list:
        if split == "test": continue
        for ne in ne_count[split]:
            total_ne_count[ne] += ne_count[split][ne]
    nes = sum(total_ne_count.itervalues())
    print("\nTotal %d spanned named entities in [train, validate]" % nes)
    print("-"*80 + "\n          NE  count  ratio\n" + "-"*80)
    for ne, count in sorted(total_ne_count.iteritems(), key=lambda x: x[1], reverse=True):
        print("%12s %6d %5.1f%%" % (ne, count, count*100./nes))
    
    # Show POS-NE distribution in [train, validate]
    total_pos_ne_count = defaultdict(lambda: 0)
    for split in data_split_list:
        if split == "test": continue
        for pos in pos_ne_count[split]:
            total_pos_ne_count[pos] += pos_ne_count[split][pos]
    print("-"*80 + "\n   POS     NE   total  ratio\n" + "-"*80)
    for pos, count in sorted(total_pos_ne_count.iteritems(), key=lambda x: x[1], reverse=True)[:10]:
        total = total_pos_count[pos]
        print("%6s %6d %7d %5.1f%%" % (pos, count, total, count*100./total))
    
    # Compute the mapping to labels
    ne_to_index["NONE"] = len(ne_to_index)
    
    # Add label to nodes
    for split in data_split_list:
        for tree, pyramid in data[split]["tree_pyramid_list"]:
            label_tree_data(tree, pos_to_index, ne_to_index)
            for node in pyramid:
                node.y = ne_to_index[node.ne]
    
    return (data, word_list, ne_list,
            len(character_to_index), len(pos_to_index), len(ne_to_index), len(lexicon_list))

if __name__ == "__main__":
    extract_vocabulary_and_alphabet()
    extract_glove_embeddings()
    #extract_clean_lexicon()
    #read_dataset()
    exit()
    
    
    
    
    
