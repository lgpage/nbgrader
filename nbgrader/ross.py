import re

from nbformat import current_nbformat

from .nbformat import read
from .utils import is_locked


def ngrams(source, n=4):
    if len(source) < n:
        yield source
    else:
        for i in range(len(source)-n+1):
            yield source[i:i+n]


def shingle(source, n=4):
    if isinstance(source, list):
        source = tuple(source)
    return set(ngrams(source, n=n))


def jaccard(source, target):
    return (
        len(source.intersection(target)) /
        len(source.union(target))
    )


def get_notebook_code(notebook):
    source = []
    nb = read(notebook, current_nbformat)
    for cell in nb.cells:
        if cell.cell_type != 'code':
            continue
        if is_locked(cell):
            continue
        source.append(cell.source)
    return '\n'.join(source)


def clear_comments(source, delimiter='#'):
    new_lines = []
    lines = source.splitlines()
    for line in lines:
        if delimiter in line:
            line = line[:line.index(delimiter)]
        new_lines.append(line)
    return '\n'.join(new_lines)


class RossNode(object):

    def __init__(self, student_id, source, **kwargs):
        self.student_id = student_id
        self.token_pattern = kwargs.get('token_pattern', r"[0-9]+\.[0-9]+|[\w']+")
        self.whitespace_pattern = kwargs.get('whitespace_pattern', r"\s+")
        self._tokens = None
        self.source = source
        self.preprocess(**kwargs)

    def preprocess(self, **kwargs):
        if kwargs.get('clear_comments', True):
            delimiter = kwargs.get('comment_delimiter', '#')
            self.source = clear_comments(self.source, delimiter=delimiter)

    @property
    def tokens(self):
        if self._tokens is None:
            self._tokens = tuple(re.findall(self.token_pattern, self.source))
        return self._tokens


class RossComparison(object):

    def __init__(self, node1, node2, **kwargs):
        self.ngram_size = kwargs.get('ngram_size', 4)
        self.window_size = kwargs.get('window_size', 3)
        self.methods = kwargs.get('methods', ['wshingling'])
        self.nodes = [node1, node2]
        self._metrics = dict()

    @property
    def student_ids(self):
        return [x.student_id for x in self.nodes]

    @property
    def wshingling(self):
        if 'wshingling' not in self._metrics.keys():
            self._metrics['wshingling'] = 100 * jaccard(
                shingle(self.nodes[0].tokens, n=self.ngram_size),
                shingle(self.nodes[1].tokens, n=self.ngram_size)
            )
        return self._metrics['wshingling']

    @property
    def metrics(self):
        for method in self.methods:
            self._metrics[method] = getattr(self, method)
        return self._metrics


class RossNotebooks(object):

    def __init__(self, notebook_id, nodes=None, **kwargs):
        self.nodes = list()
        if nodes is not None:
            self.nodes.extend(nodes)
        self.notebook_id = notebook_id
        self.kwargs = kwargs
        self._comparisons = None
        self._metrics = None

    @property
    def student_ids(self):
        return [x.student_ids for x in self.nodes]

    @property
    def comparisons(self):
        if self._comparisons is None:
            self._comparisons = list()
            for i in range(len(self.nodes)-1):
                for j in range(i+1, len(self.nodes)):
                    comp = RossComparison(
                        self.nodes[i], self.nodes[j], **self.kwargs)
                    self._comparisons.append(comp)
        return self._comparisons

    @property
    def metrics(self):
        if self._metrics is None:
            self._metrics = [x.metrics for x in self.comparisons]
        return self._metrics

    def append(self, node):
        if not isinstance(node, RossNode):
            raise TypeError(node)
        self.nodes.append(node)

        if self._comparisons is not None:
            new_comps = list()
            for i in range(len(self.nodes)-1):
                new_comps.append(RossComparison(self.nodes[i], node, **kwargs))
            self._comparisons.extend(new_comps)
            if self._metrics is not None:
                self._metrics.extend([x.metrics for x in new_comps])
