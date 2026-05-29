from qdrant_client import QdrantClient,models
from qdrant_client.models import VectorParams

import os
from dotenv import load_dotenv

load_dotenv()


client = QdrantClient(
    url=os.getenv("QDRANT_CLUSTER_ENDPOINT"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


COLLECTION_NAME = "sparse_vector_demo"

SPARSE_VECTOR_NAME = "sparse_vector"

#! 创建稀疏向量集合 并给稀疏向量 命名
if not client.collection_exists(collection_name=COLLECTION_NAME):
  client.create_collection(
      collection_name=COLLECTION_NAME,
      sparse_vectors_config={
          SPARSE_VECTOR_NAME: models.SparseVectorParams()
      },
      )

#! 插入稀疏向量
try:
    client.upsert(
      collection_name=COLLECTION_NAME,
      points=[
          models.PointStruct(
              id=1,
              vector={SPARSE_VECTOR_NAME: models.SparseVector(
                  indices=[1,2,3], 
                  values=[0.2,-0.2,0.2]
              )}
          ),
          models.PointStruct(
              id=2,
              vector={SPARSE_VECTOR_NAME: models.SparseVector(
                  indices=[1,5], 
                  values=[0.2,0.1]
              )}
          ),
      ],
    )
except Exception as e:
    print(e)


#! 搜索稀疏向量
researchs = client.query_points(
    collection_name=COLLECTION_NAME,
    using=SPARSE_VECTOR_NAME,
    query=models.SparseVector(indices=[1,3], values=[1,1]),
    limit=2
)


print(researchs)