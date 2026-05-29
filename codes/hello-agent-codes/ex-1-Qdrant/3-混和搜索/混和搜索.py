from qdrant_client import QdrantClient,models
from qdrant_client.models import VectorParams

import os
from dotenv import load_dotenv

load_dotenv()


client = QdrantClient(
    url=os.getenv("QDRANT_CLUSTER_ENDPOINT"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
COLLECTION_NAME = "dense_sparse_collection_demo"

DENSE_VECTOR_NAME = "dense_vector_1"
SPARSE_VECTOR_NAME = "sparse_vector_1"

#!  创建一个混合搜索集合
if not client.collection_exists(collection_name=COLLECTION_NAME):
    client.create_collection(
      collection_name=COLLECTION_NAME,
      vectors_config={           #? 稠密向量配置
          DENSE_VECTOR_NAME: VectorParams(
              size=384,
              distance=models.Distance.CosineDistance,
          )
      },
      sparse_vectors_config={    #? 稀疏向量配置
          SPARSE_VECTOR_NAME: models.SparseVectorParams()
      },
      )

#! 插入数据点
if not client.collection_exists(collection_name=COLLECTION_NAME):
  try:  
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=1,
                vector={
                    "dense_vector": [0.1, 0.2, 0.3, 0.4] * 96,  # 示例密集向量
                    "sparse_vector": models.SparseVector(
                        indices=[1, 5, 10],
                        values=[0.2, 0.5, 0.3]
                    )
                },
                payload={"text": "示例1", "category": "example1"}
            ),
            models.PointStruct(
                id=2,
                vector={
                    "dense_vector": [0.4, 0.3, 0.2, 0.1] * 96,  # 示例密集向量
                    "sparse_vector": models.SparseVector(
                        indices=[2, 8, 15],
                        values=[0.3, 0.4, 0.6]
                    )
                },
                payload={"text": "示例2", "category": "example2"}
            ),
        ],
    )
    print("已插入示例数据")
  except Exception as e:
      print(f"插入数据时出错: {e}")


#! 模式一：稠密检索 → 稀疏重排序
query = "这是一个查询"
client.query_points(
    collection_name=COLLECTION_NAME,
    prefetch=[
        models.Prefetch(
            query=models.Document(
                text=query,
                model="sentence-transformers/all-MiniLM-L6-v2",
            ),
            using=DENSE_VECTOR_NAME,
            limit=20,
        ),
    ],
    query=models.Document(
        text=query,
        model="Qdrant/bm25",
    ),
    using=SPARSE_VECTOR_NAME,
    limit=20,
)

#! 模式二：稀疏检索 → 稠密重排序
query = "这是一个查询"
client.query_points(
    collection_name=COLLECTION_NAME,
    prefetch=[
        models.Prefetch(
            query=models.Document(
                text=query,
                model="Qdrant/bm25",
            ),
            using=SPARSE_VECTOR_NAME,
            limit=20,
        ),
    ],
    query=models.Document(
        text=query,
        model="sentence-transformers/all-MiniLM-L6-v2",
    ),
    using=DENSE_VECTOR_NAME,
    limit=20,
)


#! RRF 模式
client.query_points(
    collection_name=COLLECTION_NAME,
    prefetch=[
        models.Prefetch(
            query=models.Document(
                text=query,
                model="sentence-transformers/all-MiniLM-L6-v2",
            ),
            using=DENSE_VECTOR_NAME,
            limit=20,
        ),
        models.Prefetch(
            query=models.Document(
                text=query,
                model="Qdrant/bm25",
            ),
            using=SPARSE_VECTOR_NAME,
            limit=20,
        ),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),  #? 指定RRF 模式
    limit=10,
)