import logging

from pylatexenc import latexwalker
from pylatexenc.latexwalker import LatexWalker, LatexNode, LatexCharsNode, LatexGroupNode, \
    LatexCommentNode, LatexMacroNode, LatexEnvironmentNode, LatexSpecialsNode, LatexMathNode
from pylatexenc.macrospec import ParsedVerbatimArgs

SRC_LANG = 'en'
DST_LANG = 'ru'
checked_langs = {'en', 'ru'}


latexwalker.LatexCharsNode.__len__ = lambda self: len(self.chars)
latexwalker.LatexCharsNode.__str__ = lambda self: self.chars


def get_node_name(node: LatexNode):
    if isinstance(node, LatexCharsNode):
        return node.chars

    if isinstance(node, LatexCommentNode):
        return node.comment

    if isinstance(node, LatexGroupNode):
        return node.delimiters[0]

    if isinstance(node, LatexMacroNode):
        return node.macroname

    if isinstance(node, LatexEnvironmentNode):
        return node.environmentname

    if isinstance(node, LatexSpecialsNode):
        return node.specials_chars

    if isinstance(node, LatexMathNode):
        return node.displaytype


class Rule:
    """ Rule is a boolean condition over a node. LatexNode -> True/False
    """

    def __init__(self, at_begin: bool, node_type: type, arg_values: [str, list] = None):
        self.at_begin = at_begin
        self.node_type = node_type
        if isinstance(arg_values, str):
            arg_values = {arg_values}
        elif isinstance(arg_values, list):
            arg_values = set(arg_values)
        self.arg_values = arg_values

    def __str__(self):
        return f"Rule {'$' if self.at_begin else '*'} {self.node_type.__class__.__name__}[{list(self.arg_values)}]"

    def match(self, node: LatexNode, parent_nodes: list) -> bool:
        """ LatexNode -> True/False
        """
        # If flag at_begin==True then node must be the first in sequence
        if self.at_begin and len(parent_nodes) > 0:
            return False

        # Match LatexNode type
        if not isinstance(node, self.node_type):
            return False

        # Match argument. If self.argument==None, any argument matches
        arg = get_node_name(node)
        if self.arg_values and arg not in self.arg_values:
            return False

        return True


LIST_ENVS = ['description', 'enumerate', 'itemize', 'list']
MATH_ENVS = ['math', 'displaymath', 'array', 'eqnarray', 'equation', 'equation*', 'subequations',
             'multline', 'align', 'align*', 'alignat', 'flalign*', 'matrix', 'pmatrix', 'bmatrix', 'Bmatrix', 'vmatrix',
             'Vmatrix', 'smallmatrix', 'cases']


class Filter:
    include_rules = [
        Rule(True, LatexEnvironmentNode, 'document'),
        Rule(True, LatexMacroNode, 'title'),
        Rule(False, LatexMacroNode, ['section', 'subsection', 'subsubsection', 'subsubsubsection']),
        Rule(False, LatexMacroNode, ['textbf', 'textit', 'texttt']),
        Rule(False, LatexMacroNode, 'caption'),  # FIXME caption is not inside but next node..
        Rule(False, LatexEnvironmentNode, LIST_ENVS),
        Rule(False, LatexEnvironmentNode, ['theorem']),
        # Rule(False, LatexSpecialsNode, ),
        # Rule(False, LatexGroupNode, ),
    ]
    exclude_rules = [
        Rule(False, LatexEnvironmentNode, ['figure', 'table', 'picture']),
        # Rule(False, LatexMacroNode, ),
    ]
    stop_rules = [
        Rule(True, LatexMacroNode, 'usepackage'),
        Rule(True, LatexMacroNode, 'newcommand'),
        Rule(False, LatexEnvironmentNode, ['bibliography', 'thebibliography', 'bibliographystyle']),
        Rule(False, LatexEnvironmentNode, MATH_ENVS),
        Rule(False, LatexEnvironmentNode, 'lstlisting'),
        Rule(False, LatexMacroNode, ['documentclass', 'newenvironment', 'renewcommand']),
        Rule(False, LatexMacroNode, ['label', 'cite', 'citep', 'citet', 'eqref', 'ref', 'color', 'verb', 'vspace', 'hspace']),
        Rule(False, LatexGroupNode, '['),
        Rule(False, LatexCommentNode, ),
        Rule(False, LatexMathNode, ),
    ]

    @staticmethod
    def decide_node(node: LatexNode, parent_nodes: list, default_decision: int) -> int:
        """
        decision: 1 - include, 0 - exclude, -1 - stop
        """
        # debug
        # if isinstance(node, LatexMacroNode):
        #     if get_node_arg(node) == 'caption':
        #         print('debug ', node)
        # if hasattr(node, 'macroname') and node.macroname == 'psi':
        #     print('debug ', node)

        if default_decision == -1:
            return -1

        # Try to apply stop rules
        for rule in Filter.stop_rules:
            if rule.match(node, parent_nodes):
                return -1

        if default_decision == 1:
            # Try to apply exclude rules
            for rule in Filter.exclude_rules:
                if rule.match(node, parent_nodes):
                    return 0

        elif default_decision == 0:
            # Try to apply include rules
            for rule in Filter.include_rules:
                if rule.match(node, parent_nodes):
                    return 1

        # # Check if NO rule can be applied
        # if not isinstance(node, LatexCharsNode) and\
        #         all(not r.match(node, parent_nodes) for r in Filter.include_rules + Filter.exclude_rules):
        #     print("No rule can be applied for ", ' -> '.join(Parser.node_to_str(n) for n in parent_nodes + [node]))
        return default_decision

    @staticmethod
    def post_filter(node: LatexCharsNode) -> bool:
        """ Some CharNode without text we do not translate, e.g. '=3', '---', 'c', etc """
        text = node.chars.strip()

        if len(text) <= 1:
            return False

        if sum(c.isalpha() for c in text) <= 1:
            return False

        return True


class Chunk:
    """
    Chunk is a list of tokens to be translated together.
    Each token represents a piece of consecutive plain text.
    Tokens are alternated with stubs which replace latex commands.

    """

    def __init__(self, tokens=None):
        self.tokens = [] if tokens is None else tokens

    def __str__(self):
        # return self._to_text()[0]
        return '<|>'.join(str(t) for t in self.tokens)

    def __getitem__(self, item: int):
        return self.tokens[item]

    def append_token(self, node: LatexCharsNode):
        self.tokens.append(node)

    def append_stub(self, stub: str):
        self.tokens.append(stub)

    def is_empty(self):
        return len(self.tokens) == 0

    # def size(self):
    #     return sum(len(t) for t in self.tokens)

    def estimated_size(self):
        """ Estimated size of text formed from tokens interleaved with separators
        """
        return sum(len(t) for t in self.tokens)

    def split_if_large(self, max_size) -> list:
        # Estimated size of text formed from tokens interleaved with separators
        est_size = self.estimated_size()
        if est_size < max_size:
            return [self]

        if len(self.tokens) < 2:
            logging.warning("Cannot split chunk, it's too big. Size=%s" % est_size)
            return [self]

        # TODO better to split by a dot. But it is inside CharNode, how to do it?
        # Split
        print("Splitting chunk of size %s" % est_size)
        assert len(self.tokens) % 2 == 1  # because N char tokens + N-1 separators
        mid = len(self.tokens) // 2
        if mid % 2 == 1:
            mid += 1
        chunk1 = Chunk(self.tokens[:mid - 1])
        chunk2 = Chunk(self.tokens[mid:])
        return chunk1.split_if_large(max_size) + \
               chunk2.split_if_large(max_size)

        # # TODO use
        # # Find any of separators
        # print("lsplit_long_text")
        # for sep in ['\n', '. ']:
        #     split_ix = text.rfind(sep, 0, limit)
        #     if split_ix == -1:
        #         continue
        # if split_ix == -1:
        #     raise RuntimeError(
        #         "Text is too long (%s) for google translate (must be < %s) and doesn't have a "
        #         "newline or even '. '. Insert them or some math in the middle and try again. "
        #         "(not fixed yet). The text was: '%s'" % (len(text), limit, text))
        # return text[:split_ix], sep, text[split_ix + len(sep):]

    def split_by_token(self, token_ix):
        chunk1 = Chunk(self.tokens[:token_ix])
        chunk2 = Chunk(self.tokens[token_ix+1:])
        return chunk1, chunk2

    def to_text(self):
        # Prepare tokens for translation (translator related part)
        spaces_before = []
        spaces_after = []
        NEW_LINE = 'NEW_LINE'  # used for a moment to handle '\n's
        for t in self.tokens:
            if isinstance(t, LatexCharsNode):
                # 1) Handle trailing whitespaces since translator will lose them
                start = 0
                end = -1
                while t.chars[start].isspace():
                    start += 1
                while t.chars[end].isspace():
                    end -= 1
                end += 1
                before = t.chars[:start]
                after = t.chars[end:] if end < 0 else ""
                spaces_before.append(before)
                spaces_after.append(after)
                # Replace whitespaces with a ' ' if any
                t.chars = "%s%s%s" % (
                    " " if len(before) > 0 else "",
                    t.chars[start: end or None],
                    " " if len(after) > 0 else "")

                # 2) Handle newlines  # TODO do we want to revert this after translation?
                # '\n' -> ' '
                # '\n\n' -> '\n'
                # t.chars = t.chars.replace('\n\n', NEW_LINE).replace('\n', ' ').replace(NEW_LINE,
                #                                                                        '\n')

        # Text to be translated is a concatenated text of all the tokens and stubs
        plain_text = ""
        for t in self.tokens:
            if isinstance(t, LatexCharsNode):
                plain_text += t.chars
            else:
                plain_text += t

        return plain_text, spaces_before, spaces_after


class Parser:
    """

    """

    def __init__(self, source_text, verbose=False):
        self.chunks = []  # sequence of tokens and stubs lists to translate together
        self.ctr = 0
        self.source_text = source_text
        self.verbose = verbose

        # print(LatexNodes2Text().latex_to_text(source_text))

        self.decisions = {True: [], False: []}
        w = LatexWalker(source_text)
        self.nodelist, pos, len_ = w.get_latex_nodes(pos=0)
        for node in self.nodelist:
            self.walk_node(node, [], 0, Chunk())
        # self._mark_with_color()

        # Print decisions
        print("Parsed latex text.")
        print("- charNodes to translate:", len(self.decisions[True]))
        print("- charNodes not to translate:", len(self.decisions[False]))
        print("- chunks:", len(self.chunks))
        print("- total length of text to translate:", sum(c.estimated_size() for c in self.chunks))

        if self.verbose:
            print("\n=== Nodes to translate:")
            for node, parent_nodes in self.decisions[True]:
                prefix = '$ '
                prefix += self.node_to_str(node)
                # prefix += ' -> '.join(self.node_to_str(n) for n in parent_nodes + [node])
                print(prefix)

            print("\n=== Nodes to NOT translate:")
            for node, parent_nodes in self.decisions[False]:
                prefix = '$ '
                prefix += ' -> '.join(self.node_to_str(n) for n in parent_nodes + [node])
                print(prefix)

    def _mark_with_color(self):
        """ Debug function - add random text color to each chunk
        """
        from random import randint
        for chunk in self.chunks:
            color = f'{randint(0, 255)},{randint(0, 255)},{randint(0, 255)}'
            for t in chunk.tokens:
                if isinstance(t, LatexCharsNode):
                    s = t.chars
                    start_idx = len(s) - len(s.lstrip())
                    end_idx = len(s.rstrip())
                    t.chars = s[:start_idx] + ("""\\begingroup\color[RGB]{%s}%s\endgroup""" % (
                        color, s[start_idx:end_idx])) + s[end_idx:]

    def add_babel_package(self, dst_lang):
        first_package_ix = None
        target_lang = {
            'ru': 'russian',
            'en': 'english',
        }[dst_lang]
        for i, node in enumerate(self.nodelist):
            if isinstance(node, LatexMacroNode) and node.macroname == 'usepackage':
                if first_package_ix is None:
                    first_package_ix = i
                args = node.nodeargd.argnlist
                if args[1].nodelist[0].chars == 'babel':
                    param_node = args[0].nodelist[0]
                    langs = param_node.chars.split(',')
                    if target_lang not in langs:
                        param_node.chars += ',' + target_lang
                        print(f"Added '{target_lang}' parameter to babel package")
                    return

        # No babel node found
        if first_package_ix is None:
            logging.warning("No package imports found.")
            first_package_ix = 1

        print("Adding babel package")
        babel_node = LatexCharsNode(f"\\usepackage[{target_lang}]{{babel}} % added language package\n")
        self.nodelist.insert(first_package_ix, babel_node)


    def walk_node(self, node: LatexNode, parent_nodes: list, default_decision, chunk=None):
        """
        Recursively process each node and decide whether to include in translation chunk.
        """
        if node is None:
            return

        decision = Filter.decide_node(node, parent_nodes, default_decision)
        prefix = '$ ' + ' -> '.join(self.node_to_str(n) for n in parent_nodes + [node])
        # print(prefix, 'decision:', decision)

        # if isinstance(node, LatexCharsNode) and '=3' in node.chars:
        #     print()

        if isinstance(node, LatexCharsNode):
            if decision == 1:
                ok = Filter.post_filter(node)
                self.decisions[ok].append((node, parent_nodes))

                if ok:  # Append to current chunk
                    chunk.append_token(node)
            else:
                self.decisions[False].append((node, parent_nodes))
            return

        if isinstance(node, LatexSpecialsNode):
            self.decisions[decision == 1].append((node, parent_nodes))

        # Handle different node types
        if hasattr(node, 'nodelist'):  # LatexGroupNode, LatexEnvironmentNode, LatexMathNode
            # Start a new chunk
            chunk = Chunk()

            # Process nodes that contain other nodes (like environments)
            for n in node.nodelist:
                self.walk_node(n, parent_nodes + [node], decision, chunk)

            if not chunk.is_empty():
                self.chunks.append(chunk)

        elif isinstance(node, LatexMacroNode):
            # Process macro arguments if they exist
            if hasattr(node, 'nodeargd') and node.nodeargd and node.nodeargd.argnlist:
                for arg in node.nodeargd.argnlist:
                    if isinstance(arg, list):
                        for n in arg:
                            self.walk_node(n, parent_nodes + [node], decision, chunk)
                    else:
                        self.walk_node(arg, parent_nodes + [node], decision, chunk)

    @staticmethod
    def node_to_str(node: LatexNode):
        """ String version of node for debugging """
        if isinstance(node, LatexCharsNode):
            return 'LatexCharsNode:[%s]' % node.chars

        if isinstance(node, LatexCommentNode):
            return 'LatexCommentNode[%s]' % node.comment

        if isinstance(node, LatexGroupNode):
            return 'LatexGroupNode[%s]' % (node.delimiters[0] + '...' + node.delimiters[1])

        if isinstance(node, LatexMacroNode):
            return 'LatexMacroNode[%s]' % node.macroname

        if isinstance(node, LatexEnvironmentNode):
            return 'LatexEnvironmentNode[%s]' % node.environmentname

        if isinstance(node, LatexSpecialsNode):
            return 'LatexSpecialsNode[%s]' % node.specials_chars

        if isinstance(node, LatexMathNode):
            return 'LatexMathNode[%s]' % '...'

    @staticmethod
    def print_node(node: LatexNode, parent_nodes: list) -> str:
        """
        Returns the LaTeX string representation of the node.
        Recursively process children.
        """
        if isinstance(node, LatexCharsNode):
            return node.chars

        if isinstance(node, LatexCommentNode):
            return '%' + node.comment + node.comment_post_space

        if isinstance(node, LatexSpecialsNode):
            return node.specials_chars

        # Handle other node types
        if isinstance(node, (LatexEnvironmentNode, LatexGroupNode, LatexMathNode, LatexMacroNode)):
            # Process nodes that contain other nodes (like environments)
            inner_content = ""
            if hasattr(node, 'nodeargd') and node.nodeargd:
                nodeargd = node.nodeargd
                # Process macro arguments if they exist
                args = []
                if nodeargd.argnlist:
                    for arg in nodeargd.argnlist:
                        if isinstance(arg, list):
                            args.append(
                                ''.join(Parser.print_node(n, parent_nodes + [node]) for n in arg))
                        elif arg is not None:
                            args.append(Parser.print_node(arg, parent_nodes + [node]))
                if isinstance(nodeargd, ParsedVerbatimArgs):
                    inner_content = f'{nodeargd.verbatim_delimiters[0]}{"".join(args)}{nodeargd.verbatim_delimiters[1]}'
                else:
                    inner_content = "".join(args)

            if hasattr(node, 'nodelist'):
                inner_content += ''.join(
                    Parser.print_node(n, parent_nodes + [node]) for n in node.nodelist)

            if isinstance(node, LatexEnvironmentNode):
                # Handle environment nodes
                return f'\\begin{{{node.environmentname}}}{inner_content}\\end{{{node.environmentname}}}'
            if isinstance(node, (LatexGroupNode, LatexMathNode)):
                return f'{node.delimiters[0]}{inner_content}{node.delimiters[1]}'
            if isinstance(node, LatexMacroNode):
                return f'\\{node.macroname}{node.macro_post_space}{inner_content}'

            return inner_content

        # Return str for unknown node types
        return str(node)

    def print_latex(self, filepath=None):
        res = ""
        for node in self.nodelist:
            res += self.print_node(node, [])
        if filepath:
            with open(filepath, 'w') as f:
                f.write(res)
        else:
            print("===== Latex =====")
            print(res)


def translate(input_path, output_path, src_lang, dst_lang, verbose):
    # Algorithm
    # 1. Parse latex into a nodes tree
    # 2. Filter which nodes contain text to be translated
    # 3. Mask non-translatable nodes
    # 4. Form chunks of text as requests to a translator
    # 5. Get response from translator and parse it to detect which text belongs to which node
    # 6. Update translatable nodes and return a new latex code
    src_lang = src_lang.lower()
    dst_lang = dst_lang.lower()
    from translators import SUPPORTED_LANGS
    if src_lang not in SUPPORTED_LANGS:
        raise RuntimeError(f"Source language '{src_lang}' is not supported.")
    if dst_lang not in SUPPORTED_LANGS:
        raise RuntimeError(f"Destination language '{dst_lang}' is not supported.")

    with open(input_path, 'r') as f:
        source_text = f.read()

    parser = Parser(source_text, verbose=False)

    from translators import CustomTranslator
    translator = CustomTranslator(parser.chunks, verbose=verbose,
                                  src_lang=src_lang, dst_lang=dst_lang)
    translator.translate()
    parser.add_babel_package(dst_lang)
    parser.print_latex(output_path)
    print("Done. See result in", output_path)


if __name__ == '__main__':

    # input_path = "../data/conference_101719.tex"
    # input_path = "../data/testing/test_diverse.tex"
    # input_path = "../data/paper3.tex"
    input_path = "../data/gasnikov.tex"
    output_path = "../data/res.tex"

    with open(input_path, 'r') as f:
        source_text = f.read()

    parser = Parser(source_text, verbose=False)

    from translators import CustomTranslator as TC

    # from translators import GoogleTranslateProxy as TC
    translator = TC(parser.chunks, verbose=True)
    translator.translate()

    parser.add_babel_package('ru')

    parser.print_latex(output_path)
