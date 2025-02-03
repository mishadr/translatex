import asyncio
import itertools
import json
import logging
import re

from pylatexenc.latexwalker import LatexCharsNode

from parser import Chunk

SUPPORTED_LANGS = ['en', 'ru']
SRC_LANG = 'en'
DST_LANG = 'ru'


class GenTranslator:
    max_text_length = 2000  # limit to request translator at once

    CHUNK_SEP = '\n{CH4NK_SEP%s}\n'  # used to separate chunks
    TOKEN_SEP = ' {{T0KEN5EP%s}}'  # used to separate consecutive tokens

    CHUNK_SEP_PAT = re.compile('\n?\{CH4NK_SEP\d+\}\n?')  # FIXME only for russian
    TOKEN_SEP_PAT = re.compile('(?:\{|\(|_BOS_)\{T0KEN5EP\d+\}\} ?')

    def __init__(self, chunks, src_lang=SRC_LANG, dst_lang=DST_LANG, verbose=True):
        self.chunks = chunks
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.verbose = verbose

        self.ctr = 0  # Count chunk separators
        self.prepare()

    def prepare(self):
        """ Split chunks to requests. Mask non-translatable """
        # Add token separators
        for chunk in self.chunks:
            tokens = [chunk.tokens[0]]
            for t in chunk.tokens[1:]:
                tokens.append(self.TOKEN_SEP % self.ctr)
                self.ctr += 1
                tokens.append(t)
            chunk.tokens = tokens

        # Split large chunks
        chunks = []
        for chunk in self.chunks:
            parts = chunk.split_if_large(self.max_text_length)
            chunks.extend(parts)
        self.chunks = chunks

        # Unite small chunks - to reduce requests to translator
        self.ctr = 0
        chunks = []
        cur_len = 0
        cur_chunk = None
        for chunk in self.chunks:
            size = chunk.estimated_size()
            assert size < self.max_text_length

            if cur_chunk is None:
                cur_chunk = chunk
                cur_len = size
                continue

            cur_len += size + len(self.CHUNK_SEP)+4
            if cur_len > self.max_text_length:
                # Finalize current chunk
                chunks.append(cur_chunk)
                cur_chunk = chunk
                cur_len = size
            else:
                # Concatenate chunk
                cur_chunk.append_stub(self.CHUNK_SEP % self.ctr)
                self.ctr += 1
                cur_chunk.tokens.extend(chunk.tokens)

        if cur_chunk:
            chunks.append(cur_chunk)

        self.chunks = chunks
        print("Prepared for translation. Chunks:", len(self.chunks))

    def translate(self):
        for ix, c in enumerate(self.chunks):
            print("Translating %s of %s text of length %s via %s" % (
                ix, len(self.chunks), c.estimated_size(), self.translator.__class__.__name__))
            self.translate_chunk(c)

    def translate_chunk(self, chunk: Chunk):
        plain_text, spaces_before, spaces_after = chunk.to_text()

        # Translate plain text
        dest_text = self.translate_text(plain_text)

        if self.verbose:
            print("Original text\n---\n")
            print(plain_text)
            print("\n---\nTranslated text\n---\n")
            print(dest_text)
            print("\n---\n")

        # Split translated text back into tokens
        parts = [dest_text]
        for sep in [self.CHUNK_SEP_PAT, self.TOKEN_SEP_PAT]:
            parts = itertools.chain.from_iterable([sep.split(p) for p in parts])
        parts = list(parts)

        # We suppose tokens list was [Token, *, Token, *, .., Token]
        if 2*len(parts)-1 != len(chunk.tokens):
            def find_several_patterns(text: str, patterns: list) -> list:
                """ Find all matches for a list of patterns, sorted by the occurrence order.
                """
                get_num = re.compile('\d+')
                all_matches = []
                for p in patterns:
                    for m in re.finditer(p, text):
                        all_matches.append((m.regs[0], m.group()))
                all_matches.sort()
                return [get_num.findall(m[1])[-1] for m in all_matches]

            # FInd the 1st token with a problem and split on it.
            original_stubs = find_several_patterns(plain_text, [self.CHUNK_SEP_PAT, self.TOKEN_SEP_PAT])
            found_stubs = find_several_patterns(dest_text, [self.CHUNK_SEP_PAT, self.TOKEN_SEP_PAT])
            mismatch_ix = 0
            while mismatch_ix < min(len(original_stubs), len(found_stubs)):
                if found_stubs[mismatch_ix] != original_stubs[mismatch_ix]:
                    break
                mismatch_ix += 1
            logging.warning(f"Stubs in the translation can't be matched. "
                            f"Splitting chunk at index {mismatch_ix} and trying again. ")
            mismatch_ix = 2 * mismatch_ix + 1
            chunk1, chunk2 = chunk.split_by_token(mismatch_ix)
            self.translate_chunk(chunk1)
            self.translate_chunk(chunk2)
            logging.warning(f"Manually check the result around '{chunk1[-1]} "
                            f"<latex symbols> {chunk2[0]}'")
            return

            # logging.error(f"Couldn't build after translation.")
            # if not self.verbose:
            #     print("Original text\n")
            #     print(plain_text)
            #     print("\nTranslated text\n")
            #     print(dest_text)

        ix = 0
        # assert order is OK
        for t in chunk.tokens:
            if isinstance(t, LatexCharsNode):
                t.chars = spaces_before[ix] + parts[ix].strip() + spaces_after[ix]
                ix += 1

    def translate_text(self, text: str, src_lang=None, dst_lang=None) -> str:
        # if len(text) > self.max_text_length:
        #     raise RuntimeError("Text is too long (%s) for translator (must be < %s)."
        #                        "The text was: '%s'" % (
        #                            len(text), self.max_text_length, text))
        # FIXME after several frequent requests it will ban your IP, what about proxies?
        # res = text.upper()
        res = self._translate(text, src_lang or self.src_lang, dst_lang or self.dst_lang)
        return res

    def _translate(self, text: str, src_lang, dst_lang):
        raise NotImplementedError


class GoogleTranslate(GenTranslator):
    """ Based on Google translate API
    """
    version = None

    def __init__(self, *args, **kwargs):

        import googletrans
        if googletrans.__version__ != self.version:
            raise ImportError(
                f"googletrans lib should be of version '{self.version}' while the installed is"
                f" '{googletrans.__version__}")
        super().__init__(*args, **kwargs)


class GoogleTranslate3(GoogleTranslate):
    """ Using googletrans version 3 """
    version = "3.1.0a0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from googletrans import Translator
        self.translator = Translator(raise_exception=True)

    def _translate(self, text: str, src_lang, dst_lang) -> str:
        return self.translator.translate(text, dest=dst_lang, src=src_lang).text


class GoogleTranslate4(GoogleTranslate):
    """ Using googletrans version 4 """
    version = "3.4.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from googletrans import Translator
        self.translator = Translator(raise_exception=True, service_urls=['translate.google.com'])

    async def async_translate(self, text: str, src_lang, dst_lang):
        self.translator.client_type = 'gtx'
        result = await self.translator.translate(text, dest=dst_lang, src=src_lang)
        return result.text

    def _translate(self, text: str, src_lang, dst_lang) -> str:
        result = asyncio.run(self.async_translate(text, src_lang, dst_lang))
        return result


class GoogleTranslateProxy(GoogleTranslate):
    """
    Uses service_url 'clients5.google.com/translate_a/t'
    """
    version = "3.1.0a0"

    CHUNK_SEP_PAT = re.compile('\n?\{(?i:CH4NK_SEP)\d+\}\n?')
    TOKEN_SEP_PAT = re.compile('\{\{(?i: ?T0KEN5EP)\d+\}\} ?')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        import googletrans
        assert googletrans.__version__ == "3.1.0-alpha"
        from googletrans import Translator, urls, LANGUAGES, LANGCODES
        from googletrans.constants import SPECIAL_CASES
        from googletrans.models import Translated

        class MyTranslator(Translator):
            service_urls = ['clients5.google.com/translate_a/t']

            def _translate(self, text: str, dest: str, src: str):
                # url = urls.TRANSLATE_RPC.format(host=self._pick_service_url())
                url = 'https://clients5.google.com/translate_a/t'
                data = {
                    'q': text,
                }
                params = {
                    'client': 'dict-chrome-ex',
                    'sl': src,
                    'tl': dest,
                    'q': text
                }
                r = self.client.post(url, params=params, data=data)

                if r.status_code != 200 and self.raise_Exception:
                    raise Exception('Unexpected status code "{}" from {}'.format(
                        r.status_code, self.service_urls))

                return r.text, r

            def translate(self, text: str, dest='en', src='auto'):
                dest = dest.lower().split('_', 1)[0]
                src = src.lower().split('_', 1)[0]

                if src != 'auto' and src not in LANGUAGES:
                    if src in SPECIAL_CASES:
                        src = SPECIAL_CASES[src]
                    elif src in LANGCODES:
                        src = LANGCODES[src]
                    else:
                        raise ValueError('invalid source language')

                if dest not in LANGUAGES:
                    if dest in SPECIAL_CASES:
                        dest = SPECIAL_CASES[dest]
                    elif dest in LANGCODES:
                        dest = LANGCODES[dest]
                    else:
                        raise ValueError('invalid destination language')

                origin = text
                data, response = self._translate(text, dest, src)

                data = json.loads(data)
                translated = data[0]

                if isinstance(translated, list):
                    translated = ''.join(translated)
                result = Translated(src=src, dest=dest, origin=origin,
                                    text=translated,
                                    pronunciation=None,
                                    # parts=None,
                                    extra_data=None,
                                    response=response)
                return result

        self.translator = MyTranslator(raise_exception=True)

    def _translate(self, text: str, src_lang, dst_lang) -> str:
        return self.translator.translate(text, dest=dst_lang, src=src_lang).text


class CustomTranslator(GenTranslator):
    """ Using googletrans version 4 """

    def __init__(self, *args, **kwargs):

        # Bad quality
        # from translatepy.translators.reverso import ReversoTranslate as tr
        # from translatepy.translators.libre import LibreTranslate as tr
        # Bad quality via API
        # from translatepy.translators.google import GoogleTranslate as tr

        # Errors
        # from translatepy.translators.microsoft import MicrosoftTranslate as tr

        # OK, but strict limit
        # from translatepy.translators.mymemory import MyMemoryTranslate as tr

        # Very good but strong request limits
        # from translatepy.translators.deepl import DeeplTranslate as tr

        # Good, but problems with patterns sometimes
        from translatepy.translators.yandex import YandexTranslate as tr
        self.max_text_length = 5000

        # OK, but max 200 words per request
        # from translatepy.translators.translatecom import TranslateComTranslate as tr
        # self.TOKEN_SEP = ' __TOKENSEP%s__'

        super().__init__(*args, **kwargs)
        self.translator = tr()

    def _translate(self, text: str, src_lang, dst_lang) -> str:
        res = self.translator.translate(
            text, destination_language=dst_lang, source_language=src_lang)
        return res.result


if __name__ == '__main__':
    text = """
This proof only uses Lemma {{CH4NK_SEP23}}, which provides a relation between the residuals {{T0KEN5EP159}} and {{T0KEN5EP160}}. It repeats the corresponding proof in the real case. For completeness we present this proof here. It is clear that it suffices to consider the case  {{T0KEN5EP161}}. Otherwise,  {{T0KEN5EP162}}. Also, assume  {{T0KEN5EP163}} (otherwise Theorem {{T0KEN5EP164}} holds trivially). Then, by Remark {{T0KEN5EP165}} we have  {{T0KEN5EP166}} for all  {{T0KEN5EP167}}. By Lemma {{T0KEN5EP168}} we obtain  {{T0KEN5EP169}} We choose {{T0KEN5EP170}} from the equation  {{T0KEN5EP171}} which implies that  {{T0KEN5EP172}} Define  {{T0KEN5EP173}} Using notation  {{T0KEN5EP174}}, we deduce from {{T0KEN5EP175}}
Raising both sides of this inequality to  {{CH4NK_SEP25}} power {{T0KEN5EP177}} and taking into account the inequality  {{T0KEN5EP178}} for  {{T0KEN5EP179}}, we obtain  {{T0KEN5EP180}} We shall need the following simple lemma, different versions of which are well known (see, for example, {{T0KEN5EP181}} We use Lemma {{T0KEN5EP182}} for  {{T0KEN5EP183}}. Using the estimate  {{T0KEN5EP184}}, we set  {{T0KEN5EP185}}. We specify  {{T0KEN5EP186}}. Then {{T0KEN5EP187}} guarantees that we can apply Lemma {{T0KEN5EP188}}. Note that  {{T0KEN5EP189}}. Then Lemma {{T0KEN5EP190}} gives  {{T0KEN5EP191}} which implies that  {{T0KEN5EP192}} Theorem {{T0KEN5EP193}} is proved. 
"""
    # from translatepy import Translator
    # # from translatepy.translators.translatecom import TranslateComTranslate as tr
    # from translatepy.translators.yandex import YandexTranslate as tr
    # translator = tr()
    # res = translator.translate(text, "Russian")
    # print(res.result)

    # ms = re.finditer(CustomTranslator.TOKEN_SEP_PAT, text)
    # print(find_several_patterns(text, [CustomTranslator.TOKEN_SEP_PAT, CustomTranslator.CHUNK_SEP_PAT]))

