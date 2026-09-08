"""Deterministic dictionary filtering; no AI, network, OCR or input automation."""
import re
import unicodedata

# Small original starter list, not a game's official or complete dictionary.
DEFAULT_WORDS=tuple(sorted(set('''airplane apple arm banana bear bed bee bicycle bird book bottle box bread bridge bus butterfly cake camera car cat chair cheese cherry clock cloud coat cookie cow crown cup dog dolphin door dragon duck eagle elephant eye face fan fire fish flag flower fork frog giraffe glass glove goat grape guitar hammer hand hat helicopter horse house ice island jacket key king kite ladder lamp leaf lemon lion lock moon mountain mouse mushroom nose ocean orange owl panda pants pen pencil penguin phone piano pig pizza plane plate potato rabbit radio rain rainbow ring robot rocket rose sandwich school scissors shark sheep shoe snake snow snowman sock sofa spider spoon star strawberry sun table taxi tiger tomato train tree truck umbrella violin volcano wall water whale wheel window wolf zebra'''.split())))


def normalize(text):
    return unicodedata.normalize('NFC',text).casefold().strip()


def load_words(path):
    if path.stat().st_size>2_000_000:raise ValueError('The word list can be at most 2 MB.')
    text=path.read_text(encoding='utf-8-sig')
    words=set()
    for line in text.splitlines():
        word=normalize(line)
        if not word or word.startswith('#'):continue
        if len(word)>80 or not all(c.isalpha() or c in " -'" for c in word):
            raise ValueError('Use UTF-8, one word/phrase per line, without digits or punctuation other than hyphens/apostrophes.')
        words.add(word)
        if len(words)>100000:raise ValueError('Up to 100,000 words are supported.')
    if not words:raise ValueError('The word list is empty.')
    return tuple(sorted(words))


def find_candidates(words,pattern='',length=''):
    pattern=normalize(pattern);length=str(length).strip()
    if not pattern and not length:raise ValueError('Enter a letter count or a pattern such as c__t.')
    count=None
    if length:
        if not length.isdecimal() or not 1<=int(length)<=80:raise ValueError('Letter count must be 1–80.')
        count=int(length)
    if len(pattern)>80 or any(not(c.isalpha() or c in "_? -'") for c in pattern):
        raise ValueError('Pattern: letters, _ or ?, spaces, hyphens and apostrophes.')
    pattern_count=sum(c.isalpha() or c in '_?' for c in pattern)
    if pattern and count is not None and pattern_count!=count:
        raise ValueError('The pattern letter count does not match the length. Spaces are not counted.')
    matcher=re.compile(''.join('[^\\W\\d_]' if c in '_?' else re.escape(c) for c in pattern)) if pattern else None
    result=[]
    for word in words:
        if count is not None and sum(c.isalpha() for c in word)!=count:continue
        if matcher is not None and matcher.fullmatch(word) is None:continue
        result.append(word)
    return sorted(set(result))
