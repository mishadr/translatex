# coding=utf-8
import argparse
import itertools
import re

from enum import IntEnum

from TexSoup.data import BraceGroup
from googletrans import Translator


# Latex line types
class LatexType(IntEnum):
    ordinary, newpar, comment, header, special, other = range(6)


MATH_STUB = '***'  # used to replace math formulas before auto-translation
TEX_STUB = 'TEX_STUB'  # used to replace short Tex commands within one piece of text
TEX_SEP = '\nTEX_SEP\n'  # used to separate pieces of text
TOKEN_SEP = ' TOKEN_SEP'  # used to separate consecutive tokens, FIXME: space could be removed by translator
# OPEN_QUOTE = '"'  # used to label start of modified text
# CLOSE_QUOTE = '"'  # used to label end of modified text


# def is_header(line):
#     for header in ['\\part', '\\chapter', '\\section', '\\subsection', '\\subsubsection', '\\paragraph', '\\subparagraph']:
#         if line.startswith(header):
#             return True
#     return False
#
#
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
# def cut_math(line):
#     """
#     Replaces all math formulas $...$ and \[ ... \] with math_stubs.
#
#     :param line:
#     :param math_stub:
#     :return:
#     """
#     # TODO add \[ ... \] support
#     math_list = []
#     result = ""
#
#     math_mode = False
#
#     print (line)
#     pieces = re.split(r"(\$)", line)
#     for p in pieces:
#         if p == '$':
#             math_mode = not math_mode
#             continue
#
#         if math_mode:
#             math_list.append("$%s$" % p)
#             result += MATH_STUB
#         else:
#             result += p
#
#     # print result
#     # print math_list
#     return result, math_list
#
#
# def embed_math(text, math_list):
#     """
#
#     :param text:
#     :param math_list:
#     :return:
#     """
#     # FIXME what if len(math_list) != number of stubs?
#     for math in math_list:
#         text = text.replace(MATH_STUB, math, 1)
#
#     # print text
#     return text
#
#
# def translate_en_ru(content, leave_orig):
#     """
#     Translate text by paragraphs, leaving original parts commented if specified.
#
#     :param content: list of pairs (LatexType, string)
#     :param leave_orig: whether to leave original parts of text (will be commented)
#     :return:
#     """
#     result = []
#     line_sep = u'\n'
#     par_sep = u'\n\n'
#     tran_sep = u'\n'  # separator between translation and original
#     orig_comment = u'%'
#
#     par_tran = []  # translated part of paragraph
#     par_orig = []  # original part of paragraph
#
#     translator = Translator()
#
#     def flush_par(par_tran, par_orig, do_translation):
#         if do_translation:  # translate whole paragraph
#             line = u' '.join(par_tran)
#
#             line_wo_math, math_list = cut_math(line)
#             translated = translator.translate(line_wo_math, dest="ru", src="en").text
#             translated = postprocess_russian(translated)
#
#             line_w_math = embed_math(translated, math_list)
#
#             par = postprocess_russian_latex(line_w_math)
#         else:
#             par = line_sep.join(par_tran)
#
#         if leave_orig:
#             par += tran_sep + line_sep.join(par_orig)
#         result.append(par)
#
#     for t, line_orig in content:
#         if t is LatexType.newpar:  # flush current paragraph
#             # TODO do not flush if last type was newpar
#             if len(par_orig) > 0:
#                 flush_par(par_tran, par_orig, True)
#                 par_tran = []
#                 par_orig = []
#
#         elif t is LatexType.comment:  # Comments are ignored for translation
#             par_orig.append(orig_comment + line_orig)
#
#         elif t is LatexType.ordinary:  # Ordinary line we translate as is
#             par_tran.append(line_orig.strip())
#             par_orig.append(orig_comment + line_orig)
#
#         elif t is LatexType.header:  # Try to parse and translate header
#             # TODO Try to parse and translate header
#             # Leave as is
#             line_tran = line_orig
#             par_tran.append(line_tran)
#             par_orig.append(orig_comment + line_orig)
#             flush_par(par_tran, par_orig, False)
#             par_tran = []
#             par_orig = []
#
#         elif t is LatexType.special:  # Leave as is
#             # TODO what if math with slash: \[
#             line_tran = line_orig
#             par_tran.append(line_tran)
#             par_orig.append(orig_comment + line_orig)
#
#         elif t is LatexType.other:  # Leave as is
#             line_tran = line_orig
#             par_tran.append(line_tran)
#             par_orig.append(orig_comment + line_orig)
#
#     flush_par(par_tran, par_orig, True)
#
#     # for line in result:
#     #     print '----new paragraph----'
#     #     print line
#     return par_sep.join(result)
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
#
#
# def main():
#     parser = argparse.ArgumentParser(description='Latex document translation via google.translate.')
#     parser.add_argument('-i', '--input', required=True, help='input .tex file path')
#     parser.add_argument('-o', '--output', default='output.tex', help='output .tex file path')
#     parser.add_argument('--leave-original', action='store_true', help='output .tex file path')
#     # parser.add_argument('--input-lang', default='EN', help='language of input document')
#     # parser.add_argument('--output-lang', default='RU', help='language of output document')
#
#     args = parser.parse_args()
#
#     # Assuming all parameters are provided and take valid values.
#     source_path = args.input
#     final_path = args.output
#     leave_orig = args.leave_original
#
#     # source_path = '../data/source.txt'
#     # final_path = '../data/final.txt'
#     # leave_orig = True
#
#     # read source text
#     with open(source_path, 'r') as f:
#         source_text = f.read()
#
#     # preprocess EN latex text
#     text = preprocess_english_latex(source_text)
#
#     # translate
#     text = translate_en_ru(text, leave_orig)
#
#     # save final text
#     with open(final_path, 'w') as f:
#         f.write(text)
#         # f.write(text.encode('utf-8'))


translator = Translator(raise_exception=True)


def translate_parts_en_ru(pieces: list):
    # FIXME after several requests it will ban your IP, what about proxies?
    # TODO unite several pieces in one request separated with \n\n
    res = []
    print("Translating %s pieces" % len(pieces))
    for t in pieces:
        r = translator.translate(t, dest='ru', src='en').text
        # r = t.upper()
        print(r)
        res.append(r)
    return res


from TexSoup import TexSoup, TexNode
from TexSoup.utils import Token
# from loguru import logger


class Chunk:
    def __init__(self):
        self.tokens = []

    def append_token(self, token: Token):
        # TODO which tokens we ignore?
        text = str(token.text)
        if len(text) < 3:
            return
        if sum(c.isalpha() for c in text) < 3:  # FIXME this works for src=en only!
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
        # tokens list is [Token, *, Token, *, .., Token]
        source_text = ""
        for t in self.tokens:
            if isinstance(t, Token):
                # TODO preprocess text \n\n -> \n etc
                source_text += t.text
            else:
                source_text += t

        dest_text = translate_parts_en_ru([source_text])[0]

        # Parse text
        # TODO assert tokens don't contain stubs besides we put it there
        parts = [dest_text]
        for sep in [TEX_SEP, TEX_STUB, TOKEN_SEP]:
            parts = itertools.chain.from_iterable([p.split(sep) for p in parts])
        parts = list(parts)

        assert 2*len(parts)-1 == len(self.tokens)
        ix = 0
        for t in self.tokens:
            if isinstance(t, Token):
                t.text = parts[ix]
                ix += 1


class Chunker:
    def __init__(self):
        self.chunks = [Chunk()]  # sequence of tokens and stubs lists to translate together

    def parse_node(self, elem: TexNode, chunk=None):
        if chunk is None:
            chunk = self.chunks[-1]
        if isinstance(elem, TexNode):
            # names.add(elem.name)

            # embed: $..$, \textit{..}, etc
            # if text modifier - add to current chunk with quotes
            # if elem.name in ['textit']:
            #     # TODO add all modifiers, custom ones?
            #     chunk.append_stub(OPEN_QUOTE)
            #     # TODO what if several embedded modifiers?
            #     for e in elem.contents:
            #         self.parse_node(e, chunk)
            #     chunk.append_stub(CLOSE_QUOTE)

            # TODO where to start a new chunk?

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
        #     print('*', elem)
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
            # Remove redundant separators
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
        max_len = 2000
        chunks = []
        cur_len = 0
        cur_chunk = None
        for chunk in self.chunks:
            size = chunk.size()
            if cur_chunk is None:
                cur_chunk = chunk
                cur_len = size
                continue
            cur_len += size + len(TEX_SEP)
            if cur_len > max_len:
                # Finalize current chunk
                chunks.append(cur_chunk)
                cur_chunk = chunk
                cur_len = size
            else:
                # Concatenate chunk
                cur_chunk.append_stub(TEX_SEP)
                cur_chunk.tokens.extend(chunk.tokens)
        chunks.append(cur_chunk)

        self.chunks = chunks

    def translate(self):
        """ Translate in-place. """
        # Prepare tokens for translation
        # Handle newlines  # FIXME it's how to revert this?
        NEW_LINE = 'NEW_LINE'
        for chunk in self.chunks:
            for t in chunk.tokens:
                if isinstance(t, Token):
                    t.text = t.text.replace('\n\n', NEW_LINE).replace('\n', ' ').replace(NEW_LINE, '\n')

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


def translate_via_texsoup():
    # read source text
    # source_path = '../data/source.txt'
    source_path = '../data/conference_101719.tex'
    with open(source_path, 'r') as f:
        source_text = f.read()

    soup = TexSoup(source_text)

    # # Tokens from special parts of text
    # tokens = []
    # for name in ['section', 'section*', 'subsection', 'subsection*',
    #              'caption', 'title']:  # TODO how to get them all? use names set
    #     for s in soup.find_all(name):
    #         for t in s.contents:
    #             if isinstance(t, Token):
    #                 tokens.append(t)

    # What to parse
    to_parse = soup.find('document')
    if to_parse is None:
        to_parse = soup
    chunker = Chunker()
    chunker.parse_node(to_parse)
    chunker.finalize()
    chunker.translate()
    chunker.print()

    # save final text
    final_path = '../data/final.tex'
    with open(final_path, 'w') as f:
        f.write(str(soup))


if __name__ == '__main__':
    # main()
    # text = "know $2+2=4$~\cite{somepaper}? % comment"
    # print re.findall("\\\[\W]|\\\[a-zA-Z]+|%.+|\$[^$]+\$|\$\$[^$]+\$\$", text)

    # t = Translator().translate('We use the following label propagation algorithm, lets name it Cordv, where X is a number of iterations.', dest='ru', src='en')
    # print(t.text)

    translate_via_texsoup()
