from itertools import chain
import pickle
from utils import FastText
from collections import defaultdict

import torch
from torch.utils.data import Dataset, DataLoader

import numpy as np


def load(file='test-output/sequences/words-types.p'):
    with open(file, 'rb') as f:
        wss, tss = pickle.load(f)
    return wss, tss


def get_all_unique(iterable_of_sequences):
    return set([x for x in chain.from_iterable(iterable_of_sequences)])


def make_oov_files(input_file='test-output/sequences/words-types.p', iv_vectors_file='wiki.nl/wiki.nl/vec',
                   oov_words_file='wiki.nl/oov.txt', oov_vectors_file='wiki.nl/oov.vec'):
    with open(input_file, 'rb') as f:
        ws, ts = pickle.load(f)

    all_words = get_all_unique(ws)

    model_vectors = FastText.load_vectors(iv_vectors_file)
    oov_words = FastText.find_oov(all_words, model_vectors)
    FastText.write_oov(oov_words, oov_words_file=oov_words_file)
    FastText.vectorize_oov(oov_words_file, oov_vectors_file)


def get_type_occurrences(type_sequences):
    all_types = get_all_unique(type_sequences)
    counts = {t: 0 for t in all_types}
    for ts in type_sequences:
        for t in ts:
            counts[t] = counts[t] + 1
    return counts


def get_high_occurrence_sequences(word_sequences, type_sequences, threshold):
    """
    Given an iterable of word sequences, an iterable of their corresponding type sequences, and a minimum occurrence
    threshold, returns a new pair of iterables by pruning type sequences containing low occurrence types.
    :param word_sequences:
    :param type_sequences:
    :param threshold:
    :return:
    """
    assert (len(word_sequences) == len(type_sequences))
    type_occurrences = get_type_occurrences(type_sequences)
    kept_indices = [i for i in range(len(word_sequences)) if not
                    list(filter(lambda x: type_occurrences[x] < threshold, type_sequences[i]))]
    return [word_sequences[i] for i in kept_indices], [type_sequences[i] for i in kept_indices]


def get_low_len_sequences(word_sequences, type_sequences, max_len):
    """

    :param word_sequences:
    :param type_sequences:
    :param max_len:
    :return:
    """
    assert len(word_sequences) == len(type_sequences)
    kept_indices = [i for i in range(len(word_sequences)) if len(word_sequences[i]) <= max_len]
    return [word_sequences[i] for i in kept_indices], [type_sequences[i] for i in kept_indices]


def map_ws_to_vs(word_sequence, vectors):
    return torch.Tensor(list(map(lambda x: vectors[x], word_sequence)))


class Sequencer(Dataset):
    def __init__(self, word_sequences, type_sequences, vectors, max_sentence_length=None,
                 minimum_type_occurrence=None):
        """
        Necessary in the case of larger data sets that cannot be stored in memory.
        :param word_sequences:
        :param type_sequences:
        :param vectors:
        :param max_sentence_length:
        :param minimum_type_occurrence:
        :param transform:
        """
        if max_sentence_length:
            word_sequences, type_sequences = get_low_len_sequences(word_sequences, type_sequences, max_sentence_length)
        if minimum_type_occurrence:
            word_sequences, type_sequences = get_high_occurrence_sequences(word_sequences, type_sequences,
                                                                           minimum_type_occurrence)
        self.word_sequences = word_sequences
        self.type_sequences = type_sequences
        self.max_sentence_length = max_sentence_length
        self.types = {t: i+1 for i, t in enumerate(get_all_unique(type_sequences))}
        self.types[None] = 0
        self.vectors = vectors
        assert len(word_sequences) == len(type_sequences)
        self.len = len(word_sequences)
        print('Constructed dataset of {} word sequences with max sentence length {} and a total of {} unique types'.
              format(self.len, self.max_sentence_length, len(self.types)-1))

    def __len__(self):
        return self.len

    def __getitem__(self, index):
        try:
            return (map_ws_to_vs(self.word_sequences[index], self.vectors),
                    torch.Tensor(list(map(lambda x: self.types[x], self.type_sequences[index]))))
        except KeyError:
            return None


def fake_vectors():
    return defaultdict(lambda: np.random.random(300))


def __main__(sequence_file='test-output/sequences/words-types.p', inv_file='wiki.nl/wiki.nl.vec',
         oov_file='wiki.nl/oov.vec', fake=False):
    ws, ts = load(sequence_file)

    if fake:
        vectors = fake_vectors()
    else:
        vectors = FastText.load_vectors([inv_file, oov_file])

    sequencer = Sequencer(ws, ts, vectors, max_sentence_length=10, minimum_type_occurrence=9)
    dl = DataLoader(sequencer, batch_size=32,
                    collate_fn=lambda batch: sorted(filter(lambda x: x is not None, batch),
                                                    key=lambda y: y[0].shape[0]))
    return sequencer, dl



