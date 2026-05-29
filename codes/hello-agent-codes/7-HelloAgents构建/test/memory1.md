7-HelloAgents构建\hello_agents\memory\manager.py:143: in clear
    total += memory.clear()
7-HelloAgents构建\hello_agents\memory\types\episodic.py:73: in clear
    return self._store.clear(memory_type="episodic")
7-HelloAgents构建\hello_agents\memory\storage\document_store.py:293: in clear
    affected = self._execute(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <hello_agents.memory.storage.document_store.DocumentStore object at 0x000001AFA8F24590>, conn = <sqlite3.Connection object at 0x000001AFA91EF970>
sql = 'DELETE FROM `memories` WHERE memory_type = %s', params = ('episodic',)

    def _execute(self, conn, sql: str, params=None) -> int:
        if self._use_mysql():
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
            conn.commit()
            return affected
        else:
>           cur = conn.execute(sql, params or ())
E           sqlite3.OperationalError: near "%": syntax error

7-HelloAgents构建\hello_agents\memory\storage\document_store.py:394: OperationalError
_______________________________________________________ ERROR at setup of TestMemoryManager.test_consolidate ________________________________________________________

self = <test_memory.TestMemoryManager object at 0x000001AFA8EF3DD0>

    @pytest.fixture(autouse=True)
    def setup(self):
        from hello_agents.memory import MemoryConfig, MemoryItem, MemoryManager
        cfg = MemoryConfig(
            working_capacity=20,
            episodic_db_path=":memory:",
            semantic_enabled=False,
            perceptual_enabled=False,
        )
        emb = TFIDFEmbedding()
        emb.fit(["测试", "记忆"])
        self.mgr = MemoryManager(config=cfg, embedding=emb)
        self.MemoryItem = MemoryItem
>       self.mgr.clear()

7-HelloAgents构建\test\test_memory.py:456: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\manager.py:143: in clear
    total += memory.clear()
7-HelloAgents构建\hello_agents\memory\types\episodic.py:73: in clear
    return self._store.clear(memory_type="episodic")
7-HelloAgents构建\hello_agents\memory\storage\document_store.py:293: in clear
    affected = self._execute(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <hello_agents.memory.storage.document_store.DocumentStore object at 0x000001AFA9230800>, conn = <sqlite3.Connection object at 0x000001AFA91EDC60>
sql = 'DELETE FROM `memories` WHERE memory_type = %s', params = ('episodic',)

    def _execute(self, conn, sql: str, params=None) -> int:
        if self._use_mysql():
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
            conn.commit()
            return affected
        else:
>           cur = conn.execute(sql, params or ())
E           sqlite3.OperationalError: near "%": syntax error

7-HelloAgents构建\hello_agents\memory\storage\document_store.py:394: OperationalError
____________________________________________________ ERROR at setup of TestMemoryManager.test_forget_importance _____________________________________________________

self = <test_memory.TestMemoryManager object at 0x000001AFA8EF0110>

    @pytest.fixture(autouse=True)
    def setup(self):
        from hello_agents.memory import MemoryConfig, MemoryItem, MemoryManager
        cfg = MemoryConfig(
            working_capacity=20,
            episodic_db_path=":memory:",
            semantic_enabled=False,
            perceptual_enabled=False,
        )
        emb = TFIDFEmbedding()
        emb.fit(["测试", "记忆"])
        self.mgr = MemoryManager(config=cfg, embedding=emb)
        self.MemoryItem = MemoryItem
>       self.mgr.clear()

7-HelloAgents构建\test\test_memory.py:456: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\manager.py:143: in clear
    total += memory.clear()
7-HelloAgents构建\hello_agents\memory\types\episodic.py:73: in clear
    return self._store.clear(memory_type="episodic")
7-HelloAgents构建\hello_agents\memory\storage\document_store.py:293: in clear
    affected = self._execute(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <hello_agents.memory.storage.document_store.DocumentStore object at 0x000001AFA9232C00>, conn = <sqlite3.Connection object at 0x000001AFA91784F0>
sql = 'DELETE FROM `memories` WHERE memory_type = %s', params = ('episodic',)

    def _execute(self, conn, sql: str, params=None) -> int:
        if self._use_mysql():
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
            conn.commit()
            return affected
        else:
>           cur = conn.execute(sql, params or ())
E           sqlite3.OperationalError: near "%": syntax error

7-HelloAgents构建\hello_agents\memory\storage\document_store.py:394: OperationalError
_____________________________________________________ ERROR at setup of TestMemoryManager.test_forget_capacity ______________________________________________________

self = <test_memory.TestMemoryManager object at 0x000001AFA8EF0DA0>

    @pytest.fixture(autouse=True)
    def setup(self):
        from hello_agents.memory import MemoryConfig, MemoryItem, MemoryManager
        cfg = MemoryConfig(
            working_capacity=20,
            episodic_db_path=":memory:",
            semantic_enabled=False,
            perceptual_enabled=False,
        )
        emb = TFIDFEmbedding()
        emb.fit(["测试", "记忆"])
        self.mgr = MemoryManager(config=cfg, embedding=emb)
        self.MemoryItem = MemoryItem
>       self.mgr.clear()

7-HelloAgents构建\test\test_memory.py:456: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\manager.py:143: in clear
    total += memory.clear()
7-HelloAgents构建\hello_agents\memory\types\episodic.py:73: in clear
    return self._store.clear(memory_type="episodic")
7-HelloAgents构建\hello_agents\memory\storage\document_store.py:293: in clear
    affected = self._execute(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <hello_agents.memory.storage.document_store.DocumentStore object at 0x000001AFA8F26840>, conn = <sqlite3.Connection object at 0x000001AFA91EC6D0>
sql = 'DELETE FROM `memories` WHERE memory_type = %s', params = ('episodic',)

    def _execute(self, conn, sql: str, params=None) -> int:
        if self._use_mysql():
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
            conn.commit()
            return affected
        else:
>           cur = conn.execute(sql, params or ())
E           sqlite3.OperationalError: near "%": syntax error

7-HelloAgents构建\hello_agents\memory\storage\document_store.py:394: OperationalError
__________________________________________________________ ERROR at setup of TestMemoryManager.test_stats ___________________________________________________________

self = <test_memory.TestMemoryManager object at 0x000001AFA8EF2ED0>

    @pytest.fixture(autouse=True)
    def setup(self):
        from hello_agents.memory import MemoryConfig, MemoryItem, MemoryManager
        cfg = MemoryConfig(
            working_capacity=20,
            episodic_db_path=":memory:",
            semantic_enabled=False,
            perceptual_enabled=False,
        )
        emb = TFIDFEmbedding()
        emb.fit(["测试", "记忆"])
        self.mgr = MemoryManager(config=cfg, embedding=emb)
        self.MemoryItem = MemoryItem
>       self.mgr.clear()

7-HelloAgents构建\test\test_memory.py:456: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\manager.py:143: in clear
    total += memory.clear()
7-HelloAgents构建\hello_agents\memory\types\episodic.py:73: in clear
    return self._store.clear(memory_type="episodic")
7-HelloAgents构建\hello_agents\memory\storage\document_store.py:293: in clear
    affected = self._execute(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <hello_agents.memory.storage.document_store.DocumentStore object at 0x000001AFA9232630>, conn = <sqlite3.Connection object at 0x000001AFA91EE7A0>
sql = 'DELETE FROM `memories` WHERE memory_type = %s', params = ('episodic',)

    def _execute(self, conn, sql: str, params=None) -> int:
        if self._use_mysql():
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
            conn.commit()
            return affected
        else:
>           cur = conn.execute(sql, params or ())
E           sqlite3.OperationalError: near "%": syntax error

7-HelloAgents构建\hello_agents\memory\storage\document_store.py:394: OperationalError
_________________________________________________________ ERROR at setup of TestMemoryManager.test_summary __________________________________________________________

self = <test_memory.TestMemoryManager object at 0x000001AFA8EF0A40>

    @pytest.fixture(autouse=True)
    def setup(self):
        from hello_agents.memory import MemoryConfig, MemoryItem, MemoryManager
        cfg = MemoryConfig(
            working_capacity=20,
            episodic_db_path=":memory:",
            semantic_enabled=False,
            perceptual_enabled=False,
        )
        emb = TFIDFEmbedding()
        emb.fit(["测试", "记忆"])
        self.mgr = MemoryManager(config=cfg, embedding=emb)
        self.MemoryItem = MemoryItem
>       self.mgr.clear()

7-HelloAgents构建\test\test_memory.py:456: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\manager.py:143: in clear
    total += memory.clear()
7-HelloAgents构建\hello_agents\memory\types\episodic.py:73: in clear
    return self._store.clear(memory_type="episodic")
7-HelloAgents构建\hello_agents\memory\storage\document_store.py:293: in clear
    affected = self._execute(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <hello_agents.memory.storage.document_store.DocumentStore object at 0x000001AFA9231610>, conn = <sqlite3.Connection object at 0x000001AFA9178B80>
sql = 'DELETE FROM `memories` WHERE memory_type = %s', params = ('episodic',)

    def _execute(self, conn, sql: str, params=None) -> int:
        if self._use_mysql():
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
            conn.commit()
            return affected
        else:
>           cur = conn.execute(sql, params or ())
E           sqlite3.OperationalError: near "%": syntax error

7-HelloAgents构建\hello_agents\memory\storage\document_store.py:394: OperationalError
============================================================================= FAILURES ==============================================================================
_______________________________________________________________ TestSemanticMemory.test_add_and_count _______________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF1100>

    def test_add_and_count(self):
        """添加语义记忆节点"""
>       mid = self.mem.add(self.MemoryItem(content="图谱节点", importance=0.8))

7-HelloAgents构建\test\test_memory.py:377: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8EF9280>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
____________________________________________________________________ TestSemanticMemory.test_get ____________________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF0B00>

    def test_get(self):
        """按 ID 获取"""
>       mid = self.mem.add(self.MemoryItem(content="查找节点"))

7-HelloAgents构建\test\test_memory.py:383: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8F0FB60>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
__________________________________________________________________ TestSemanticMemory.test_update ___________________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF0E90>

    def test_update(self):
        """更新节点"""
>       mid = self.mem.add(self.MemoryItem(content="旧", importance=0.5))

7-HelloAgents构建\test\test_memory.py:388: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8F0F4D0>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
__________________________________________________________________ TestSemanticMemory.test_delete ___________________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF09E0>

    def test_delete(self):
        """删除节点（含关联关系）"""
>       mid = self.mem.add(self.MemoryItem(content="删"))

7-HelloAgents构建\test\test_memory.py:394: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8F1C2F0>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
__________________________________________________________________ TestSemanticMemory.test_search ___________________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF06B0>

    def test_search(self):
        """content 属性文本搜索"""
>       self.mem.add(self.MemoryItem(content="机器学习是AI的分支"))

7-HelloAgents构建\test\test_memory.py:400: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8F1DE80>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
________________________________________________________ TestSemanticMemory.test_create_relationship_and_get ________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF05C0>

    def test_create_relationship_and_get(self):
        """创建关系并查询"""
>       a = self.mem.add(self.MemoryItem(content="Python"))

7-HelloAgents构建\test\test_memory.py:408: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8F2BAA0>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
_________________________________________________________________ TestSemanticMemory.test_traverse __________________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF0410>

    def test_traverse(self):
        """图遍历 1 跳"""
>       a = self.mem.add(self.MemoryItem(content="Python"))

7-HelloAgents构建\test\test_memory.py:416: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8F2A720>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
_______________________________________________________________ TestSemanticMemory.test_query_cypher ________________________________________________________________
neo4j.exceptions.GqlError: {gql_status: 22N51} {gql_status_description: error: data exception - graph reference not found. A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {message: 22N51: A graph reference with the name `neo4j` was not found. Verify that the spelling is correct.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}

The above exception was the direct cause of the following exception:

self = <test_memory.TestSemanticMemory object at 0x000001AFA8EF0590>

    def test_query_cypher(self):
        """直接执行 Cypher"""
>       mid = self.mem.add(self.MemoryItem(content="Cypher 测试"))

7-HelloAgents构建\test\test_memory.py:428: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\types\semantic.py:110: in add
    self._store.create_node(labels, props, node_id=item.id)
7-HelloAgents构建\hello_agents\memory\storage\neo4j_store.py:175: in create_node
    result = session.run(query, props=props, node_id=nid)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:318: in run
    self._connect(self._config.default_access_mode)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\session.py:128: in _connect
    super()._connect(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\work\workspace.py:181: in _connect
    self._connection = self._pool.acquire(**acquire_kwargs_)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1216: in acquire
    self.ensure_routing_table_is_fresh(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1150: in ensure_routing_table_is_fresh
    self.update_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:1009: in update_routing_table
    self._update_routing_table_from(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:935: in _update_routing_table_from
    new_routing_table = self.fetch_routing_table(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:833: in fetch_routing_table
    new_routing_info = self.fetch_routing_info(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_pool.py:794: in fetch_routing_info
    routing_table = cx.route(
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:273: in route
    self.fetch_all()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:883: in fetch_all
    detail_delta, summary_delta = self.fetch_message()
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt.py:868: in fetch_message
    res = self._process_message(tag, fields)
E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_bolt6.py:548: in _process_message
    response.on_failure(summary_metadata or {})
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <neo4j._sync.io._common.Response object at 0x000001AFA8F27980>
metadata = {'cause': {'description': 'error: data exception - graph reference not found. A graph reference with the name `neo4j` ...T_SCHEMA': '/', 'OPERATION': '', 'OPERATION_CODE': '0', '_classification': 'CLIENT_ERROR'}, 'gql_status': '22000', ...}

    def on_failure(self, metadata):
        """Handle a FAILURE message been received."""
        with suppress(SessionExpired, ServiceUnavailable):
            self.connection.reset()
        handler = self.handlers.get("on_failure")
        Util.callback(handler, metadata)
        handler = self.handlers.get("on_summary")
        Util.callback(handler)
>       raise self._hydrate_error(metadata)
E       neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this database does not exist} {gql_status: 22000} {gql_status_description: error: data exception}

E:\anaconda3\anaconda\Lib\site-packages\neo4j\_sync\io\_common.py:263: ClientError
___________________________________________________________ TestEmbedding.test_tfidf_embed_and_similarity ___________________________________________________________

self = <test_memory.TestEmbedding object at 0x000001AFA7B69940>

    def test_tfidf_embed_and_similarity(self):
        """TF-IDF 嵌入 + 余弦相似度"""
        emb = TFIDFEmbedding(max_features=50)
        emb.fit(["苹果是一种水果", "香蕉是热带水果", "电脑需要编程"])
        v1, v2, v3 = emb.embed("苹果"), emb.embed("香蕉"), emb.embed("电脑")
>       assert emb.cosine_similarity(v1, v2) > emb.cosine_similarity(v1, v3)
E       assert 0.0 > 0.0
E        +  where 0.0 = <bound method BaseEmbedding.cosine_similarity of <hello_agents.memory.embedding.TFIDFEmbedding object at 0x000001AFA9232CC0>>([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
E        +    where <bound method BaseEmbedding.cosine_similarity of <hello_agents.memory.embedding.TFIDFEmbedding object at 0x000001AFA9232CC0>> = <hello_agents.memory.embedding.TFIDFEmbedding object at 0x000001AFA9232CC0>.cosine_similarity
E        +  and   0.0 = <bound method BaseEmbedding.cosine_similarity of <hello_agents.memory.embedding.TFIDFEmbedding object at 0x000001AFA9232CC0>>([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
E        +    where <bound method BaseEmbedding.cosine_similarity of <hello_agents.memory.embedding.TFIDFEmbedding object at 0x000001AFA9232CC0>> = <hello_agents.memory.embedding.TFIDFEmbedding object at 0x000001AFA9232CC0>.cosine_similarity

7-HelloAgents构建\test\test_memory.py:567: AssertionError
_____________________________________________________________________ TestFastEmbed.test_embed ______________________________________________________________________

self = <test_memory.TestFastEmbed object at 0x000001AFA7B83E30>

    def test_embed(self):
        """FastEmbed 文本嵌入"""
        emb = FastEmbedEmbedding(model_name="all-MiniLM-L6-v2")
>       vec = emb.embed("Hello world")

7-HelloAgents构建\test\test_memory.py:600: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\embedding.py:154: in embed
    self._lazy_init()
7-HelloAgents构建\hello_agents\memory\embedding.py:150: in _lazy_init
    self._model = TextEmbedding(model_name=self.model_name, **self._kwargs)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <fastembed.text.text_embedding.TextEmbedding object at 0x000001AFA9BC6F30>, model_name = 'all-MiniLM-L6-v2', cache_dir = None, threads = None, providers = None
cuda = <Device.AUTO: 'auto'>, device_ids = None, lazy_load = False, kwargs = {}
EMBEDDING_MODEL_TYPE = <class 'fastembed.text.custom_text_embedding.CustomTextEmbedding'>, supported_models = []

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: str | None = None,
        threads: int | None = None,
        providers: Sequence[OnnxProvider] | None = None,
        cuda: bool | Device = Device.AUTO,
        device_ids: list[int] | None = None,
        lazy_load: bool = False,
        **kwargs: Any,
    ):
        super().__init__(model_name, cache_dir, threads, **kwargs)
        if model_name.lower() == "nomic-ai/nomic-embed-text-v1.5-Q".lower():
            warnings.warn(
                "The model 'nomic-ai/nomic-embed-text-v1.5-Q' has been updated on HuggingFace. Please review "
                "the latest documentation on HF and release notes to ensure compatibility with your workflow. ",
                UserWarning,
                stacklevel=2,
            )
        if model_name.lower() in {
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2".lower(),
            "thenlper/gte-large".lower(),
            "intfloat/multilingual-e5-large".lower(),
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2".lower(),
        }:
            warnings.warn(
                f"The model {model_name} now uses mean pooling instead of CLS embedding. "
                f"In order to preserve the previous behaviour, consider either pinning fastembed version to 0.5.1 or "
                "using `add_custom_model` functionality.",
                UserWarning,
                stacklevel=2,
            )
        for EMBEDDING_MODEL_TYPE in self.EMBEDDINGS_REGISTRY:
            supported_models = EMBEDDING_MODEL_TYPE._list_supported_models()
            if any(model_name.lower() == model.model.lower() for model in supported_models):
                self.model = EMBEDDING_MODEL_TYPE(
                    model_name=model_name,
                    cache_dir=cache_dir,
                    threads=threads,
                    providers=providers,
                    cuda=cuda,
                    device_ids=device_ids,
                    lazy_load=lazy_load,
                    **kwargs,
                )
                return
    
>       raise ValueError(
            f"Model {model_name} is not supported in TextEmbedding. "
            "Please check the supported models using `TextEmbedding.list_supported_models()`"
        )
E       ValueError: Model all-MiniLM-L6-v2 is not supported in TextEmbedding. Please check the supported models using `TextEmbedding.list_supported_models()`

E:\anaconda3\anaconda\Lib\site-packages\fastembed\text\text_embedding.py:126: ValueError
__________________________________________________________________ TestFastEmbed.test_embed_batch ___________________________________________________________________

self = <test_memory.TestFastEmbed object at 0x000001AFA7B832C0>

    def test_embed_batch(self):
        """批量嵌入"""
        emb = FastEmbedEmbedding(model_name="all-MiniLM-L6-v2")
>       vecs = emb.embed_batch(["Hello", "World", "Test"])

7-HelloAgents构建\test\test_memory.py:606: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\embedding.py:159: in embed_batch
    self._lazy_init()
7-HelloAgents构建\hello_agents\memory\embedding.py:150: in _lazy_init
    self._model = TextEmbedding(model_name=self.model_name, **self._kwargs)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <fastembed.text.text_embedding.TextEmbedding object at 0x000001AFA9C2B080>, model_name = 'all-MiniLM-L6-v2', cache_dir = None, threads = None, providers = None
cuda = <Device.AUTO: 'auto'>, device_ids = None, lazy_load = False, kwargs = {}
EMBEDDING_MODEL_TYPE = <class 'fastembed.text.custom_text_embedding.CustomTextEmbedding'>, supported_models = []

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: str | None = None,
        threads: int | None = None,
        providers: Sequence[OnnxProvider] | None = None,
        cuda: bool | Device = Device.AUTO,
        device_ids: list[int] | None = None,
        lazy_load: bool = False,
        **kwargs: Any,
    ):
        super().__init__(model_name, cache_dir, threads, **kwargs)
        if model_name.lower() == "nomic-ai/nomic-embed-text-v1.5-Q".lower():
            warnings.warn(
                "The model 'nomic-ai/nomic-embed-text-v1.5-Q' has been updated on HuggingFace. Please review "
                "the latest documentation on HF and release notes to ensure compatibility with your workflow. ",
                UserWarning,
                stacklevel=2,
            )
        if model_name.lower() in {
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2".lower(),
            "thenlper/gte-large".lower(),
            "intfloat/multilingual-e5-large".lower(),
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2".lower(),
        }:
            warnings.warn(
                f"The model {model_name} now uses mean pooling instead of CLS embedding. "
                f"In order to preserve the previous behaviour, consider either pinning fastembed version to 0.5.1 or "
                "using `add_custom_model` functionality.",
                UserWarning,
                stacklevel=2,
            )
        for EMBEDDING_MODEL_TYPE in self.EMBEDDINGS_REGISTRY:
            supported_models = EMBEDDING_MODEL_TYPE._list_supported_models()
            if any(model_name.lower() == model.model.lower() for model in supported_models):
                self.model = EMBEDDING_MODEL_TYPE(
                    model_name=model_name,
                    cache_dir=cache_dir,
                    threads=threads,
                    providers=providers,
                    cuda=cuda,
                    device_ids=device_ids,
                    lazy_load=lazy_load,
                    **kwargs,
                )
                return
    
>       raise ValueError(
            f"Model {model_name} is not supported in TextEmbedding. "
            "Please check the supported models using `TextEmbedding.list_supported_models()`"
        )
E       ValueError: Model all-MiniLM-L6-v2 is not supported in TextEmbedding. Please check the supported models using `TextEmbedding.list_supported_models()`

E:\anaconda3\anaconda\Lib\site-packages\fastembed\text\text_embedding.py:126: ValueError
___________________________________________________________________ TestFastEmbed.test_similarity ___________________________________________________________________

self = <test_memory.TestFastEmbed object at 0x000001AFA7B83830>

    def test_similarity(self):
        """语义相似度"""
        emb = FastEmbedEmbedding(model_name="all-MiniLM-L6-v2")
>       v1 = emb.embed("apple")

7-HelloAgents构建\test\test_memory.py:613: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
7-HelloAgents构建\hello_agents\memory\embedding.py:154: in embed
    self._lazy_init()
7-HelloAgents构建\hello_agents\memory\embedding.py:150: in _lazy_init
    self._model = TextEmbedding(model_name=self.model_name, **self._kwargs)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <fastembed.text.text_embedding.TextEmbedding object at 0x000001AFA9C2BC80>, model_name = 'all-MiniLM-L6-v2', cache_dir = None, threads = None, providers = None
cuda = <Device.AUTO: 'auto'>, device_ids = None, lazy_load = False, kwargs = {}
EMBEDDING_MODEL_TYPE = <class 'fastembed.text.custom_text_embedding.CustomTextEmbedding'>, supported_models = []

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: str | None = None,
        threads: int | None = None,
        providers: Sequence[OnnxProvider] | None = None,
        cuda: bool | Device = Device.AUTO,
        device_ids: list[int] | None = None,
        lazy_load: bool = False,
        **kwargs: Any,
    ):
        super().__init__(model_name, cache_dir, threads, **kwargs)
        if model_name.lower() == "nomic-ai/nomic-embed-text-v1.5-Q".lower():
            warnings.warn(
                "The model 'nomic-ai/nomic-embed-text-v1.5-Q' has been updated on HuggingFace. Please review "
                "the latest documentation on HF and release notes to ensure compatibility with your workflow. ",
                UserWarning,
                stacklevel=2,
            )
        if model_name.lower() in {
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2".lower(),
            "thenlper/gte-large".lower(),
            "intfloat/multilingual-e5-large".lower(),
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2".lower(),
        }:
            warnings.warn(
                f"The model {model_name} now uses mean pooling instead of CLS embedding. "
                f"In order to preserve the previous behaviour, consider either pinning fastembed version to 0.5.1 or "
                "using `add_custom_model` functionality.",
                UserWarning,
                stacklevel=2,
            )
        for EMBEDDING_MODEL_TYPE in self.EMBEDDINGS_REGISTRY:
            supported_models = EMBEDDING_MODEL_TYPE._list_supported_models()
            if any(model_name.lower() == model.model.lower() for model in supported_models):
                self.model = EMBEDDING_MODEL_TYPE(
                    model_name=model_name,
                    cache_dir=cache_dir,
                    threads=threads,
                    providers=providers,
                    cuda=cuda,
                    device_ids=device_ids,
                    lazy_load=lazy_load,
                    **kwargs,
                )
                return
    
>       raise ValueError(
            f"Model {model_name} is not supported in TextEmbedding. "
            "Please check the supported models using `TextEmbedding.list_supported_models()`"
        )
E       ValueError: Model all-MiniLM-L6-v2 is not supported in TextEmbedding. Please check the supported models using `TextEmbedding.list_supported_models()`

E:\anaconda3\anaconda\Lib\site-packages\fastembed\text\text_embedding.py:126: ValueError
========================================================================= warnings summary ==========================================================================
E:\anaconda3\anaconda\Lib\site-packages\_pytest\config\__init__.py:1204
  E:\anaconda3\anaconda\Lib\site-packages\_pytest\config\__init__.py:1204: PytestAssertRewriteWarning: Module already imported so cannot be rewritten: anyio
    self._mark_plugins_for_rewrite(hook)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================================================================== short test summary info ======================================================================
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_add_and_count - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_get - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_update - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_delete - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_search - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_create_relationship_and_get - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_traverse - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestSemanticMemory::test_query_cypher - neo4j.exceptions.ClientError: {neo4j_code: Neo.ClientError.Database.DatabaseNotFound} {message: Unable to get a routing table for database 'neo4j' because this d...
FAILED 7-HelloAgents构建/test/test_memory.py::TestEmbedding::test_tfidf_embed_and_similarity - assert 0.0 > 0.0
FAILED 7-HelloAgents构建/test/test_memory.py::TestFastEmbed::test_embed - ValueError: Model all-MiniLM-L6-v2 is not supported in TextEmbedding. Please check the supported models using `TextEmbedding.list_supported_models()`
FAILED 7-HelloAgents构建/test/test_memory.py::TestFastEmbed::test_embed_batch - ValueError: Model all-MiniLM-L6-v2 is not supported in TextEmbedding. Please check the supported models using `TextEmbedding.list_supported_models()`
FAILED 7-HelloAgents构建/test/test_memory.py::TestFastEmbed::test_similarity - ValueError: Model all-MiniLM-L6-v2 is not supported in TextEmbedding. Please check the supported models using `TextEmbedding.list_supported_models()`
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_add_and_count - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_add_returns_id - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_get - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_get_not_found - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_update - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_delete - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_clear - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_search - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_get_by_session - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestEpisodicMemory::test_get_recent - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_save_working - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_save_episodic - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_search_cross_type - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_search_filter_by_type - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_get_and_update - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_delete - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_consolidate - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_forget_importance - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_forget_capacity - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_stats - sqlite3.OperationalError: near "%": syntax error
ERROR 7-HelloAgents构建/test/test_memory.py::TestMemoryManager::test_summary - sqlite3.OperationalError: near "%": syntax error
======================================================= 12 failed, 22 passed, 1 warning, 21 errors in 19.62s ========================================================