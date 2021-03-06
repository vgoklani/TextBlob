# -*- coding: utf-8 -*-

MISSING_CORPUS_MESSAGE = """Looks like you are missing some required data for this feature.

To download the necessary data, simply run

    curl https://raw.github.com/sloria/TextBlob/master/download_corpora.py | python

If this doesn't fix the problem, file an issue at https://github.com/sloria/TextBlob/issues.
"""

class MissingCorpusException(Exception):

    '''Exception thrown when a user tries to use a feature that requires a
    dataset or model that the user does not on their system.
    '''

    def __init__(self, message=MISSING_CORPUS_MESSAGE, *args, **kwargs):
        super(MissingCorpusException, self).__init__(message, *args, **kwargs)