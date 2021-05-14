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
MAX_LENGTH_TEXT_TRANSLATE = 2000  # limit for google translate at once

MATH_STUB = 'MATH_STUB'  # used to replace math formulas before auto-translation
TEX_STUB = 'TEX_STUB'  # used to replace short Tex commands within one piece of text
TEX_SEP = '\nTEX_SEP\n'  # used to separate pieces of text
TOKEN_SEP = 'TOKEN_SEP'  # used to separate consecutive tokens
NEW_LINE = 'NEW_LINE'  # TODO assert NEW_LINE is not encountered in text

# def preprocess_english_latex(text):
#     """
#     Split into lines and mark each line with a latex type.
#
#     :param text:
#     :return:
#     """
#     content = []  # list of pairs (LatexType, string)
#     last_type = LatexType.newpar
#
#     for line_orig in text.splitlines():
#         line = line_orig.strip()
#
#         if len(line) == 0:
#             # TODO new paragraph
#             last_type = LatexType.newpar
#
#         elif line.startswith('%'):  # comment
#             last_type = LatexType.comment
#
#         elif line.startswith('\\'):  # header or special command
#             if is_header(line):
#                 last_type = LatexType.header
#             else:
#                 last_type = LatexType.special
#
#         elif line[0].isalnum():  # works for English chars only
#             last_type = LatexType.ordinary
#
#         else:
#             print ('unknown type:', line_orig)
#             last_type = LatexType.other
#
#         # add original line
#         content.append((last_type, str(line_orig)))
#         # content.append((last_type, unicode(line_orig, encoding='utf-8')))
#
#     # for t, l in content:
#     #     print '-------'
#     #     print t, l
#     return content
#
#
# def postprocess_russian(text):
#     """
#     Process russian text disregarding latex constructions
#     :param text:
#     :return:
#     """
#
#     # sometimes quotes are replaced
#     text = text.replace(u'«', '``')
#     text = text.replace(u'»', '\'\'')
#
#     text = text.replace(u'т. Д.', u'т.\\,д.')
#     text = text.replace(u'т. П.', u'т.\\,п.')
#
#     # not in math mode: short '-' replace with long '---'
#     text = text.replace(u' - ', u'~--- ')  # shouldn't be used in cases like $x$-abcd
#
#     return text
#
#
# def postprocess_russian_latex(text):
#     """
#     Process russian text regarding latex constructions
#
#     :param text:
#     :return:
#     """
#
#     # replace ~\cite
#     text = text.replace('\\ cite ', '\\cite')
#     text = text.replace(' ~ \\cite', '~\\cite')
#
#     return text


translator = Translator(raise_exception=True)


def google_translate_text(text: str, src_lang=SRC_LANG, dst_lang=DST_LANG) -> str:
    if len(text) > MAX_LENGTH_TEXT_TRANSLATE:
        raise RuntimeError("Text is too long (%s) for google translate (must be < %s): %s" % (
            len(text), MAX_LENGTH_TEXT_TRANSLATE, text))
    # FIXME after several requests it will ban your IP, what about proxies?
    print("Translating text of length %s" % len(text))
    res = translator.translate(text, dest=dst_lang, src=src_lang).text
    # res = t.upper()
    print(res)
    return res


class Chunk:
    def __init__(self):
        self.tokens = []

    def append_token(self, token: Token):
        # TODO which tokens we ignore?
        text = str(token.text)
        ignore = False
        if len(text) == 0 and text in "[]()":
            # Exceptions
            ignore = False
        else:
            # Rules for ignorance
            if len(text) < 3:
                ignore = True
            if sum(c.isalpha() for c in text) < 3:  # FIXME this works for src=en only!
                ignore = True

        # TODO do not ignore: []
        if ignore:
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
                t.text = "%s%s%s" % (
                    " " if len(before) > 0 else "",
                    t.text[start: end or None],
                    " " if len(after) > 0 else "")
                if len(t.text) < 1:
                    print("-1")

                # 2) Handle newlines  # TODO do we want to revert this?
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
        # remove whitespaces around / (Wb/m -> Wb / m)
        # remove extra whitespaces within various quotes (``0,25'' -> `` 0,25 '')
        # ...

        # Split translated text back into tokens
        # TODO assert tokens don't contain stubs besides we put it there
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
    def __init__(self):
        self.chunks = [Chunk()]  # sequence of tokens and stubs lists to translate together

    def parse_node(self, elem: TexNode, chunk=None):
        if chunk is None:
            chunk = self.chunks[-1]
        if isinstance(elem, TexNode):
            # TODO ignore some TexNodes:
            # \color{...}, \begin{thebibliography}{} ...,
            # \label{...}, \cite{...}, +
            # \begin{...}, \end{...}, name=aligned ???
            # \usepackage{...}
            if elem.name in [
                'label', 'cite', 'color', 'thebibliography', 'ref', 'eqref', '$',
                'usepackage', 'addbibresource',  # preamble - do we translate it at all?
                'tabular',  # to prevent translating '&' as 'and'
                'algorithm',  # to prevent translating keywords FIXME some text can be inside?
                'equation',  # to prevent translating keywords FIXME some text can be inside?
                'BraceGroup',  # FIXME check
            ]:
                return

            # Start a new chunk
            new_chunk = Chunk()
            self.chunks.append(new_chunk)
            for e in elem.contents:
                self.parse_node(e, new_chunk)

            if new_chunk.is_empty():
                chunk.append_stub(TEX_STUB)
            else:
                chunk.append_stub(TEX_SEP)

        elif isinstance(elem, Token):
            if 'Figure Labels' in elem.text:
                print('Figure Labels')
            # Append to current chunk
            chunk.append_token(elem)
        # elif isinstance(elem, str):
        #     print('*', elem)  # TODO
        # else:
        #     print('**', type(elem), elem)
        #     # raise ValueError("")

    def finalize(self):
        """ Remove empty chunks, redundant separators, unite small chunks.
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


def translate_via_texsoup(source_path, output_path):
    with open(source_path, 'r') as f:
        source_text = f.read()

    soup = TexSoup(source_text, tolerance=0)

    # Parse only 'document' part if present
    to_parse = soup.find('document') or soup
    chunker = Chunker()
    chunker.parse_node(to_parse)
    chunker.finalize()
    chunker.translate()
    chunker.print()

    # save final text
    with open(output_path, 'w') as f:
        f.write(str(soup))


def main():
    parser = argparse.ArgumentParser(description='Latex document translation via google.translate.')
    parser.add_argument('-i', '--input', required=True, help='input .tex file path')
    parser.add_argument('-o', '--output', default='output.tex', help='output .tex file path')
    # parser.add_argument('--leave-original', action='store_true', help='output .tex file path')
    # parser.add_argument('--input-lang', default='en', help='language of input document')
    # parser.add_argument('--output-lang', default='ru', help='language of output document')

    args = parser.parse_args()

    # Assuming all parameters are provided and take valid values.
    input_path = args.input
    output_path = args.output  # FIXME check
    # leave_orig = args.leave_original

    # source_path = '../data/source.txt'
    # final_path = '../data/final.txt'
    # leave_orig = True

    translate_via_texsoup(input_path, output_path)


if __name__ == '__main__':
    # main()

    # text = "know $2+2=4$~\cite{somepaper}? % comment"
    # print re.findall("\\\[\W]|\\\[a-zA-Z]+|%.+|\$[^$]+\$|\$\$[^$]+\$\$", text)

    # t = Translator().translate('We use the following label propagation algorithm, lets name it Cordv, where X is a number of iterations.', dest='ru', src='en')
    # print(t.text)

    # SIGNATURES.update({
    #     'label': (1, 0),
    #     'cup': (0, 0),
    #     'noindent': (0, 0),
    #     'in': (0, 0),
    #     'bigl': (0, 0),
    #     'bigr': (0, 0),
    #     'left': (0, 0),
    #     'right': (0, 0),
    # })

    # 1. Incorrect parse of mismatch brackets
    # TexSoup(r""" $ \bigl[ \bigl] $""")  # works fine
    # TexSoup(r""" $ \bigl[ \bigl) $""")  # EOFError: [Line: 0, Offset: 11] "$" env expecting $. Reached end of file.
    # A workaround works
    # TexSoup(r""" $ \biggl[ \biggl ) $""")

    # 2. Incorrect parse of \left and \right
    # TexSoup(r""" $ \left[ \right) $""")  # compiles, but TexSoup treats them like 'left[' and 'right)' instead of 'left' and 'right'
    # TexSoup(r""" $ \left[ \right) $""")  # so this also compiles

    # TexSoup(r""" $ \left [ \right ] $""")  # works fine
    # TexSoup(r""" $ \left [ \right ) $""")  # EOFError: [Line: 0, Offset: 13] "$" env expecting $. Reached end of file.
    # A workaround works but
    # soup = TexSoup(r"""$ \cup [0, \infty)$""")  # works fine
    # soup = TexSoup(r""" \begin{equation} \cup [0, \infty) \end{equation}""")  # fails
    # soup = TexSoup(r""" \begin{equation} \bigl[ \bigr) \end{equation}""", tolerance=0)  # fails

    # TexSoup(r"""$S \cup [0, \infty)$""")

    # # source_path = '../data/source.txt'
    source_path = '../data/conference_101719.tex'
    # source_path = '../data/modularity_report.tex'

    translate_via_texsoup(source_path, '../data/final.tex')
