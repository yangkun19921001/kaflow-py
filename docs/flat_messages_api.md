# 展平消息 API 使用指南

## 🎯 新增功能

新增的 `/api/chat/messages` 接口用于**按单条消息分页**获取对话历史，与 `/api/chat/history` 的区别如下：

| 特性 | `/api/chat/history` | `/api/chat/messages` |
|------|---------------------|----------------------|
| 分页单位 | Checkpoint（对话快照） | 单条消息 |
| 返回内容 | 每个 checkpoint 包含多条消息 | 单条消息列表 |
| 适用场景 | 调试、状态恢复 | **常规对话历史展示** ✅ |
| 数据量 | 可能包含重复消息 | 去重后的消息列表 |

## 📡 API 接口

### **POST** `/api/chat/messages`

获取展平的单条消息列表。

#### 请求参数

```json
{
  "thread_id": "yang1001yk@gmail.com_3cb83f36-85a9-47d1-a2df-4df2e8eced86_4",
  "page": 1,
  "page_size": 20,
  "order": "desc",
  "config_id": "4"  // 可选
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| thread_id | string | ✅ | - | 会话线程ID |
| page | integer | ❌ | 1 | 页码（从 1 开始） |
| page_size | integer | ❌ | 20 | 每页大小（1-100） |
| order | string | ❌ | desc | desc（最新在前）或 asc（最早在前） |
| config_id | string | ❌ | null | 配置ID（可从 thread_id 自动解析） |

#### 响应示例

```json
{
  "thread_id": "yang1001yk@gmail.com_3cb83f36-85a9-47d1-a2df-4df2e8eced86_4",
  "total": 30,           // 总共 30 条消息
  "page": 1,
  "page_size": 5,
  "total_pages": 6,      // 共 6 页
  "config_id": "4",
  "messages": [          // 本页的 5 条消息
    {
      "type": "AIMessage",
      "content": "你好呀！",
      "role": "ai",
      "additional_kwargs": {},
      "tool_call_id": null
    },
    {
      "type": "HumanMessage",
      "content": "你好",
      "role": "human",
      "additional_kwargs": {},
      "tool_call_id": null
    },
    // ... 另外 3 条消息
  ]
}
```

## 💻 使用示例

### cURL

```bash
# 获取第1页（最新的 5 条消息）
curl -X POST "http://localhost:8000/api/chat/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "yang1001yk@gmail.com_xxx_4",
    "page": 1,
    "page_size": 5,
    "order": "desc"
  }'

# 获取第2页
curl -X POST "http://localhost:8000/api/chat/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "yang1001yk@gmail.com_xxx_4",
    "page": 2,
    "page_size": 5,
    "order": "desc"
  }'
```

### Python

```python
import requests

def get_conversation_messages(thread_id, page=1, page_size=20):
    """获取对话消息（按单条消息分页）"""
    url = "http://localhost:8000/api/chat/messages"
    
    payload = {
        "thread_id": thread_id,
        "page": page,
        "page_size": page_size,
        "order": "desc"
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 调用失败: {response.text}")

# 使用示例
result = get_conversation_messages(
    "yang1001yk@gmail.com_xxx_4",
    page=1,
    page_size=10
)

print(f"总消息数: {result['total']}")
print(f"当前页: {result['page']} / {result['total_pages']}")
print(f"\n消息列表:")
for i, msg in enumerate(result['messages'], 1):
    print(f"{i}. [{msg['role']}] {msg['content'][:50]}...")
```

### JavaScript/TypeScript

```typescript
async function getConversationMessages(
  threadId: string,
  page: number = 1,
  pageSize: number = 20
) {
  const response = await fetch('http://localhost:8000/api/chat/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      thread_id: threadId,
      page,
      page_size: pageSize,
      order: 'desc'
    })
  });
  
  if (!response.ok) {
    throw new Error(`API 调用失败: ${await response.text()}`);
  }
  
  return await response.json();
}

// 使用示例
const result = await getConversationMessages('yang1001yk@gmail.com_xxx_4', 1, 10);
console.log(`总消息数: ${result.total}`);
console.log(`当前页: ${result.page} / ${result.total_pages}`);

result.messages.forEach((msg: any, idx: number) => {
  console.log(`${idx + 1}. [${msg.role}] ${msg.content.substring(0, 50)}...`);
});
```

## 🎨 典型 UI 场景

### 1. 聊天历史页面

```
┌─────────────────────────────────────┐
│  对话历史 (共 30 条消息)            │
├─────────────────────────────────────┤
│ 🤖 你好呀！                         │
│ 👤 你好                             │
│ 🤖 有什么可以帮你的吗？             │
│ 👤 帮我写一个函数                   │
│ 🤖 好的，我来帮你写...               │
├─────────────────────────────────────┤
│ [加载更多] 第 1/6 页                │
└─────────────────────────────────────┘
```

### 2. 无限滚动加载

```javascript
// React 示例
const [messages, setMessages] = useState([]);
const [page, setPage] = useState(1);
const [hasMore, setHasMore] = useState(true);

const loadMore = async () => {
  const result = await getConversationMessages(threadId, page, 20);
  
  setMessages([...messages, ...result.messages]);
  setPage(page + 1);
  setHasMore(page < result.total_pages);
};
```

## 🔄 与 checkpoint 分页的对比

### 示例数据结构

**`/api/chat/history` (Checkpoint 分页):**
```json
{
  "total": 63,  // 63 个 checkpoint
  "messages": [
    {
      "checkpoint_id": "xxx",
      "messages": [消息1, 消息2, ..., 消息30]  // 一个 checkpoint 包含 30 条消息
    }
  ]
}
```

**`/api/chat/messages` (消息分页):**
```json
{
  "total": 30,  // 30 条消息
  "messages": [消息1, 消息2, 消息3, 消息4, 消息5]  // 直接是单条消息列表
}
```

## 📊 性能说明

- **优化点**: 只获取最新的 checkpoint（包含完整对话历史）
- **适用范围**: 消息总数 < 10,000 条
- **推荐分页大小**: 20-50 条/页

## 🧪 测试

运行测试脚本：

```bash
cd /Users/devyk/Data/code/AI/kaflow-py
bash tests/test_memory_api_curl.sh
```

查看测试 6-7 的输出，验证单条消息分页是否正常工作。

## 📞 支持

如有问题，请联系：
- 邮箱: yang1001yk@gmail.com
- GitHub: https://github.com/yangkun19921001

