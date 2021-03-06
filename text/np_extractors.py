# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from .packages import nltk

from .taggers import PatternTagger
from .exceptions import MissingCorpusException

class BaseNPExtractor(object):

    '''Abstract base class from which all NPExtractor classes inherit.

    Descendant classes should implement an API, like so:

        from text.np_extractor import MyExtractor
        extractor = MyExtractor()
        text = "Python is a high-level scripting language."
        exractor.extract(text)
        # ['Python', 'scripting language']

    In other words, descendant classes must implement an extract method
    that returns a list of noun phrases as strings.
    '''

    def extract(self, text):
        '''Return a list of noun phrases (strings) for a body of text.'''
        raise(NotImplementedError, 'must implement an extract(text) method')


class ChunkParser(nltk.ChunkParserI):

    def __init__(self):
        self.trained = False

    def train(self):
        try:
            train_data = [[(t, c) for (w, t, c) in nltk.chunk.tree2conlltags(sent)]
                          for sent in
                          nltk.corpus.conll2000.chunked_sents('train.txt', chunk_types=['NP'])]
        except LookupError:
            raise MissingCorpusException()
        unigram_tagger = nltk.UnigramTagger(train_data)
        self.tagger = nltk.BigramTagger(train_data, backoff=unigram_tagger)
        self.trained = True

    def parse(self, sentence):
        if not self.trained:
            self.train()
        pos_tags = [pos for (word, pos) in sentence]
        tagged_pos_tags = self.tagger.tag(pos_tags)
        chunktags = [chunktag for (pos, chunktag) in tagged_pos_tags]
        conlltags = [(word, pos, chunktag) for ((word, pos), chunktag) in
                     zip(sentence, chunktags)]
        return nltk.chunk.util.conlltags2tree(conlltags)


class ConllExtractor(BaseNPExtractor):

    '''A noun phrase extractor that uses chunk parsing trained with the
    ConLL-2000 training corpus.
    '''

    POS_TAGGER = PatternTagger()

    # The context-free grammar with which to filter the noun phrases
    CFG = {
        ('NNP', 'NNP'): 'NNP',
        ('NN', 'NN'): 'NNI',
        ('NNI', 'NN'): 'NNI',
        ('JJ', 'JJ'): 'JJ',
        ('JJ', 'NN'): 'NNI',
        }

    # POS suffixes that will be ignored
    INSIGNIFICANT_SUFFIXES = ['DT', 'CC', 'PRP$', 'PRP']

    def __init__(self, parser=None):
        self.parser = (ChunkParser() if not parser else parser)

    def extract(self, text):
        '''Return a list of noun phrases (strings) for body of text.'''
        sentences = nltk.tokenize.sent_tokenize(text)
        noun_phrases = []
        for sentence in sentences:
            parsed = self.parse_sentence(sentence)
            # Get the string representation of each subtree that is a
            # noun phrase tree
            phrases = [normalize_tags(filter_insignificant(each,
                       self.INSIGNIFICANT_SUFFIXES)) for each in parsed
                       if isinstance(each, nltk.tree.Tree) and each.node
                       == 'NP' and len(filter_insignificant(each)) >= 1
                       and is_match(each, cfg=self.CFG)]
            nps = [tree2str(phrase) for phrase in phrases]
            noun_phrases.extend(nps)
        return noun_phrases

    def parse_sentence(self, sentence):
        '''Tag and parse a sentence (a plain, untagged string).'''
        tagged = self.POS_TAGGER.tag(sentence)
        return self.parser.parse(tagged)


class FastNPExtractor(BaseNPExtractor):

    '''A fast and simple noun phrase extractor.

    Credit to Shlomi Babluk
    Link to original blog post:
        http://thetokenizer.com/2013/05/09/efficient-way-to-extract-the-main-topics-of-a-sentence/
    '''

    CFG = {
        ('NNP', 'NNP'): 'NNP',
        ('NN', 'NN'): 'NNI',
        ('NNI', 'NN'): 'NNI',
        ('JJ', 'JJ'): 'JJ',
        ('JJ', 'NN'): 'NNI',
        }

    def __init__(self):
        self.trained = False

    def train(self):
        try:
            train_data = nltk.corpus.brown.tagged_sents(categories='news')
        except LookupError:
            raise MissingCorpusException()
        REGEXP_TAGGER = nltk.RegexpTagger([
            (r'^-?[0-9]+(.[0-9]+)?$', 'CD'),
            (r'(-|:|;)$', ':'),
            (r'\'*$', 'MD'),
            (r'(The|the|A|a|An|an)$', 'AT'),
            (r'.*able$', 'JJ'),
            (r'^[A-Z].*$', 'NNP'),
            (r'.*ness$', 'NN'),
            (r'.*ly$', 'RB'),
            (r'.*s$', 'NNS'),
            (r'.*ing$', 'VBG'),
            (r'.*ed$', 'VBD'),
            (r'.*', 'NN'),
            ])
        UNIGRAM_TAGGER = nltk.UnigramTagger(train_data, backoff=REGEXP_TAGGER)
        self.TAGGER = nltk.BigramTagger(train_data, backoff=UNIGRAM_TAGGER)
        self.trained = True
        return None


    def tokenize_sentence(self, sentence):
        '''Split the sentence into singlw words/tokens'''
        tokens = nltk.word_tokenize(sentence)
        return tokens

    def normalize_tags(self, tagged):
        '''Normalize brown corpus' tags ("NN", "NN-PL", "NNS" > "NN")'''
        n_tagged = []
        for t in tagged:
            if t[1] == 'NP-TL' or t[1] == 'NP':
                n_tagged.append((t[0], 'NNP'))
                continue
            if t[1].endswith('-TL'):
                n_tagged.append((t[0], (t[1])[:-3]))
                continue
            if t[1].endswith('S'):
                n_tagged.append((t[0], (t[1])[:-1]))
                continue
            n_tagged.append((t[0], t[1]))
        return n_tagged

    def extract(self, sentence):
        if not self.trained:
            self.train()
        tokens = self.tokenize_sentence(sentence)
        tagged = self.TAGGER.tag(tokens)
        tags = self.normalize_tags(tagged)
        merge = True
        while merge:
            merge = False
            for x in range(0, len(tags) - 1):
                t1 = tags[x]
                t2 = tags[x + 1]
                key = t1[1], t2[1]
                value = self.CFG.get(key, '')
                if value:
                    merge = True
                    tags.pop(x)
                    tags.pop(x)
                    match = '%s %s' % (t1[0], t2[0])
                    pos = value
                    tags.insert(x, (match, pos))
                    break

        matches = [t[0] for t in tags if t[1] in ['NNP', 'NNI']]
        return matches


### Utility methods ###

def normalize_tags(chunk):
    '''Normalize the corpus tags.
    ("NN", "NN-PL", "NNS") -> "NN"
    '''
    ret = []
    for word, tag in chunk:
        if tag == 'NP-TL' or tag == 'NP':
            ret.append((word, 'NNP'))
            continue
        if tag.endswith('-TL'):
            ret.append((word, tag[:-3]))
            continue
        if tag.endswith('S'):
            ret.append((word, tag[:-1]))
            continue
        ret.append((word, tag))
    return ret


def is_match(tagged_phrase, cfg):
    copy = list(tagged_phrase)  # A copy of the list
    merge = True
    while merge:
        merge = False
        for i in range(len(copy) - 1):
            first, second = copy[i], copy[i + 1]
            key = first[1], second[1]  # Tuple of tags e.g. ('NN', 'JJ')
            value = cfg.get(key, None)
            if value:
                merge = True
                copy.pop(i)
                copy.pop(i)
                match = '{0} {0}'.format(first[0], second[0])
                pos = value
                copy.insert(i, (match, pos))
                break
    is_match = any([t[1] in ('NNP', 'NNI') for t in copy])
    return is_match


def get_structure(chunk):
    return tuple([tag for (word, tag) in chunk])


def tree2str(tree, concat=' '):
    '''Convert a nltk.tree.Tree to a string.

    For example:
        (NP a/DT beautiful/JJ new/JJ dashboard/NN) -> "a beautiful dashboard"
    '''
    s = concat.join([word for (word, tag) in tree])
    return s


def filter_insignificant(chunk, tag_suffixes=['DT', 'CC', 'PRP$', 'PRP']):
    good = []
    for word, tag in chunk:
        ok = True
        for suffix in tag_suffixes:
            if tag.endswith(suffix):
                ok = False
                break
        if ok:
            good.append((word, tag))
    return good
