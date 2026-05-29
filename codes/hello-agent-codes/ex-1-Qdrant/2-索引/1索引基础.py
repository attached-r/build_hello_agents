from qdrant_client.models import HnswConfig
from qdrant_client import QdrantClient, models
import os
from dotenv import load_dotenv
import random

load_dotenv()


#! 索引配置示例
#? 图连通性 m
# Lower recall, less memory, faster build
fast_config = HnswConfig(m=8, ef_construct=100, full_scan_threshold=10000)  

# Default - good balance    
balanced_config = HnswConfig(m=16, ef_construct=100, full_scan_threshold=10000) 

# Better recall, more memory, slower build
accurate_config = HnswConfig(m=32, ef_construct=100, full_scan_threshold=10000) 


#! 创建 playload 索引

client = QdrantClient(
    url=os.getenv("QDRANT_CLUSTER_ENDPOINT"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


collection_name = "playload_index_demo"
vector_size = 768

if client.collection_exists(collection_name=collection_name):
    client.delete_collection(collection_name=collection_name)

client.create_collection(
    collection_name=collection_name,
    vectors_config=models.VectorParams(
        size=vector_size,
        distance=models.Distance.COSINE,               #? 余弦相似度
        # hnsw_config=balanced_config,                     #? HNSW 配置
    ),
    optimizers_config=models.OptimizersConfigDiff(     #? 索引优化器配置
        indexing_threshold=100,                        #? 索引阈值
    ),
)
#! 给playload 添加索引
# Index frequently filtered fields
client.create_payload_index(
    collection_name=collection_name,
    field_name="category",
    field_schema=models.PayloadSchemaType.KEYWORD,
)

client.create_payload_index(
    collection_name=collection_name,
    field_name="price",
    field_schema=models.PayloadSchemaType.FLOAT,
)

client.create_payload_index(
    collection_name=collection_name,
    field_name="brand",
    field_schema=models.PayloadSchemaType.KEYWORD,
)


#! 添加测试数据
points = []
for i in range(1000):
    points.append(
        models.PointStruct(
            id=i,
            vector=[random.random() for _ in range(vector_size)],
            payload={
                "category": random.choice(["laptop", "phone", "tablet"]),
                "price": random.randint(0, 1000),
                "brand": random.choice(
                    ["Apple", "Dell", "HP", "Lenovo", "Asus", "Acer", "Samsung"]
                ),
            },
        )
    )

try:  #? 事务操作
    client.upload_points(
        collection_name=collection_name,
        points=points,
    )
except Exception as e:
    print(e)


#! 搜索过滤 测试数据
# Create filter combining multiple conditions
filter_conditions = models.Filter(
    must=[
        models.FieldCondition(key="category", match=models.MatchValue(value="laptop")),
        models.FieldCondition(key="price", range=models.Range(lte=1000)),
        models.FieldCondition(key="brand", match=models.MatchAny(any=["Apple", "Dell", "HP"])),
    ]
)

query_vector = [random.random() for _ in range(vector_size)]

# Execute filtered search
results = client.query_points(
    collection_name=collection_name,
    query=query_vector,
    query_filter=filter_conditions,
    limit=10,
    search_params=models.SearchParams(hnsw_ef=128),    #? HNSW 搜索参数 ef 候选数
)


print(results)
