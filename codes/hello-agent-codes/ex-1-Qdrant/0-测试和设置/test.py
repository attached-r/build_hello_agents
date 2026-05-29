from qdrant_client import QdrantClient, models  #? 导入模型模块
import os
import dotenv

dotenv.load_dotenv()

#! 创建客户端
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_CLUSTER_ENDPOINT"), 
    api_key=os.getenv("QDRANT_API_KEY"),
)

collections = qdrant_client.get_collections()
print(collections)


#! 创建集合
collection_name = "my_first_collection"

# Create the collection with specified vector parameters
if collection_name not in [c.name for c in collections.collections]: #?防止重复创建
    qdrant_client.create_collection(

    collection_name=collection_name,
    vectors_config=models.VectorParams(
        size=4,  # Dimensionality of the vectors
        distance=models.Distance.COSINE  # Distance metric for similarity search
      )
    )


#! 插入点
#? 定义要插入的向量 model.PointStruct
points = [
    models.PointStruct(
        id=1,
        vector=[0.1, 0.2, 0.3, 0.4],  # 4D vector
        payload={"category": "example"}  # Metadata (optional)
    ),
    models.PointStruct(
        id=2,
        vector=[0.2, 0.3, 0.4, 0.5],
        payload={"category": "demo"}
    )
]

#? 插入  upsert
if collection_name in [c.name for c in collections.collections]: #?防止重复插入
    qdrant_client.upsert(
      collection_name=collection_name,
      points=points
    )

#? 获取集合信息
# collection_info = qdrant_client.get_collection(collection_name)
# print("Collection info:", collection_info)


#! 相似度搜索
query_vector = [0.08, 0.14, 0.33, 0.28]

search_results = qdrant_client.query_points(
    collection_name=collection_name,
    query=query_vector,
    limit=1  # Return the top 1 most similar vector
)

print("Search results:", search_results)


#! 添加索引 
#? 检查索引是否存在
if("category" not in [i.field_name for i in qdrant_client.get_payload_indices(collection_name)]):
    qdrant_client.create_payload_index(
    collection_name=collection_name,
    field_name="category",
    field_type=models.PayloadSchemaType.KEYWORD,    # 关键词索引
    )


#! 过滤查询
filter = models.Filter(
    should=[
        models.FieldCondition(
            key="category",
            match=models.MatchValue(value="example"),
        )
    ]
)

filter_results = qdrant_client.query_points(
    collection_name=collection_name,
    limit=1,
    query_filter=filter,
)
print("Filter results:", filter_results)
