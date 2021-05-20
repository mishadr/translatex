# coding=utf-8
import argparse
import itertools

from TexSoup.data import BraceGroup
from TexSoup import TexSoup, TexNode
from TexSoup.reader import SIGNATURES
from TexSoup.utils import Token
from googletrans import Translator


SRC_LANG = 'en'
DST_LANG = 'ru'
checked_langs = {'en', 'ru'}

MAX_LENGTH_TEXT_TRANSLATE = 2000  # limit for google translate at once

MATH_STUB = 'MATH_STUB'  # used to replace math formulas before auto-translation
TEX_STUB = 'TEX_STUB'  # used to replace short Tex commands within one piece of text
TEX_SEP = '\nTEX_SEP\n'  # used to separate pieces of text
TOKEN_SEP = 'TOKEN_SEP'  # used to separate consecutive tokens
NEW_LINE = 'NEW_LINE'  # used for a moment to handle '\n's

TRANSLATOR = Translator(raise_exception=True)

# Workaround to TexSoup according to https://github.com/alvinwan/TexSoup/issues/115
# TODO check when bug is fixed
SIGNATURES.update({
    'def': (0, 0),
    'cup': (0, 0),
    'noindent': (0, 0),
    'in': (0, 0),
    'bigl': (0, 0),
    'bigr': (0, 0),
    'left': (0, 0),
    'right': (0, 0),
})


def google_translate_text(text: str, src_lang=SRC_LANG, dst_lang=DST_LANG) -> str:
    if len(text) > MAX_LENGTH_TEXT_TRANSLATE:
        raise RuntimeError("Text is too long (%s) for google translate (must be < %s)."
                           "Insert some math in the middle and try again. (not fixed yet)."
                           "The text was: '%s'" % (
            len(text), MAX_LENGTH_TEXT_TRANSLATE, text))
    # FIXME after several frequent requests it will ban your IP, what about proxies?
    print("Translating text of length %s" % len(text))
    res = TRANSLATOR.translate(text, dest=dst_lang, src=src_lang).text
    # res = t.upper()
    print(res)
    return res


class Chunk:
    """
    Chunk is a list of tokens to be translated together.
    Each token represents a piece of consecutive plain text.
    Tokens are alternated with stubs which replace latex commands.

    """
    # Heuristic rules to exclude token from chunk
    exclude_rules = [
        # # Token is too short, e.g. '*', 'th', 'st'
        # lambda token: len(token) < 3,

        # Token contains mainly special symbols
        lambda token: len(token.strip()) > 2 > sum(c.isalpha() for c in token),
    ]
    # Exceptions for rules
    exceptions = [
        # Token is a brace
        lambda token: len(token) == 1 and token in "[]()",
    ]

    def __init__(self):
        self.tokens = []

    def append_token(self, token: Token):
        text = str(token.text)

        # Define whether to ignore token
        if not any(e(text) for e in self.exceptions):
            if any(rule(text) for rule in self.exclude_rules):
                return

        self.tokens.append(token)

    def append_stub(self, stub: str):
        self.tokens.append(stub)

    def is_empty(self):
        return len(self.tokens) == 0

    def size(self):
        return sum(len(t) for t in self.tokens)

    # @logger.catch
    def translate(self):
        """ Translate in-place. """
        # Prepare tokens for translation (translator related part)
        spaces_before = []
        spaces_after = []
        for t in self.tokens:
            if isinstance(t, Token):
                # 1) Handle trailing whitespaces since translator will lose them
                start = 0
                end = -1
                while t.text[start].isspace():
                    start += 1
                while t.text[end].isspace():
                    end -= 1
                end += 1
                before = t.text[:start]
                after = t.text[end:] if end < 0 else ""
                spaces_before.append(before)
                spaces_after.append(after)
                # Replace whitespaces with a ' ' if any
                t.text = "%s%s%s" % (
                    " " if len(before) > 0 else "",
                    t.text[start: end or None],
                    " " if len(after) > 0 else "")

                # 2) Handle newlines  # TODO do we want to revert this after translation?
                # '\n' -> ' '
                # '\n\n' -> '\n'
                t.text = t.text.replace('\n\n', NEW_LINE).replace('\n', ' ').replace(NEW_LINE, '\n')

        # Text to be translated is a concatenated text of all the tokens and stubs
        plain_text = ""
        for t in self.tokens:
            if isinstance(t, Token):
                plain_text += t.text
            else:
                plain_text += t

        # Translate plain text
        dest_text = google_translate_text(plain_text)

        # TODO process text after translator:
        # remove whitespaces between word and * (Conference Paper Title* -> Название доклада конференции *)
        # remove whitespaces around '/' (Wb/m -> Wb / m)
        # remove extra whitespaces within various quotes (``0,25'' -> `` 0,25 '', sometimes `` 0,25 ' '),
        # around '~', etc
        # ...

        # Split translated text back into tokens
        # TODO assert tokens don't contain stubs text besides that we put there
        parts = [dest_text]
        for sep in [TEX_SEP, TEX_STUB, TOKEN_SEP]:
            parts = itertools.chain.from_iterable([p.split(sep) for p in parts])
        parts = list(parts)

        # We suppose tokens list was [Token, *, Token, *, .., Token]
        assert 2*len(parts)-1 == len(self.tokens)
        ix = 0
        for t in self.tokens:
            if isinstance(t, Token):
                t.text = spaces_before[ix] + parts[ix].strip() + spaces_after[ix]
                ix += 1


class Chunker:
    """
    Parses Texsoup tree into chunks
    """
    # TODO ignore some TexNodes:
    # \aligned ???
    # \begin{array}{this argument}
    ignore_texnodes = [
        'label', 'cite', 'color', 'thebibliography', 'ref', 'eqref', '$',
        'usepackage', 'addbibresource',  # preamble - do we translate it at all?
        'tabular',  # to prevent translating '&' as 'and'
        'algorithm',  # to prevent translating keywords FIXME some text could be inside?
        'equation',  # to prevent translating keywords FIXME some text could be inside?
    ]

    def __init__(self):
        self.chunks = [Chunk()]  # sequence of tokens and stubs lists to translate together

    def parse_node(self, elem: TexNode, chunk=None):
        if chunk is None:
            chunk = self.chunks[-1]
        if isinstance(elem, TexNode):
            if elem.name in self.ignore_texnodes:
                return

            # Start a new chunk
            new_chunk = Chunk()
            self.chunks.append(new_chunk)
            for e in elem.contents:
                self.parse_node(e, new_chunk)

            if new_chunk.is_empty():
                chunk.append_stub(TEX_STUB)
            elif False:
                # TODO in some cases we want to embed parts into chunk, e.g.
                # \textit{...}, etc
                # {\em ...} and other simple BraceGroups
                pass
            else:
                chunk.append_stub(TEX_SEP)

        elif isinstance(elem, Token):
            # Append to current chunk
            chunk.append_token(elem)
        # elif isinstance(elem, str):
        #     print('*', elem)  # FIXME
        # else:
        #     print('**', type(elem), elem)
        #     # raise ValueError("")

    def finalize(self):
        """ Remove empty chunks, redundant separators, unite small chunks, split large chunks.
        """
        chunks = []
        for chunk in self.chunks:
            # Remove redundant separators, add separators between consecutive tokens
            tokens = []
            prev_token_was_separator = False
            for t in chunk.tokens:
                if isinstance(t, Token):
                    if not prev_token_was_separator:
                        # Consecutive tokens w/o separator
                        tokens.append(TOKEN_SEP)
                    tokens.append(t)
                    prev_token_was_separator = False
                else:  # is separator
                    if prev_token_was_separator:
                        # rewrite last separator
                        tokens[-1] = t
                    else:
                        tokens.append(t)
                        prev_token_was_separator = True

            # Eliminate first and last stubs
            if len(tokens) > 0 and not isinstance(tokens[0], Token):
                tokens = tokens[1:]
            if len(tokens) > 0 and not isinstance(tokens[-1], Token):
                tokens = tokens[:-1]
            chunk.tokens = tokens
            chunks.append(chunk)

        # Remove empty chunks
        self.chunks = [c for c in chunks if not c.is_empty()]

        # Unite small chunks - to reduce requests to translator
        chunks = []
        cur_len = 0
        cur_chunk = None
        for chunk in self.chunks:
            size = chunk.size()
            if size >= MAX_LENGTH_TEXT_TRANSLATE:  # Split chunk into several smaller ones
                if cur_chunk:
                    # Finalize current chunk
                    chunks.append(cur_chunk)
                    cur_len = 0
                cur_chunk = Chunk()
                for t in chunk.tokens:
                    cur_len += len(t)
                    if cur_len > MAX_LENGTH_TEXT_TRANSLATE and isinstance(t, Token):
                        # Cut last sep and finalize current chunk
                        if len(cur_chunk.tokens) > 0:
                            cur_chunk.tokens.pop()
                        else:
                            # Split the token itself
                            # raise NotImplementedError()
                            print("WARNING: long token to be splitted: %s" % t)
                        chunks.append(cur_chunk)
                        cur_chunk = Chunk()
                        cur_len = len(t)  # FIXME what if 1 token > max len?
                    cur_chunk.tokens.append(t)

                chunks.append(cur_chunk)
                cur_chunk = None
                continue

            if cur_chunk is None:
                cur_chunk = chunk
                cur_len = size
                continue
            cur_len += size + len(TEX_SEP)
            if cur_len > MAX_LENGTH_TEXT_TRANSLATE:
                # Finalize current chunk
                chunks.append(cur_chunk)
                cur_chunk = chunk
                cur_len = size
            else:
                # Concatenate chunk
                cur_chunk.append_stub(TEX_SEP)
                cur_chunk.tokens.extend(chunk.tokens)
        if cur_chunk:
            chunks.append(cur_chunk)

        self.chunks = chunks

    def translate(self):
        """ Translate in-place. """
        for c in self.chunks:
            c.translate()

    def print(self):
        for ix, chunk in enumerate(self.chunks):
            print("Chunk", ix)
            for t in chunk.tokens:
                if isinstance(t, Token):
                    print('***', t.category, t.position)
                    print(t.text)
                else:
                    print('*', t)


def translate_via_texsoup(source_path, output_path, input_lang=SRC_LANG, output_lang=DST_LANG,
                          verbose=False):
    assert input_lang != output_lang
    assert input_lang in checked_langs and output_lang in checked_langs
    with open(source_path, 'r') as f:
        source_text = f.read()

    # FIXME TexSoup has many bugs, see https://github.com/alvinwan/TexSoup/issues
    soup = TexSoup(source_text, tolerance=0)

    chunker = Chunker()

    # TODO \title{} could be outside of document - handle it separately
    # TODO Same for \author{} etc?
    # Parse only '\begin{document} ... \end{document}' part if present
    # to avoid errors while parsing preamble (e.g. \newtheorem{theorem}{} -> \newtheorem{теорема}{})
    document = soup.find('document')
    if document:
        # Insert target language babel package before document
        for i, node in enumerate(soup.contents):
            if hasattr(node, '__match__') and node.__match__('document', attrs={}):
                language = {
                    'ru': 'russian',
                    'en': 'english',
                }[output_lang]
                # FIXME position is guessed. self._content and self.content have different numerations
                soup.insert(i, TexSoup("\n"), TexSoup(r"""\usepackage[%s]{babel}""" % language), TexSoup("\n"))
                break

        chunker.parse_node(document)
    else:
        chunker.parse_node(soup)
    chunker.finalize()
    chunker.translate()
    if verbose:
        chunker.print()

    # TODO post-process text
    # add \usepackage[russian]{babel} (or target lang)
    # replace(u'«', '``')
    # replace(u'»', '\'\'')
    # replace(u'т. Д.', u'т.\\,д.')
    # replace(u'т. П.', u'т.\\,п.')
    # replace(u' - ', u'~--- ')  # shouldn't be used in cases like $x$-abcd

    # Save final text
    with open(output_path, 'w') as f:
        f.write(str(soup))


def main():
    parser = argparse.ArgumentParser(description='Latex document translation via google.translate.')
    parser.add_argument('-i', '--input', required=True, help='input Tex file path')
    parser.add_argument('-o', '--output', default='output.tex', help='output Tex file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='print chunks')
    # parser.add_argument('--leave-original', action='store_true', help='output .tex file path')
    # parser.add_argument('--input-lang', default='en', help='language of input document')
    # parser.add_argument('--output-lang', default='ru', help='language of output document')

    args = parser.parse_args()
    print(args)

    input_path = args.input
    output_path = args.output or '../data/output.tex'

    translate_via_texsoup(input_path, output_path, verbose=args.verbose)


if __name__ == '__main__':
    main()

    # translate_via_texsoup('../data/conference_101719.tex', '../data/final.tex')
    # translate_via_texsoup('../data/pmetemplate03.tex', '../data/final.tex')
