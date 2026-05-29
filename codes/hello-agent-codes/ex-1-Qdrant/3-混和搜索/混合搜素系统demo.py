from qdrant_client import QdrantClient,models
from qdrant_client.models import VectorParams

import uuid
import os
from dotenv import load_dotenv

load_dotenv()


client = QdrantClient(
    url=os.getenv("QDRANT_CLUSTER_ENDPOINT"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


#! 创建混合搜索集合
collection_name = "hybrid_search_demo"

# Create our collection with both sparse (bm25) and dense vectors
if not client.collection_exists(collection_name=collection_name):
    client.create_collection(
    collection_name=collection_name,
    vectors_config={
        "dense": models.VectorParams(
            distance=models.Distance.COSINE,
            size=384,
        ),
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(
            modifier=models.Modifier.IDF        #? IDF修改器 逆文档频率加权
        )
    }
)


#! 上传数据

documents = [
    "Aged Gouda develops a crystalline texture and nutty flavor profile after 18 months of maturation.",
    "Mature Gouda cheese becomes grainy and develops a rich, buttery taste with extended aging.",
    "Brie cheese features a soft, creamy interior surrounded by an edible white rind.",
    "This French cheese has a flowing, buttery center encased in a bloomy white crust.",
    "Fresh mozzarella pairs beautifully with ripe tomatoes and basil leaves.",
    "Classic Margherita pizza topped with tomato sauce, mozzarella, and fresh basil.",
    "Parmesan requires at least 12 months of cave aging to develop its signature sharp taste.",
    "Parmigiano-Reggiano's distinctive piquant flavor comes from extended maturation in controlled environments.",
    "Grilled cheese sandwiches are the ultimate American comfort food for cold winter days.",
    "Croque Monsieur combines ham and Gruyère in France's answer to the toasted cheese sandwich.",
]



try:
  client.upsert(
      collection_name=collection_name,
      points=[
          models.PointStruct(
              id=uuid.uuid4().hex,
              vector={
                  "dense": models.Document(
                      text=doc,
                      model="sentence-transformers/all-MiniLM-L6-v2",  #? 密度模型将句子转换为稠密向量
                  ),
                  "sparse": models.Document(
                      text=doc,
                      model="Qdrant/bm25",                            #? 稀疏模型将句子转换为稀疏向量
                  ),
              },
              payload={"text": doc},
          )
          for doc in documents
      ]
  )
  print("数据上传成功")
except Exception as e:
  print(f"数据上传失败: {e}")



#! 辅助搜索函数

#? 密度搜索
def dense_search(query: str) -> list[models.ScoredPoint]:
    response = client.query_points(
        collection_name=collection_name,
        query=models.Document(            #? 查询文档 将查询句子转换为稠密向量搜索
            text=query,
            model="sentence-transformers/all-MiniLM-L6-v2",
        ),
        using="dense",
        limit=3,
    )
    return response.points

#? 稀疏搜索
def sparse_search(query: str) -> list[models.ScoredPoint]:
    response = client.query_points(
        collection_name=collection_name,
        query=models.Document(
            text=query,
            model="Qdrant/bm25",
        ),
        using="sparse",
        limit=3,
    )
    return response.points


#! 测试搜索
queries = [
    "nutty aged cheese",
    "soft French cheese",
    "pizza ingredients",
    "a good lunch",
]

for query in queries:
    print("Query:", query)

    dense_results = dense_search(query)
    print("Dense Results:")
    for result in dense_results:
        print("\t-", result.payload["text"], result.score)

    sparse_results = sparse_search(query)
    print("Sparse Results:")
    for result in sparse_results:
        print("\t-", result.payload["text"], result.score)
    print()



#! RRF 混合搜索
def rrf_search(query: str) -> list[models.ScoredPoint]:
    response = client.query_points(
        collection_name=collection_name,
        prefetch=[
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="Qdrant/bm25",
                ),
                using="sparse",
                limit=3,
            ),
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="sentence-transformers/all-MiniLM-L6-v2",
                ),
                using="dense",
                limit=3,
            )
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=3,
    )
    return response.points


for query in queries:
    print("Query:", query)

    rrf_results = rrf_search(query)
    print("RRF Results:")
    for result in rrf_results:
        print("\t-", result.payload["text"], result.score)
    print()




#! DBSF 混合搜索
def dbsf_search(query: str) -> list[models.ScoredPoint]:
    response = client.query_points(
        collection_name=collection_name,
        prefetch=[
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="Qdrant/bm25",
                ),
                using="sparse",
                limit=3,
            ),
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="sentence-transformers/all-MiniLM-L6-v2",
                ),
                using="dense",
                limit=3,
            )
        ],
        query=models.FusionQuery(fusion=models.Fusion.DBSF),
        limit=3,
    )
    return response.points

for query in queries:
    print("Query:", query)

    dbsf_results = dbsf_search(query)
    print("DBSF Results:")
    for result in dbsf_results:
        print("\t-", result.payload["text"], result.score)
    print()


