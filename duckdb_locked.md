这是一个典型的 DuckDB 文件锁冲突问题。DuckDB 在同一个数据库文件上不支持多个写入连接同时打开。以下是几种解决方案：

## 解决方案 1：复用现有连接（推荐）

避免在对话框函数中创建新连接，而是复用已有的全局连接：

```python
import duckdb
import streamlit as st

# 初始化全局连接
@st.cache_resource
def init_db():
    return duckdb.connect('your_database.db')

def _open_filter_dialog():
    db = init_db()  # 复用连接，而不是创建新的
    # 你的查询逻辑
    result = db.execute("SELECT * FROM your_table").fetchdf()
    # ... 其他逻辑
```

## 解决方案 2：使用只读连接

如果对话框只需要查询数据，可以打开只读连接：

```python
def _open_filter_dialog():
    # 以只读模式打开，避免锁冲突
    readonly_db = duckdb.connect('your_database.db', read_only=True)
    try:
        result = readonly_db.execute("SELECT * FROM your_table").fetchdf()
        # ... 处理结果
    finally:
        readonly_db.close()
```

## 解决方案 3：添加连接池管理

```python
import threading
from contextlib import contextmanager

class DuckDBPool:
    def __init__(self, db_path, max_connections=5):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._connections = []
        self._max_connections = max_connections
    
    @contextmanager
    def get_connection(self):
        conn = None
        with self._lock:
            if self._connections:
                conn = self._connections.pop()
            elif len(self._connections) < self._max_connections:
                conn = duckdb.connect(self.db_path)
        
        if conn is None:
            raise Exception("No available connections")
        
        try:
            yield conn
        finally:
            with self._lock:
                self._connections.append(conn)

# 使用示例
pool = DuckDBPool('your_database.db')

def _open_filter_dialog():
    with pool.get_connection() as conn:
        result = conn.execute("SELECT * FROM your_table").fetchdf()
```

## 解决方案 4：短期释放主连接

如果必须在对话框中使用新连接，可以临时关闭主连接：

```python
def _open_filter_dialog():
    # 关闭当前 session 的连接
    if 'db' in st.session_state:
        st.session_state.db.close()
    
    try:
        # 创建临时连接
        with duckdb.connect('your_database.db') as temp_db:
            result = temp_db.execute("SELECT * FROM your_table").fetchdf()
            # ... 处理结果
    finally:
        # 重新建立主连接
        st.session_state.db = duckdb.connect('your_database.db')
```

## 最佳实践建议

对于 Streamlit 应用，推荐使用**方案 1** + 连接缓存：

```python
import streamlit as st
import duckdb
from contextlib import contextmanager

@st.cache_resource
def get_db_connection():
    """全局单例连接"""
    return duckdb.connect('your_database.db', config={'temp_directory': '/tmp/duckdb'})

@contextmanager
def get_db_session():
    """获取数据库会话（复用全局连接）"""
    conn = get_db_connection()
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        raise e

# 使用示例
def main():
    with get_db_session() as conn:
        df = conn.execute("SELECT * FROM table").fetchdf()
    
    # 按钮回调
    if st.button("打开筛选对话框"):
        with get_db_session() as conn:
            # 同样使用会话
            filtered = conn.execute("SELECT * FROM table WHERE condition").fetchdf()
```

**关键点：**
- DuckDB 对同一个数据库文件的写操作需要独占锁
- Streamlit 的 rerun 机制可能多次创建连接
- 使用 `@st.cache_resource` 确保单例连接
- 尽量避免在同一个应用生命周期内打开多个连接