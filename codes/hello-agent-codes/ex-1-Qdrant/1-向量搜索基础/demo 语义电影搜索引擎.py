from sentence_transformers import SentenceTransformer       #? 句子/文本嵌入
from qdrant_client import QdrantClient, models
from llama_index.embeddings.huggingface import HuggingFaceEmbedding       #? 嵌入模型
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser  #? 文本分词器
from llama_index.core import Document                          #? 用于存储文档
from transformers import AutoTokenizer                       #? 分词器

import os
import dotenv
# Initialize components
encoder = SentenceTransformer("all-MiniLM-L6-v2")  #? 句子/文本嵌入模型

# In-memory for demo: NO HNSW built -> queries are a full scan.

dotenv.load_dotenv()

#! 创建客户端
client = QdrantClient(
    url=os.getenv("QDRANT_CLUSTER_ENDPOINT"), 
    api_key=os.getenv("QDRANT_API_KEY"),
)


#! 创建集合, 包含三个命名向量
# 1. 固定长度向量
# 2. 句子向量
# 3. 语义向量
client.recreate_collection(
    collection_name='movie_search',
    vectors_config={
        'fixed': models.VectorParams(size=384, distance=models.Distance.COSINE),
        'sentence': models.VectorParams(size=384, distance=models.Distance.COSINE),
        'semantic': models.VectorParams(size=384, distance=models.Distance.COSINE),
    },
)

#? 分词器
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
MAX_TOKENS = 40  # 最大分词数

#! 固定长度分词
def fixed_size_chunks(text, size=MAX_TOKENS):
    """Fixed-size chunking: splits at exact token boundaries"""
    tokens = tokenizer.encode(text, add_special_tokens=False)
    return [
        tokenizer.decode(tokens[i:i+size], skip_special_tokens=True)
        for i in range(0, len(tokens), size)
    ]
#! 句子分词
def sentence_chunks(text):
    """Sentence-aware chunking: respects sentence boundaries"""
    splitter = SentenceSplitter(chunk_size=MAX_TOKENS, chunk_overlap=10)
    return splitter.split_text(text)

#! 语义分词
def semantic_chunks(text):
    """Semantic chunking: uses embedding similarity to find natural breaks.
    Note: still constrained by the embed model's context window (same as retrievers)."""
    semantic_splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    )
    nodes = semantic_splitter.get_nodes_from_documents([Document(text=text)])
    return [node.text for node in nodes]



#! 数据处理上传
points = []  
idx = 0  
from movies import documents  as movie_datas

for movie in movie_datas:  # Process each movie
    # Fixed-size chunks
    for chunk in fixed_size_chunks(movie["description"]):
        points.append(models.PointStruct(
            id=idx,
            vector={"fixed": encoder.encode(chunk).tolist()},
            payload={**movie, "chunk": chunk, "chunking": "fixed"}
        ))
        idx += 1

    # Sentence-aware chunks  
    for chunk in sentence_chunks(movie["description"]):
        points.append(models.PointStruct(
            id=idx,
            vector={"sentence": encoder.encode(chunk).tolist()},
            payload={**movie, "chunk": chunk, "chunking": "sentence"}
        ))
        idx += 1

    # Semantic chunks
    for chunk in semantic_chunks(movie["description"]):
        points.append(models.PointStruct(
            id=idx,
            vector={"semantic": encoder.encode(chunk).tolist()},
            payload={**movie, "chunk": chunk, "chunking": "semantic"}
        ))
        idx += 1

client.upload_points(collection_name='movie_search', points=points)
print(f"Uploaded {idx} vectors across three chunking strategies")



#! 比较不同分词策略的搜索结果
def search_and_compare(query, k=3):
    """Compare search results across all three chunking strategies"""
    print(f"Query: '{query}'\n")
    
    for strategy in ['fixed', 'sentence', 'semantic']:
        results = client.query_points(
            collection_name='movie_search',
            query=encoder.encode(query).tolist(),
            using=strategy,
            limit=k,
        )
        
        print(f"--- {strategy.upper()} CHUNKING ---")
        for i, point in enumerate(results.points, 1):
            payload = point.payload
            print(f"{i}. {payload['name']} ({payload['year']}) | Score: {point.score:.3f}")
            print(f"   Chunk: {payload['chunk'][:100]}...")
        print()

# Test with different queries
search_and_compare("alien invasion")
search_and_compare("questioning reality and existence")

"""
流程；实现文本分词 嵌入 上传 搜索
"""