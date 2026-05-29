# ! pip install nltk
from nltk.tokenize import sent_tokenize   #! 句子分词器

import nltk
nltk.download('punkt_tab')

#! 句子分词
def sentence_chunk(text, max_words=150):
    sentences = sent_tokenize(text)
    chunks, buffer, length = [], [], 0

    for sent in sentences:
        count = len(sent.split())
        if length + count > max_words:
            chunks.append(" ".join(buffer))
            buffer, length = [], 0
        buffer.append(sent)
        length += count

    if buffer:
        chunks.append(" ".join(buffer))
    return chunks






if __name__ == "__main__":
    text = """
    这是一个测试句子。它包含多个句子。
    这是第二个句子。
    这是第三个句子。
    这是第四个句子。
    这是第五个句子。
    """
    chunks = sentence_chunk(text, max_words=100)
    print(chunks)