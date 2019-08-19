import re
import os
import sys
import codecs
import subprocess
from collections import defaultdict

import numpy as np

sys.path.append("/home/danniel/Desktop/CONLL2012-intern")
import pstree
import head_finder

from rnn import Node

dataset = "conll2003"
character_file = os.path.join(dataset, "character.txt")
word_file = os.path.join(dataset, "word.txt")
pos_file = os.path.join(dataset, "pos.txt")
ne_file = os.path.join(dataset, "ne.txt")
pretrained_word_file = os.path.join(dataset, "word.npy")
pretrained_embedding_file = os.path.join(dataset, "embedding.npy")

senna_path = "/home/danniel/Downloads/senna/hash"
lexicon_meta_list = [
    {"ne": "PER",  "path": os.path.join(dataset, "senna_per.txt"),  "senna": os.path.join(senna_path, "ner.per.lst")}, 
    {"ne": "ORG",  "path": os.path.join(dataset, "senna_org.txt"),  "senna": os.path.join(senna_path, "ner.org.lst")},
    {"ne": "LOC",  "path": os.path.join(dataset, "senna_loc.txt"),  "senna": os.path.join(senna_path, "ner.loc.lst")},
    {"ne": "MISC", "path": os.path.join(dataset, "senna_misc.txt"), "senna": os.path.join(senna_path, "ner.misc.lst")}]

data_path = "/home/danniel/Downloads/ner"
glove_file = "/home/danniel/Downloads/glove.840B.300d.txt"
parser_classpath = "/home/danniel/Downloads/stanford-parser-full-2015-12-09/*:"

split_raw = {"train": "eng.train", "validate": "eng.testa", "test": "eng.testb"}
split_sentence = {"train": "sentence_train.txt", "validate": "sentence_validate.txt", "test": "sentence_test.txt"}
split_parse = {"train": "parse_train.txt", "validate": "parse_validate.txt", "test": "parse_test.txt"}

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

def group_sequential_label(seq_ne_list):
    span_ne_dict = {}
    
    start, ne = -1, None
    for index, label in enumerate(seq_ne_list + ["O"]):
        if (label[0]=="O" or label[0]=="B") and ne:
            span_ne_dict[(start, index)] = ne
            start, ne = -1, None
        
        if label[0]=="B" or (label[0]=="I" and not ne):
            start, ne = index, label[2:]
        
    return span_ne_dict

def extract_ner(split):
    #with open("tmp.txt", "r") as f:
    with open(os.path.join(data_path, split_raw[split]), "r") as f:
        line_list = f.read().splitlines()
    
    sentence_list = []
    ner_list = []
        
    sentence = []
    ner = []
    for line in line_list[2:]:
        if line[:10] == "-DOCSTART-": continue
        if not line:
            if sentence:
                sentence_list.append(sentence)
                ner_list.append(group_sequential_label(ner))
                sentence = []
                ner = []
            continue
        word, _, _, sequential_label = line.split()
        sentence.append(word)
        ner.append(sequential_label)
    """    
    for i, j in enumerate(sentence_list):
        print(""
        print j
        print ner_list[i]
    """ 
    return sentence_list, ner_list
"""
def get_parse_tree(parse_string, pos_set=None):
    node = Node()
    
    # get POS
    header, parse_string = parse_string.split(" ", 1)
    node.pos = header[1:]
    if pos_set is not None: pos_set.add(node.pos)
    
    # bottom condition: hit a word
    if parse_string[0] != "(":
        node.word, parse_string = parse_string.split(")", 1)
        return node, parse_string
    node.word = None
    #node.word = ""
    
    # Process children
    while True:
        child, parse_string = get_parse_tree(parse_string, pos_set)
        node.add_child(child)
        delimiter, parse_string = parse_string[0], parse_string[1:]
        if delimiter == ")":
            return node, parse_string

def print_parse_tree(node, indent):
    print indent, node.pos, node.word
    for child in node.child_list:
        print_parse_tree(child, indent+"    ")
    return
"""
def extract_pos_from_pstree(tree, pos_set):
    pos_set.add(tree.label)
    
    for child in tree.subtrees:
        extract_pos_from_pstree(child, pos_set)
    return

def print_pstree(node, indent):
    word = node.word if node.word else ""
    print indent + node.label + " "+ word
    
    for child in node.subtrees:
        print_pstree(child, indent+"    ")
    return

def prepare_dataset():
    ne_set = set()
    word_set = set()
    character_set = set()
    pos_set = set()
    
    for split in split_raw:
        sentence_list, ner_list = extract_ner(split)
        
        # Procecss raw NER
        for ner in ner_list:
            for ne in ner.itervalues():
                ne_set.add(ne)
        
        # Procecss raw sentences
        split_sentence_file = os.path.join(dataset, split_sentence[split])
        with open(split_sentence_file, "w") as f:
            for sentence in sentence_list:
                f.write(" ".join(sentence)+"\n")
                for word in sentence:
                    word_set.add(word)
                    for character in word:
                        character_set.add(character)
        word_set |= set(["``", "''", "-LSB-", "-RSB-",
            "-LRB-", "25.49,-LRB-3-yr", "6-7-LRB-3-7", "Videoton-LRB-*",
            "-RRB-", "1-RRB-266", "12.177-RRB-.", "53.04-RRB-.", "Austria-RRB-118"])
        
        split_parse_file = os.path.join(dataset, split_parse[split])
        
        # Generate parses
        with open(split_parse_file, "w") as f:
            subprocess.call(["java", "-cp", parser_classpath,
                "edu.stanford.nlp.parser.lexparser.LexicalizedParser",
                "-outputFormat", "oneline", "-sentences", "newline", "-tokenized",
                "-escaper", "edu.stanford.nlp.process.PTBEscapingProcessor",
                "edu/stanford/nlp/models/lexparser/englishRNN.ser.gz",
                split_sentence_file], stdout=f)
        
        # Process parses
        with open(split_parse_file, "r") as f:
            line_list = f.read().splitlines()
        for line in line_list:
            #get_parse_tree(line, pos_set)
            tree = pstree.tree_from_text(line)
            extract_pos_from_pstree(tree, pos_set)
    
    with open(ne_file, "w") as f:
        for ne in sorted(ne_set):
            f.write(ne + '\n')
    
    with open(word_file, "w") as f:
        for word in sorted(word_set):
            f.write(word + '\n')
    
    with open(character_file, "w") as f:
        for character in sorted(character_set):
            f.write(character + '\n')
    
    with open(pos_file, "w") as f:
        for pos in sorted(pos_set):
            f.write(pos + '\n')
    return

def extract_glove_embeddings():
    log("extract_glove_embeddings()...")
    
    _, word_to_index = read_list_file(word_file)
    word_list = []
    embedding_list = []
    with open(glove_file, "r") as f:
        for line in f:
            line = line.strip().split()
            word = line[0]
            if word not in word_to_index: continue
            embedding = np.array([float(i) for i in line[1:]])
            word_list.append(word)
            embedding_list.append(embedding)
    
    np.save(pretrained_word_file, word_list)
    np.save(pretrained_embedding_file, embedding_list)
    
    log(" %d pre-trained words\n" % len(word_list))
    return

def construct_node(node, tree, ner_raw_data, head_raw_data, text_raw_data,
        character_to_index, word_to_index, pos_to_index, index_to_lexicon,
        pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node):
    pos = tree.label
    word = tree.word
    span = tree.span
    head = tree.head if hasattr(tree, "head") else head_raw_data[(span, pos)][1]
    ne = ner_raw_data[span] if span in ner_raw_data else "NONE"
    constituent = " ".join(text_raw_data[span[0]:span[1]]).lower()
    
    # Process pos info
    node.pos_index = pos_to_index[pos]
    pos_count[pos] += 1
    
    # Process word info
    node.word_split = [character_to_index[character] for character in word] if word else []
    node.word_index = word_to_index[word] if word else -1
    
    # Process head info
    node.head_split = [character_to_index[character] for character in head]
    #if head == "-LSB-": print text_raw_data
    node.head_index = word_to_index[head]
    
    # Process ne info
    node.ne = ne
    if ne != "NONE":
        if not node.parent or node.parent.span!=span:
            ne_count[ne] += 1
        pos_ne_count[pos] += 1
    
    # Process span info
    node.span = span
    span_to_node[span] = node
    
    # Process lexicon info
    node.lexicon_hit = [0] * len(index_to_lexicon)
    hits = 0
    for index, lexicon in index_to_lexicon.iteritems():
        if constituent in lexicon:
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
        new_tree = pstree.PSTree(label=pos, span=new_span, subtrees=sub_subtrees)
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
            character_to_index, word_to_index, pos_to_index, index_to_lexicon,
            pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node)
        nodes += child_nodes
    return nodes
    
def create_dense_nodes(ner_raw_data, text_raw_data, pos_to_index, index_to_lexicon,
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
            node = Node()
            node_list.append(node)
            node.span = span
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
            node.lexicon_hit = [0] * len(index_to_lexicon)
            hits = 0
            for index, lexicon in index_to_lexicon.iteritems():
                if constituent in lexicon:
                    node.lexicon_hit[index] = 1
                    hits = 1
            lexicon_hits[0] += hits
    
    return node_list
    
def get_tree_data(sentence_list, parse_list, ner_list,
        character_to_index, word_to_index, pos_to_index, index_to_lexicon):
    log("get_tree_data()...")
    """ Get tree structured data from CoNLL-2003
    
    Stores into Node data structure
    """
    tree_pyramid_list = []
    word_count = 0
    pos_count = defaultdict(lambda: 0)
    ne_count = defaultdict(lambda: 0)
    pos_ne_count = defaultdict(lambda: 0)
    lexicon_hits = [0]
    
    for index, parse in enumerate(parse_list):
        text_raw_data = sentence_list[index]
        word_count += len(text_raw_data)
        span_to_node = {}
        head_raw_data = head_finder.collins_find_heads(parse)
        
        root_node = Node()
        nodes = construct_node(
           root_node, parse, ner_list[index], head_raw_data, text_raw_data,
           character_to_index, word_to_index, pos_to_index, index_to_lexicon,
           pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node)
        root_node.nodes = nodes
        root_node.tokens = len(text_raw_data)
        
        additional_node_list = create_dense_nodes(
            ner_list[index], text_raw_data,
            pos_to_index, index_to_lexicon,
            pos_count, ne_count, pos_ne_count, lexicon_hits, span_to_node)
        
        tree_pyramid_list.append((root_node, additional_node_list))
        
    log(" %d sentences\n" % len(tree_pyramid_list))
    return tree_pyramid_list, word_count, pos_count, ne_count, pos_ne_count, lexicon_hits[0]

def label_tree_data(node, pos_to_index, ne_to_index):
    node.y = ne_to_index[node.ne]
    # node.y = ne_to_index[":".join(node.ner)]
        
    for child in node.child_list:
        label_tree_data(child, pos_to_index, ne_to_index)
    return
    
def read_dataset(data_split_list = ["train", "validate", "test"]):
    # Read all raw data
    sentence_data = {}
    ner_data = {}
    parse_data = {}
    for split in data_split_list:
        sentence_data[split], ner_data[split] = extract_ner(split)
        
        split_parse_file = os.path.join(dataset, split_parse[split])
        with open(split_parse_file, "r") as f:
            line_list = f.read().splitlines()
        parse_data[split] = [pstree.tree_from_text(line) for line in line_list]
    
    # Read lists of annotations
    character_list, character_to_index = read_list_file(character_file)
    word_list, word_to_index = read_list_file(word_file)
    pos_list, pos_to_index = read_list_file(pos_file)
    ne_list, ne_to_index = read_list_file(ne_file)
    
    pos_to_index["NONE"] = len(pos_to_index)
    
    # Read lexicon
    index_to_lexicon = {}
    for index, meta in enumerate(lexicon_meta_list):
        _, index_to_lexicon[index] = read_list_file(meta["senna"], "iso8859-15")
    
    # Build a tree structure for each sentence
    data = {}
    word_count = {}
    pos_count = {}
    ne_count = {}
    pos_ne_count = {}
    lexicon_hits = {}
    for split in data_split_list:
        (tree_pyramid_list,
            word_count[split], pos_count[split], ne_count[split], pos_ne_count[split],
            lexicon_hits[split]) = get_tree_data(
                sentence_data[split], parse_data[split], ner_data[split],
                character_to_index, word_to_index, pos_to_index, index_to_lexicon)
        data[split] = {"tree_pyramid_list": tree_pyramid_list, "ner_list": ner_data[split]}
        
    # Show statistics of each data split 
    print("-" * 80
    print("%10s%10s%9s%9s%7s%12s%13s" % ("split", "sentence", "token", "node", "NE", "spanned_NE",
        "lexicon_hit")
    print("-" * 80
    for split in data_split_list:
        print("%10s%10d%9d%9d%7d%12d%13d" % (split,
            len(data[split]["tree_pyramid_list"]),
            word_count[split],
            sum(pos_count[split].itervalues()),
            sum(len(ner) for ner in data[split]["ner_list"]),
            sum(ne_count[split].itervalues()),
            lexicon_hits[split])
        
    # Show POS distribution
    total_pos_count = defaultdict(lambda: 0)
    for split in data_split_list:
        for pos in pos_count[split]:
            total_pos_count[pos] += pos_count[split][pos]
    nodes = sum(total_pos_count.itervalues())
    print("\nTotal %d nodes" % nodes
    print("-"*80 + "\n   POS   count  ratio\n" + "-"*80
    for pos, count in sorted(total_pos_count.iteritems(), key=lambda x: x[1], reverse=True)[:10]:
        print("%6s %7d %5.1f%%" % (pos, count, count*100./nodes)
    
    # Show NE distribution in [train, validate]
    total_ne_count = defaultdict(lambda: 0)
    for split in data_split_list:
        if split == "test": continue
        for ne in ne_count[split]:
            total_ne_count[ne] += ne_count[split][ne]
    nes = sum(total_ne_count.itervalues())
    print("\nTotal %d spanned named entities in [train, validate]" % nes
    print("-"*80 + "\n          NE  count  ratio\n" + "-"*80
    for ne, count in sorted(total_ne_count.iteritems(), key=lambda x: x[1], reverse=True):
        print("%12s %6d %5.1f%%" % (ne, count, count*100./nes)
    
    # Show POS-NE distribution
    total_pos_ne_count = defaultdict(lambda: 0)
    for split in data_split_list:
        if split == "test": continue
        for pos in pos_ne_count[split]:
            total_pos_ne_count[pos] += pos_ne_count[split][pos]
    print("-"*80 + "\n   POS     NE   total  ratio\n" + "-"*80
    for pos, count in sorted(total_pos_ne_count.iteritems(), key=lambda x: x[1], reverse=True)[:10]:
        total = total_pos_count[pos]
        print("%6s %6d %7d %5.1f%%" % (pos, count, total, count*100./total)
    
    # Compute the mapping to labels
    ne_to_index["NONE"] = len(ne_to_index)
    
    # Add label to nodes
    for split in data_split_list:
        for tree, pyramid in data[split]["tree_pyramid_list"]:
            label_tree_data(tree, pos_to_index, ne_to_index)
            for node in pyramid:
                node.y = ne_to_index[node.ne]
        
    return (data, word_list, ne_list,
        len(character_to_index), len(pos_to_index), len(ne_to_index), len(index_to_lexicon))

if __name__ == "__main__":
    #prepare_dataset()
    """
    print(""
    parse_string = "(ROOT (S (NP (NNP EU)) (VP (VBZ rejects) (NP (JJ German) (NN call)) (PP (TO to) (NP (NN boycott) (JJ British) (NN lamb)))) (. .)))"
    root = pstree.tree_from_text(parse_string)
    print_pstree(root, "")
    print(""
    for i, j in head_finder.collins_find_heads(root).iteritems(): print i, j
    """
    #extract_glove_embeddings()
    read_dataset()
    exit()
    
    
    
    
    
    
    
    
    
    
    
