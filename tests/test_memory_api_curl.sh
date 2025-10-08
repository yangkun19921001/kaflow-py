#!/bin/bash

# KaFlow-Py Memory API 测试脚本
# 测试内存相关接口

BASE_URL="http://localhost:8102"

echo "🚀 KaFlow-Py Memory API 测试脚本"
echo "===================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


# echo "================================"
# echo "测试 1: 获取会话列表（所有用户）"
# echo "================================"
# curl -X POST "${BASE_URL}/api/chat/threads" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "page": 1,
#     "page_size": 5,
#     "order": "desc"
#   }' | jq '.'

echo ""
echo "================================"
echo "测试 2: 获取会话列表（指定用户）"
echo "================================"
curl -X POST "${BASE_URL}/api/chat/threads" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "yang1001yk@gmail.com",
    "page": 1,
    "page_size": 50,
    "order": "desc"
  }' | jq '.'

# echo ""
# echo "================================"
# echo "测试 3: 获取历史消息（第1页）"
# echo "================================"
# curl -X POST "${BASE_URL}/api/chat/history" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "thread_id": "yang1001yk@gmail.com_ebb74d1f-d3fe-429b-8c94-c873fcf2f425_1",
#     "page": 1,
#     "page_size": 2,
#     "order": "desc"
#   }' | jq 

# echo ""
# echo "================================"
# echo "测试 4: 获取历史消息（第2页）"
# echo "================================"
# curl -X POST "${BASE_URL}/api/chat/history" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "thread_id": "yang1001yk@gmail.com_3cb83f36-85a9-47d1-a2df-4df2e8eced86_4",
#     "page": 2,
#     "page_size": 2,
#     "order": "desc"
#   }' | jq 

echo ""
echo "================================"
echo "测试 5: 获取历史消息（第3页）"
echo "================================"
curl -X POST "${BASE_URL}/api/chat/history" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "yang1001yk@gmail.com_f5bdab0b-961f-467f-a013-1f98cc2ac259_1",
    "page": 1,
    "page_size": 10,
    "order": "desc"
  }' | jq 

# echo ""
# echo "================================"
# echo "测试 6: 获取展平消息（单条消息分页 - 第1页）"
# echo "================================"
# curl -X POST "${BASE_URL}/api/chat/messages" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "thread_id": "yang1001yk@gmail.com_f5bdab0b-961f-467f-a013-1f98cc2ac259_1",
#     "page": 1,
#     "page_size": 100,
#     "order": "desc"
#   }' | jq 

# echo ""
# echo "================================"
# echo "测试 7: 获取展平消息（单条消息分页 - 第2页）"
# echo "================================"
# curl -X POST "${BASE_URL}/api/chat/messages" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "thread_id": "yang1001yk@gmail.com_3cb83f36-85a9-47d1-a2df-4df2e8eced86_4",
#     "page": 2,
#     "page_size": 5,
#     "order": "desc"
#   }' | jq 



# echo ""
# echo "================================"
# echo "测试 8: 获取展平消息（单条消息分页 - 所有）"
# echo "================================"
# curl -X POST "${BASE_URL}/api/chat/messages" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "thread_id": "yang1001yk@gmail.com_68e3d1c5-2594-4895-9e11-3152ec7279e3_4",
#     "page": 1,
#     "page_size": 100,   
#     "order": "desc"
#   }' | jq 

# echo ""
# echo "================================"
# echo "验证说明："
# echo "- Checkpoint 分页（测试3-5）：每页返回不同的 checkpoint"
# echo "- 消息分页（测试6-7）：每页返回不同的单条消息"
# echo "- 推荐使用 /api/chat/messages 获取对话历史"
# echo "================================"

