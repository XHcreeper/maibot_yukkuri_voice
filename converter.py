"""将字符串转换为假名
大部分代码逻辑来自于https://github.com/Love-Kogasa/zh-yukkuri.js感谢"""

import json
import os
import regex
from cn2an import an2cn
from e2k import C2K
from pypinyin import lazy_pinyin
from itertools import zip_longest

class Pinyin2Kana:
    def __init__(self, mapping_file):
        self.__mapping_file = mapping_file

    def pinyin2kana(self, pinyin):
        """将拼音转换为假名"""
        result = []
        with open(self.__mapping_file, 'r', encoding='utf-8') as mapping_file:
            pinyin_mapping = json.load(mapping_file)
        for syllable in pinyin.split():
            if syllable in pinyin_mapping:
                result.append(pinyin_mapping[syllable])
        return ''.join(result)

class Converter:
    def __init__(self, map):
        self.pinyin2kana = Pinyin2Kana(map)

    def en2kana(self, string):
        """将英文字符串转换为假名(列表)"""
        c2k = C2K()
        result = []
        split = regex.split(r'([^a-zA-Z]+)', string)
        for i in split:
            result.append(c2k(i))
        return ''.join(result)

    def kanaify(self, string):
        """将拼音转换为假名"""
        str = string
        pinyin_str = lazy_pinyin(str, errors='ignore')
        pinyin_str = ' '.join(pinyin_str)
        result = self.pinyin2kana.pinyin2kana(pinyin_str).replace('\n', ' ').replace('_', '')
        return result

    def number(self, string):
        """将数字转换为中文数字"""

        def replace_number(match):
            num_str = match.group(0)
            try:
                return an2cn(num_str)
            except Exception:
                pass
        return regex.sub(r'-{0,1}\d+(\.\d+){0,1}', replace_number, string)

    def str1kana(self, string):
        """将不包含英文的字符串转换为假名（列表）"""
        str = self.kanaify(self.number(string))
        result = []
        split = regex.split(r'([a-zA-Z]+)', str)
        for i in split:
            result.append(i)
        return ''.join(result)

    def str2kana(self, string):
        """将字符串转换为假名"""
        first = self.str1kana(string)
        second = self.en2kana(string)
        def replace_other(match):
            return match.group(0)
        pattern = r'[^\p{Script=Han}\p{Script=Latin}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}]+'
        result = regex.sub(pattern, replace_other, string)
        result = regex.match(r'([a-zA-Z]+)',string)
        result = result is not None
        if result:
            first = self.en2kana(string)
            second = self.str1kana(string)
        else:
            first = self.str1kana(string)
            second = self.en2kana(string)
        result = []
        for a, b in zip_longest(first, second, fillvalue=''):
            if a != '':
                result.append(a)
            if b != '':
                result.append(b)
        return ''.join(result)

# 测试
if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "mapping.json")
    converter = Converter(file_path)
    test_string = "Kirisame Marisa 我操114514快点端上来罢"
    result = converter.str2kana(test_string)
    print(result)