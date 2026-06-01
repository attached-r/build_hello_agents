"""
测试 Neo4j 连接（云端 Aura 版）。

用法:
  & "E:/anaconda3/anaconda/python.exe" testNeo4j.py

环境变量来自 .env（通过 hello_agents.core 自动加载）:
  NEO4J_URI      = neo4j+s://xxx.databases.neo4j.io
  NEO4J_USER     = baf80178
  NEO4J_PASSWORD = ...
  NEO4J_DATABASE = baf80178
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

# ── 方式一：直接用官方驱动连接 ──
print("=" * 60)
print("测试 1: 官方 GraphDatabase 驱动直连")
print("=" * 60)

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")
DATABASE = os.getenv("NEO4J_DATABASE") or None

print(f"  URI:      {URI}")
print(f"  User:     {USER}")
print(f"  Database: {DATABASE or '(default)'}")

try:
    with GraphDatabase.driver(URI, auth=(USER, PASSWORD)) as driver:
        driver.verify_connectivity()
        print("  ✅ verify_connectivity() 通过")

        with driver.session(database=DATABASE) as session:
            result = session.run("RETURN 1 AS ok")
            record = result.single()
            print(f"  ✅ 查询执行成功: RETURN 1 = {record['ok']}")

            # 列出所有数据库
            with driver.session(database="system") as sys_session:
                dbs = sys_session.run("SHOW DATABASES")
                names = [r["name"] for r in dbs]
                print(f"  📚 可用数据库: {names}")

    print("🎉 Neo4j 连接测试通过！\n")

except Exception as e:
    print(f"❌ Neo4j 连接失败: {e}\n")

# ── 方式二：通过 Neo4jGraphStore 连接 ──
print("=" * 60)
print("测试 2: Neo4jGraphStore 封装类")
print("=" * 60)

try:
    from hello_agents.memory.storage.neo4j_store import Neo4jGraphStore

    store = Neo4jGraphStore()
    result = store._run("RETURN 1 AS ok")
    print(f"  ✅ _run 查询成功: {result}")
    print(f"  ✅ 数据库名: {store._database}")

    n = store.count_entities()
    print(f"  📊 当前实体数: {n}")

    store.close()
    print("🎉 Neo4jGraphStore 测试通过！")

except Exception as e:
    print(f"❌ Neo4jGraphStore 连接失败: {e}")
