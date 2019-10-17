from src.milltypes import WordType, PolarizedIndexedType, ColoredType
from src.graphutils import DAG, fst
from src.extraction import order_nodes

from src.proofs import ProofNet

from itertools import chain
from typing import *


class Atom(object):
    def __init__(self, atom: str, features: List[int]):
        self.type = atom
        self.features = features

    def __str__(self) -> str:
        return 'at(' + self.type + ', ' + str(self.features) + ')'

    def __repr__(self) -> str:
        return str(self)


class Implication(object):
    def __init__(self, form_a: 'Formula', form_b: 'Formula'):
        self.A = form_a
        self.B = form_b

    def __str__(self) -> str:
        return 'impl(' + str(self.A) + ', ' + str(self.B) + ')'

    def __repr__(self) -> str:
        return str(self)


Formula = Union[Atom, Implication]


class L1(NamedTuple):
    sent_id: str
    words: List[str]
    formulas: List[Formula]
    conclusion: Formula

    def __str__(self):
        return 'lassy({}) :-\n\t{},\n\t{},\n\t{}.'.format(self.sent_id.split('/')[-1],
                                                              self.words, self.formulas, self.conclusion)


def to_l1(proof: ProofNet, dag: DAG) -> L1:
    leaves = set(filter(lambda node: dag.is_leaf(node), dag.nodes))
    leaves = order_nodes(dag, leaves)
    matchings = get_matchings(proof)
    types_ = list(map(lambda leaf: dag.attribs[leaf]['type'], leaves))
    formulas = list(map(lambda type_: type_to_formula(type_, matchings), types_))
    sent_id = dag.meta['src']
    words = list(map(lambda node: dag.attribs[node]['word'], leaves))
    return L1(sent_id, words, formulas, get_conclusion(types_, matchings))


def atomic_type_to_atom(inp: PolarizedIndexedType, matchings: Dict[int, int]) -> Atom:
    if inp.polarity:
        return Atom(str(inp.depolarize()).lower(), [inp.index])
    else:
        return Atom(str(inp.depolarize()).lower(), [matchings[inp.index]])


def colored_type_to_impl(inp: ColoredType, matchings: Dict[int, int]) -> Implication:
    a = inp.argument
    b = inp.result
    return Implication(atomic_type_to_atom(a, matchings) if isinstance(a, PolarizedIndexedType) else
                       colored_type_to_impl(a, matchings),
                       atomic_type_to_atom(b, matchings) if isinstance(b, PolarizedIndexedType) else
                       colored_type_to_impl(b, matchings))


def type_to_formula(type_: WordType, matchings: Dict[int, int]) -> Formula:
    return atomic_type_to_atom(type_, matchings) if isinstance(type_, PolarizedIndexedType) else \
        colored_type_to_impl(type_, matchings)


def get_matchings(proof: ProofNet) -> Dict[int, int]:
    return {v: k for k, v in proof}


def get_conclusion(types_: List[WordType], matchings: Dict[int, int]) -> Atom:
    atomic_types = map(lambda type_: type_.get_atomic(), types_)
    atomic_types = list(chain.from_iterable(atomic_types))
    atomic_indexes = set(map(lambda atomic: atomic.index, atomic_types))
    missing = fst(list(set(k for k in matchings.keys()) - atomic_indexes))
    missing = matchings[missing]
    conclusion = fst(list(filter(lambda atomic: atomic.index == missing, atomic_types)))
    return atomic_type_to_atom(conclusion, matchings)






