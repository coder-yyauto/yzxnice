

---

## 教学模拟平台（NiceGUI + DuckDB）

### 一、项目概述

基于现有 `ycnice`（系统管理底座）和 `yzxpyq`（微信朋友圈模拟模块），重构一个支持**多学校隔离**的线上教育系统。每个学校为独立租户，组织架构为 **学校 → 年级 → 班级**。学生使用“上课席位”账号（学号）登录，教师直属学校，管理员按年级/班级授权。核心业务是**朋友圈模块**，内容按学校、年级、班级隔离可见，用户仅能管理自己发布的内容。

目标框架：**NiceGUI**  
项目根目录：`yzxnice`（当前为空）  
参考代码：`../ycnice`（底座）、`../yzxpyq`（朋友圈）  
数据库：**DuckDB**（与 `ycnice` 一致，使用 SQLAlchemy + duckdb_engine）

---

### 二、组织与用户模型（基于ycnice扩展）

#### 1. 组织（Organization）

- **根组织**：系统级，id=1
- **二级组织**：每个学校，属性 `org_type = 'school'`，附加属性 `school_code`（唯一，如 `xx001`）、`school_level = 'primary'`
- **三级组织**：年级（1~5年级），属性 `org_type = 'grade'`，关联 `parent_org` 为学校，附加 `grade_number`
- **四级组织**：班级（每个年级6个班），属性 `org_type = 'class'`，关联 `parent_org` 为年级，附加 `class_number`（1~6）

> 利用 `ycnice` 的多级组织表（如 `sys_org`），支持 `parent_id` 层级。

#### 2. 用户（User）

- **教师账号**：直属二级组织（学校），`user_type = 'teacher'`，账号格式 `工号`（如 `T+学校代码+数字`），密码初始可统一。
- **学生账号**：`user_type = 'student'`，账号 = **学校代码 + 2001开始的四位数字**（如 `xx0012001`）。**不绑定真实身份**，仅作为上课席位。账号所属组织为**班级**（四级组织）。
- **系统/学校管理员**：由系统或学校指定，`user_type = 'admin'`，但**学生账号永远不能成为管理员**。

> 用户与组织关联：一个用户可属于一个组织（教师属于学校，学生属于班级），但为了权限继承，可记录 `default_org_id`。管理员需额外关联授权范围。

#### 3. 管理员授权（Role / Permission）

- **角色**：`school_admin`（校级）、`grade_admin`（年级级）、`class_admin`（班级级）。
- **授权方式**：为指定用户（教师）绑定角色，并指定**管辖组织ID**（`scope_org_id`）。该用户对该组织及其所有子组织拥有**管理权限**（管理内容包括：用户、朋友圈内容审核/删除？需求中说“管理员对被授权范围组织及其子组织具备管理权限”——需明确管理范围：可管理该组织下所有用户发布的内容？或者仅管理组织成员？按常见教育系统，管理员可删除管辖范围内的不当内容，但需求未明确。建议：管理员对管辖范围内所有用户发布的内容有**删除/隐藏**权限，但不可编辑他人内容。学生不得有此权限。）
- **普通教师**：对本校内所有**非管理信息**有默认权限 = 等同普通用户（只能管理自己的发布内容），但能**查看**本校所有朋友圈（按班级隔离？需求未明确班级隔离）。为了教学安全，建议：教师可见本校**所有班级**的朋友圈（只读），但只能删除/编辑自己发的。学校管理员可见全校并可删除任何内容。

> 具体实现时可在 `ycnice` 权限表基础上增加 `scope_org_id` 字段。

---

### 三、权限与数据隔离规则（核心）

| 用户类型        | 可见范围（朋友圈）                  | 可管理的内容（编辑/删除）         |
| ----------- | -------------------------- | --------------------- |
| 学生（student） | 仅自己**所在班级**的朋友圈            | 仅自己发布的内容              |
| 教师（teacher） | 自己**所在学校**的所有班级朋友圈（可看不可干预） | 仅自己发布的内容              |
| 班级管理员       | 管辖班级（及其子组织，无子）的朋友圈         | 管辖范围内所有用户发布的内容（删除/隐藏） |
| 年级管理员       | 管辖年级下所有班级的朋友圈              | 管辖范围内所有用户发布的内容        |
| 学校管理员       | 全校朋友圈                      | 全校所有内容                |
| 系统管理员       | 所有学校                       | 所有内容                  |

> **注意**：学生账号**不能**被授予任何管理员角色。教师默认无管理他人内容的权限，除非被授予管理员角色。

#### 补充隔离细节：

- 发朋友圈时，必须选择**发布范围**（仅班级 / 仅年级 / 全校？为了安全，初期只实现“发布到所在班级”，后续可扩展）。
- 每个帖子记录 `owner_user_id`（发布者）、`org_id`（发布时所属组织，即班级ID），用于隔离查询。
- 教师登录后默认展示本校所有班级的帖子流（可按班级筛选）。学生只展示自己班级的帖子流。

---

### 四、朋友圈模块功能（基于yzxpyq改造）

复用 `yzxpyq` 的UI组件（卡片、点赞、评论、发布框），但需增加：

1. **登录与组织选择**  
   
   - 使用 `ycnice` 的登录认证。登录后根据用户类型和组织信息，自动确定可见范围。
   - 如果是教师且管理多个班级，可切换“管理视图”（展示管辖范围内所有帖子，带删除按钮）。

2. **发布帖子**  
   
   - 文本+图片（NiceGUI支持上传）。  
   - 发布时自动标记所属组织：学生取所在班级ID；教师取所在学校ID（但教师发布帖子可设置可见范围？初期教师也仅发布到自己的“教师圈”或全校？按需求，教师等同普通用户，即只能管理自己的发布，但可见全校。为简化，教师发布帖子默认**全校可见**，学生发布默认**本班可见**。  
   - 教师如果被授予年级/班级管理员，发布时可见范围可扩大到管辖范围。

3. **帖子列表**  
   
   - 根据当前用户权限，过滤出可见帖子。  
   - 显示发布者姓名、所属班级（或学校）、发布时间、点赞数、评论列表。  
   - 对于管理员，每条帖子附带“删除”按钮（仅当用户对该帖子所属组织有管理权限时显示）。

4. **点赞与评论**  
   
   - 任何人可见即可点赞/评论。评论者也受同样权限约束（评论内容可被管理员删除）。  
   - 删除自己的评论。管理员可删除管辖范围内的评论。

5. **管理后台**（集成到 `ycnice` 组织管理页面）  
   
   - 创建学校、年级、班级（自动生成班级内的学生账号，批量生成学号：学校代码+2001~2001+40*6*5-1？需按班级分配）。  
   - 为教师账号分配管理员角色及管辖组织。  
   - 查看/重置学生账号密码（学生账号不绑定真实身份，密码可统一或随机生成）。

---

### 五、数据模型关键字段（使用 DuckDB + SQLAlchemy）

DuckDB 连接方式：`duckdb:///./yzxnice.db`（与 `ycnice` 保持一致，使用文件型数据库）。SQLAlchemy ORM 完全兼容。

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Org(Base):
    __tablename__ = 'org'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    org_type = Column(String)  # school, grade, class
    parent_id = Column(Integer, ForeignKey('org.id'))
    school_code = Column(String, unique=True)  # 仅学校有
    grade_number = Column(Integer)  # 1~5
    class_number = Column(Integer)  # 1~6

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    user_type = Column(String)  # teacher, student, admin
    default_org_id = Column(Integer, ForeignKey('org.id'))
    # 学生所属班级（冗余，便于查询）
    class_org_id = Column(Integer, ForeignKey('org.id'), nullable=True)

class UserRole(Base):
    __tablename__ = 'user_role'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    role = Column(String)  # school_admin, grade_admin, class_admin
    scope_org_id = Column(Integer, ForeignKey('org.id'))  # 管辖组织根

class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    content = Column(String)
    images = Column(JSON)  # 存储图片URL列表（本地路径或base64）
    org_id = Column(Integer, ForeignKey('org.id'))  # 发布时的所属班级/学校
    visible_org_id = Column(Integer, ForeignKey('org.id'))  # 可见范围根组织（班级/年级/学校）
    created_at = Column(DateTime)

class Like(Base):
    __tablename__ = 'like'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('post.id'))
    user_id = Column(Integer, ForeignKey('user.id'))

class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('post.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    content = Column(String)
    created_at = Column(DateTime)
```

> 注意：DuckDB 默认支持 `JSON` 类型，可直接存储列表。

---

### 六、技术栈与实现步骤

#### 技术栈

- **NiceGUI**：前端组件与后端路由一体化（`开发环境已安装`）
- **SQLAlchemy** + **DuckDB**（`开发环境已安装`）
- **FastAPI**（NiceGUI底层）
- 认证：使用 `ycnice` 的 session 或 JWT（参考其实现）

#### 实施步骤（AI执行顺序）

1. **复制并整合基础代码**
   
   - 将 `../ycnice` 的核心模块（组织管理、用户认证、权限表）复制到 `yzxnice` 中，重命名为 `core`。
   - 将 `../yzxpyq` 的朋友圈UI组件（如 `moment_card.py`, `moment_list.py`, `publish.py`）复制到 `yzxnice/pyq`。

2. **调整数据模型**
   
   - 修改 `core/models.py`，按上述模型添加 `Org`、`User`、`UserRole`、`Post`、`Like`、`Comment`。
   - 确保使用 DuckDB 连接：`engine = create_engine('duckdb:///./yzxnice.db')`。
   - 运行 `Base.metadata.create_all(engine)` 创建表。

3. **实现组织初始化脚本**
   
   - 编写脚本 `init_school.py`：创建学校（指定school_code），创建5个年级，每个年级6个班级。
   - 批量生成学生账号：每个班级40个，账号格式 `{school_code}{2001+offset}`，密码默认 `123456`，组织绑定到对应班级。
   - 创建教师账号（每个学校至少1名），并可选分配管理员角色。

4. **实现权限判断中间件/工具函数**
   
   - `get_visible_org_ids(user)`：返回该用户可见帖子的组织ID列表（递归查询子组织）。
   - `can_manage_post(user, post)`：判断用户是否有权删除/编辑该帖子（基于UserRole的scope_org_id和post.org_id的包含关系）。

5. **改造朋友圈视图**
   
   - 登录页：使用 `ycnice` 登录逻辑。
   - 主页：显示 `Post` 列表，调用 `get_visible_org_ids` 过滤。
   - 发布框：自动填充 `org_id`（用户默认组织）和 `visible_org_id`（学生为班级，教师为学校）。
   - 管理员界面：为每个帖子添加“删除”按钮（仅当 `can_manage_post` 为真）。

6. **集成管理功能**
   
   - 在 `ycnice` 的管理页面中增加“管理员授权”标签页，允许校级管理员为用户（教师）分配年级/班级管理员角色并选择管辖组织。
   - 增加“批量生成学生账号”按钮（按班级）。

7. **测试与演示**
   
   - 创建两个不同学校（如 `xx001`、`xx002`），登录学生验证只能看到本班帖子。
   - 登录教师验证可见全校帖子但只能删自己的。
   - 登录年级管理员验证可删除管辖年级内任何帖子。

---

### 七、关键实现提示（给AI的编程约束）

- **NiceGUI 组件使用**：`ui.column`, `ui.card`, `ui.input`, `ui.button`, `ui.image`, `ui.dialog` 等。图片上传用 `ui.upload`。
- **路由组织**：使用 `@ui.page('/')` 等。登录状态通过 `app.storage.user` 或 `app.storage.browser` 管理。
- **安全**：所有数据查询必须基于当前用户权限过滤，**禁止**前端传入 `org_id` 直接查询，必须后端验证。
- **不要**依赖外部的复杂权限库，手写简单的 `if` 判断即可，因为需求明确。
- **DuckDB 注意事项**：
  - 并发连接数有限，生产环境可考虑开启 `thread_safe` 模式（使用 `duckdb:///file.db?thread_safe=1`）。
  - 日期时间使用 Python `datetime` 对象，DuckDB 会自动转换。
  - 图片存储建议保存为本地文件（`static/uploads/`），数据库中存储相对路径。
- **代码结构**：
  
  ```
  yzxnice/
  ├── main.py           # NiceGUI启动，创建数据库引擎
  ├── core/             # 复制自ycnice，调整模型
  │   ├── models.py
  │   ├── auth.py
  │   └── org_utils.py
  ├── pyq/              # 朋友圈模块
  │   ├── views.py      # 页面逻辑
  │   ├── components.py # 卡片等组件
  │   └── permissions.py
  ├── admin/            # 管理页面（组织、账号、授权）
  ├── static/           # 上传图片
  └── init_data.py
  ```

---

### 八、交付标准

运行 `python main.py` 后，访问 `http://localhost:8080`，能够：

- 注册/登录（已有账号）。
- 学生（如 `xx0012001`）登录后只能看到本班朋友圈，发布内容仅本班可见，不能删除他人内容。
- 教师（如 `Txx001001`）登录后看到本校所有班级朋友圈，只能删除自己发布的内容。
- 学校管理员（为某教师授予 `school_admin`）登录后，每条帖子都有删除按钮，删除生效。
- 管理后台可创建新学校、年级、班级，并自动生成学生账号。
- 数据库文件 `yzxnice.db` 自动生成，且所有数据持久化。

---

此描述已适配 **DuckDB**，可直接用于 AI 编程任务。请按上述步骤生成代码。
