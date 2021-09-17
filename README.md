# Before You Start

Apple-peeler was written using python 3.9 (but it should be trivial to support earlier versions of python 3.5+).

# Installation

    pip install apple-peeler

# Dependencies

[BeautifulSoup 4](https://beautiful-soup-4.readthedocs.io/en/latest/), [lxml](https://lxml.de), and [click](https://click.palletsprojects.com/en/8.0.x/)

# Usage

Apple likes to move around the dictionaries location from macOS version to macOS version. So if the dictionaries are no longer at the path below you can tell `apple-peeler` where to look by exporting `DICT_BASE` in your environment or using the `--base` option below.

    export DICT_BASE="/System/Library/AssetsV2/com_apple_MobileAsset_DictionaryServices_dictionaryOSX/"

After that, useage is straightforward.

    Usage: apple-peeler [OPTIONS]

    Extract XML from Apple Dictionary files.

    Options:
    --base DIRECTORY                The root directory of the OS X dictionaries.
                                    (Default: /System/Library/AssetsV2/com_apple
                                    _MobileAsset_DictionaryServices_dictionaryOS
                                    X/) [Env var DICT_BASE]
    --out DIRECTORY                 The path to place extracted XML files.
    -d, --dictionary [
        all|Arabic - English|Danish|Duden Dictionary Data Set I|Dutch|
        Dutch - English|French|French - English|French - German|German - English|
        Hebrew|Hindi|Hindi - English|Indonesian - English|Italian|
        Italian - English|Korean|Korean - English|New Oxford American Dictionary|
        Norwegian|Oxford American Writer's Thesaurus|
        Oxford Dictionary of English|Oxford Thesaurus of English|
        Polish - English|Portuguese|Portuguese - English|Russian|
        Russian - English|Sanseido Super Daijirin|
        Sanseido The WISDOM English-Japanese Japanese-English Dictionary|
        Simplified Chinese - English|Simplified Chinese - Japanese|Spanish|
        Spanish - English|Swedish|Thai|Thai - English|
        The Standard Dictionary of Contemporary Chinese|Traditional Chinese|
        Traditional Chinese - English|Turkish|Vietnamese - English]
                                    The dictionary to extract or 'all'.
                                    (Default: all) [Accepts multiple]
    --format-xml / --no-format-xml  Format the XML files using BeautifulSoup.
                                    (Default: False)
    --debug                         Output debug information to STDERR.
                                    (Default: False)
    --help                          Show this message and exit.

## Introduction

I need a ton of dictionary data for prototyping my learning a language tool, [Parsnip](https://solarmist.net/), and licensing 40 dictionaries seems too expensive for a bootstrapper working on an MVP (I look forward to the day this is no longer true).

Parsnip uses Natural Language Processing and Dictionaries to decouple the word <-> sentence tug-of-war that's existed as long as flashcards have been used for language learning. I.e., should I make a word (concept) or a sentence (example) flashcard?

I care about what words I know for tracking purposes, but I want those words in context when I'm practicing. So the learning system breaks down sentences into lemmas (or dictionary form of a word) and a database of example sentences that the words appear in. This resolves the conceptual tug-of-war for flashcards.

But by removing reference data from the flashcards themselves, I need to integrate reference material directly into Parsnip's UI. [JMDict](https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project) is a great open source project for this, but that only covers a single language. So, I've been keeping my eyes open for people working on extracting the data from Apple's bundled dictionaries.

This has been a community effort that's spanned several years. My contribution is to collect the results, clear up some details about the file format, and package it into a general command-line tool.

## References

This is inspired by
[Reverse-Engineering Apple Dictionary](https://fmentzer.github.io/posts/2020/dictionary/).
And the discussion on Hacker News
[Hacker News: Reverse-Engineering Apple Dictionary (2020)](https://news.ycombinator.com/item?id=28505406). Special thanks to tim-- and enragedcacti who introduced me to `binwalk`. And dunham who mentioned the random bytes looking like `int`s of payload sizes.

Additionally, I've found these posts informative:

- https://developer.apple.com/library/archive/documentation/UserExperience/Conceptual/DictionaryServicesProgGuide/prepare/prepare.html#//apple_ref/doc/uid/TP40006152-CH3-SW7
- https://jadedtuna.github.io/apple-dictionary/
- https://josephg.com/blog/reverse-engineering-apple-dictionaries/
- https://josephg.com/blog/apple-dictionaries-part-2/
- https://gist.github.com/josephg/5e134adf70760ee7e49d
