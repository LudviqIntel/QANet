import tensorflow as tf
# random module is used for generating random numbers
import random
# tqdm module is used for show the progress bar
from tqdm import tqdm
# spacy is a module used for NLP
import spacy
# ujson is used like json
import ujson as json
# collections module hold some interntic things
from collections import Counter
# numpy module has some mathemetics rules
import numpy as np
# codecs module is used for code coversion
from codecs import open

'''
This file is taken and modified from R-Net by HKUST-KnowComp
https://github.com/HKUST-KnowComp/R-Net
'''

# create a blank spacy model of English
nlp = spacy.blank("en")

# //Tokenization//convert the sentence to token
def word_tokenize(sent):
    # create a doc that can be visualized 
    doc = nlp(sent)
    # return the token's text info trained by the nlp model
    return [token.text for token in doc]

# number all the index of token of the tokens from the context, return the list of the pairs
def convert_idx(text, tokens):
    current = 0
    spans = []
    for token in tokens:
        current = text.find(token, current)
        if current < 0:
            print("Token {} cannot be found".format(token))
            raise Exception()
        spans.append((current, current + len(token)))
        current += len(token)
    return spans

# get the data to token and save them as example
def process_file(filename, data_type, word_counter, char_counter):
    print("Generating {} examples...".format(data_type))
    examples = []
    eval_examples = {}
    total = 0
    # use with operation to make sure we will close the file path whatever happened
    with open(filename, "r") as fh:
        source = json.load(fh)
        # use tqdm to show the process when it read the data from the file
        for article in tqdm(source["data"]):
            for para in article["paragraphs"]:
                # first replace ''and``to "
                context = para["context"].replace(
                    "''", '" ').replace("``", '" ')
                # tokenization the context
                context_tokens = word_tokenize(context)
                # listen the token from context
                context_chars = [list(token) for token in context_tokens]
                # number all the index of token of the tokens from the context
                spans = convert_idx(context, context_tokens)
                # add the qas addition to token and char, like add the influence to them form the qas part
                for token in context_tokens:
                    word_counter[token] += len(para["qas"])
                    for char in token:
                        char_counter[char] += len(para["qas"])
                # for each question from qas part
                for qa in para["qas"]:
                    total += 1
                    # freash the question by replacing ''and `` to "???Englishen???
                    ques = qa["question"].replace(
                        "''", '" ').replace("``", '" ')
                    # tokenization the question
                    ques_tokens = word_tokenize(ques)
                    # listen the token from the tokens from the question
                    ques_chars = [list(token) for token in ques_tokens]
                    # add the influence to the tokens and chars of the question
                    for token in ques_tokens:
                        word_counter[token] += 1
                        for char in token:
                            char_counter[char] += 1
                    # deal with the answer
                    y1s, y2s = [], []
                    answer_texts = []
                    # under a question ,we can find some answers
                    for answer in qa["answers"]:
                        # get the answer text
                        answer_text = answer["text"]
                        # get the answer start???means what???
                        answer_start = answer['answer_start']
                        # get where answer end
                        answer_end = answer_start + len(answer_text)
                        # it must have a magical format, we can get the answer from that in this way
                        answer_texts.append(answer_text)
                        # find where the answer is
                        answer_span = []
                        for idx, span in enumerate(spans):
                            # if answer_end's position is bigger than this span's start, and litter than this span's end, means it is in this span
                            if not (answer_end <= span[0] or answer_start >= span[1]):
                                # then add the index of this span to remember this answer's position in the answer_span
                                answer_span.append(idx)
                        # save the start position of every answer in the context and the end position in the context in two arrays 
                        y1, y2 = answer_span[0], answer_span[-1]
                        y1s.append(y1)
                        y2s.append(y2) 
                    example = {"context_tokens": context_tokens, "context_chars": context_chars, "ques_tokens": ques_tokens,
                               "ques_chars": ques_chars, "y1s": y1s, "y2s": y2s, "id": total}
                    # save an example in a specific format
                    examples.append(example)
                    # in one question, save it(context, the answer and the id in(or from) this context, so it means without question???)
                    eval_examples[str(total)] = {
                        "context": context, "spans": spans, "answers": answer_texts, "uuid": qa["id"]}
        # line(or arrange) the examples
        random.shuffle(examples)
        # print the total number of the questions(one question can have several answers, but placed them in one example)
        print("{} questions in total".format(len(examples)))
    # return the examples, and the eval_examples
    return examples, eval_examples

# saving the vextor and their position???
def get_embedding(counter, data_type, limit=-1, emb_file=None, size=None, vec_size=None):
    # saying embedding what kind of data, like training data or validation data?
    print("Generating {} embedding...".format(data_type))
    embedding_dict = {}
    # ???
    filtered_elements = [k for k, v in counter.items() if v > limit]
    # assert the emb_file conf is exit
    if emb_file is not None:
        assert size is not None
        assert vec_size is not None
        with open(emb_file, "r", encoding="utf-8") as fh:
            for line in tqdm(fh, total=size):
                array = line.split()
                # add the array part splited the vector to word前面是word
                word = "".join(array[0:-vec_size])
                # deal with the vector part, map each one in array to float format, and turn the type from tuple to list后面是vector  
                vector = list(map(float, array[-vec_size:]))
                # ???may be want to label the word using vector
                if word in counter and counter[word] > limit:
                    embedding_dict[word] = vector
        # ???print the embedding and filtered things' number together
        print("{} / {} tokens have corresponding {} embedding vector".format(
            len(embedding_dict), len(filtered_elements), data_type))
    else:
        assert vec_size is not None
        for token in filtered_elements:
            # _ is just a label for each thing
            # np.random.normal is outputing a number fitting Gaussion Distribution, scale=0.1 means the distribution's width is little
            # randomly generate a list, for each filtered_elements generate a  vector_size length number list
            embedding_dict[token] = [np.random.normal(
                scale=0.1) for _ in range(vec_size)]
        # ???without emb_file, we create the vector 
        print("{} tokens have corresponding embedding vector".format(
            len(filtered_elements)))

    NULL = "--NULL--"
    OOV = "--OOV--"
    # embedding_dict save the things from word to vector, like dimensionality reduction
    # enumerate the things from the embedding_dict's keys, and start the idx from two
    # by using keys(), we will get all the keys in the dict by a list, and 
    # then enum them, like they have their number position, and then get them from the first one
    # so the token is the key in embedding_dict, as means the word(or the vector), and the idx is the enum number just got
    # and them save them in ——token:idx—— way
    token2idx_dict = {token: idx for idx,token in enumerate(embedding_dict.keys(), 2)}
    # save two before the words from the embedding_dict
    token2idx_dict[NULL] = 0
    token2idx_dict[OOV] = 1
    # also create two things in the embedding_dict using random number create the vector
    embedding_dict[NULL] = [0. for _ in range(vec_size)]
    embedding_dict[OOV] = [0. for _ in range(vec_size)]
    # reverse the dict just got, and create a new dict saving idx and the vector that the token towards
    idx2emb_dict = {idx: embedding_dict[token]
                    for token, idx in token2idx_dict.items()}
    # create a list by using the vector from the dict just got, and maybe means saving all the vector
    emb_mat = [idx2emb_dict[idx] for idx in range(len(idx2emb_dict))]
    # return the vector list and the token:idx dict
    return emb_mat, token2idx_dict

# 
def convert_to_features(config, data, word2idx_dict, char2idx_dict):
    
    example = {}
    context, question = data
    context = context.replace("''", '" ').replace("``", '" ')
    question = question.replace("''", '" ').replace("``", '" ')
    # tokenize the context and question
    example['context_tokens'] = word_tokenize(context)
    example['ques_tokens'] = word_tokenize(question)
    # characterize the context and question by listen the token just got
    example['context_chars'] = [list(token) for token in example['context_tokens']]
    example['ques_chars'] = [list(token) for token in example['ques_tokens']]

    para_limit = config.test_para_limit# 1000--Limit length for paragraph in test file
    ques_limit = config.test_ques_limit# 100--Limit length for question in test file
    ans_limit = 100# maybe limit length for ans
    char_limit = config.char_limit# 16--Limit length for character

    # check if the word number in paragraph or the word number in question is larger than the limit
    def filter_func(example):
        return len(example["context_tokens"]) > para_limit or \
               len(example["ques_tokens"]) > ques_limit

    # if the example's length is not in the limit, raise an error
    if filter_func(example):
        raise ValueError("Context/Questions lengths are over the limit")

    # create an array that length is the para_limit with all thing is zero
    context_idxs = np.zeros([para_limit], dtype=np.int32)
    # create a matrix that size is para_limit(==word number of a paragraph)*char_limit(==char number of a word), so it also means it create a matrix with zero
    context_char_idxs = np.zeros([para_limit, char_limit], dtype=np.int32)
    # create an array that length is ques_limit
    ques_idxs = np.zeros([ques_limit], dtype=np.int32)
    # create a matrix that size is ques_limit(==word number of a question)*char_limit(==char number of a word)
    ques_char_idxs = np.zeros([ques_limit, char_limit], dtype=np.int32)
    # create an array that length is para_limit
    y1 = np.zeros([para_limit], dtype=np.float32)
    # create ana array that length is para_limit
    y2 = np.zeros([para_limit], dtype=np.float32)

    # find the word's position
    def _get_word(word):
        for each in (word, word.lower(), word.capitalize(), word.upper()):
            if each in word2idx_dict:
                return word2idx_dict[each]
        return 1

    # find the char's position(concern about the upper or lower type?)
    def _get_char(char):
        if char in char2idx_dict:
            return char2idx_dict[char]
        return 1

    # fullfill all the arrays or matrixs by position or idx//add all the word's position to the array
    for i, token in enumerate(example["context_tokens"]):
        context_idxs[i] = _get_word(token)

    for i, token in enumerate(example["ques_tokens"]):
        ques_idxs[i] = _get_word(token)

    for i, token in enumerate(example["context_chars"]):
        for j, char in enumerate(token):
            if j == char_limit:
                break
            context_char_idxs[i, j] = _get_char(char)

    for i, token in enumerate(example["ques_chars"]):
        for j, char in enumerate(token):
            if j == char_limit:
                break
            ques_char_idxs[i, j] = _get_char(char)

    return context_idxs, context_char_idxs, ques_idxs, ques_char_idxs

# 
def build_features(config, examples, data_type, out_file, word2idx_dict, char2idx_dict, is_test=False):

    # test_para_limit=1000, para_limit=400
    # test_ques_limit=100,ques_limit=50
    # ans_limit=30
    # char_limit=16
    para_limit = config.test_para_limit if is_test else config.para_limit
    ques_limit = config.test_ques_limit if is_test else config.ques_limit
    ans_limit = 100 if is_test else config.ans_limit
    char_limit = config.char_limit

    # test if context_tokens is longer than para_limit, or ques_tokens is longer than ques_limit, or things of para's size is greater than the ans_limit
    def filter_func(example, is_test=False):
        return len(example["context_tokens"]) > para_limit or \
               len(example["ques_tokens"]) > ques_limit or \
               (example["y2s"][0] - example["y1s"][0]) > ans_limit

    print("Processing {} examples...".format(data_type))
    # a class to output the record
    writer = tf.python_io.TFRecordWriter(out_file)
    total = 0
    total_ = 0
    meta = {}
    # for each thing in the examples(?)
    for example in tqdm(examples):
        total_ += 1

        # if their is something that larger than the limit, just continue, and not do the follow
        if filter_func(example, is_test):
            continue

        total += 1
        context_idxs = np.zeros([para_limit], dtype=np.int32)
        context_char_idxs = np.zeros([para_limit, char_limit], dtype=np.int32)
        ques_idxs = np.zeros([ques_limit], dtype=np.int32)
        ques_char_idxs = np.zeros([ques_limit, char_limit], dtype=np.int32)
        y1 = np.zeros([para_limit], dtype=np.float32)
        y2 = np.zeros([para_limit], dtype=np.float32)

        # return the idx of the word no matter what format
        def _get_word(word):
            for each in (word, word.lower(), word.capitalize(), word.upper()):
                if each in word2idx_dict:
                    return word2idx_dict[each]
            return 1

        # return the char's idx
        def _get_char(char):
            if char in char2idx_dict:
                return char2idx_dict[char]
            return 1

        # get the idx of context
        for i, token in enumerate(example["context_tokens"]):
            context_idxs[i] = _get_word(token)

        # get the idx of each token in ques
        for i, token in enumerate(example["ques_tokens"]):
            ques_idxs[i] = _get_word(token)

        # get the idx of chars in context
        for i, token in enumerate(example["context_chars"]):
            for j, char in enumerate(token):
                if j == char_limit:
                    break
                context_char_idxs[i, j] = _get_char(char)

        # get the idx of chars in ques
        for i, token in enumerate(example["ques_chars"]):
            for j, char in enumerate(token):
                if j == char_limit:
                    break
                ques_char_idxs[i, j] = _get_char(char)

        # ???for what???
        start, end = example["y1s"][-1], example["y2s"][-1]
        y1[start], y2[end] = 1.0, 1.0

        # ??? make these idx to string and to byte
        record = tf.train.Example(features=tf.train.Features(feature={
                                  "context_idxs": tf.train.Feature(bytes_list=tf.train.BytesList(value=[context_idxs.tostring()])),
                                  "ques_idxs": tf.train.Feature(bytes_list=tf.train.BytesList(value=[ques_idxs.tostring()])),
                                  "context_char_idxs": tf.train.Feature(bytes_list=tf.train.BytesList(value=[context_char_idxs.tostring()])),
                                  "ques_char_idxs": tf.train.Feature(bytes_list=tf.train.BytesList(value=[ques_char_idxs.tostring()])),
                                  "y1": tf.train.Feature(bytes_list=tf.train.BytesList(value=[y1.tostring()])),
                                  "y2": tf.train.Feature(bytes_list=tf.train.BytesList(value=[y2.tostring()])),
                                  "id": tf.train.Feature(int64_list=tf.train.Int64List(value=[example["id"]]))
                                  }))
        # save the record
        writer.write(record.SerializeToString())
    print("Built {} / {} instances of features in total".format(total, total_))
    meta["total"] = total
    writer.close()
    return meta


def save(filename, obj, message=None):
    if message is not None:
        print("Saving {}...".format(message))
        with open(filename, "w") as fh:
            json.dump(obj, fh)

# use config to do prepro
def prepro(config):
    # create two counter to count the time each letter(or word or char) attend
    word_counter, char_counter = Counter(), Counter()
    
    # process_file: get them to tokens and save them as example
    # train_file:train-v1.1.json
    # dev_file:dev-v1.1.json
    # test_file:dev-v1.1.json
    
    #   in this function, we input the train-v1.1.json, and deal with the train data, also input two counters just created
    #   in detail:
    #             if we see tqdm, that means we see a process to deal with the a piece of data
    #             
    train_examples, train_eval = process_file(
        config.train_file, "train", word_counter, char_counter)
    
    dev_examples, dev_eval = process_file(
        config.dev_file, "dev", word_counter, char_counter)
    test_examples, test_eval = process_file(
        config.test_file, "test", word_counter, char_counter)

    # fasettext=False, glove_word_file=glove.840B.300d.txt, fasttext_file is wiki-news-300d-1M.vec
    word_emb_file = config.fasttext_file if config.fasttext else config.glove_word_file
    # pretrained_char=False, glove_char_file=glove.840B.300d-char.txt
    char_emb_file = config.glove_char_file if config.pretrained_char else None
    # pretrained_char=False, glove_char_size=94
    char_emb_size = config.glove_char_size if config.pretrained_char else None
    # pretrained_char=False, glove_dim=300
    char_emb_dim = config.glove_dim if config.pretrained_char else config.char_dim

    # 
    word_emb_mat, word2idx_dict = get_embedding(
        word_counter, "word", emb_file=word_emb_file, size=config.glove_word_size, vec_size=config.glove_dim)
    char_emb_mat, char2idx_dict = get_embedding(
        char_counter, "char", emb_file=char_emb_file, size=char_emb_size, vec_size=char_emb_dim)

    build_features(config, train_examples, "train",
                   config.train_record_file, word2idx_dict, char2idx_dict)
    dev_meta = build_features(config, dev_examples, "dev",
                              config.dev_record_file, word2idx_dict, char2idx_dict)
    test_meta = build_features(config, test_examples, "test",
                               config.test_record_file, word2idx_dict, char2idx_dict, is_test=True)

    save(config.word_emb_file, word_emb_mat, message="word embedding")
    save(config.char_emb_file, char_emb_mat, message="char embedding")
    save(config.train_eval_file, train_eval, message="train eval")
    save(config.dev_eval_file, dev_eval, message="dev eval")
    save(config.test_eval_file, test_eval, message="test eval")
    save(config.dev_meta, dev_meta, message="dev meta")
    save(config.test_meta, test_meta, message="test meta")
    save(config.word_dictionary, word2idx_dict, message="word dictionary")
    save(config.char_dictionary, char2idx_dict, message="char dictionary")
