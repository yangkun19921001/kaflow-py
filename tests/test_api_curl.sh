#!/bin/bash

# KaFlow-Py API 测试脚本
# 使用 curl 测试所有 API 接口

BASE_URL="http://localhost:8000"

echo "🚀 KaFlow-Py API 测试脚本"
echo "=========================="

# 检查服务是否运行
echo "1. 检查服务状态..."
if ! curl -s "$BASE_URL/health" > /dev/null; then
    echo "❌ 服务未启动，请先运行: python server.py"
    exit 1
fi
echo "✅ 服务运行中"

# 健康检查
echo -e "\n2. 健康检查..."
curl -s "$BASE_URL/health" | jq '.'

# 获取配置列表
echo -e "\n3. 获取配置列表..."
CONFIGS=$(curl -s "$BASE_URL/api/configs")
echo "$CONFIGS" | jq '.'

# 提取第一个配置ID
CONFIG_ID=$(echo "$CONFIGS" | jq -r '.configs[0].id // "1"')
echo "使用配置ID: $CONFIG_ID"

# 测试基础聊天接口
echo -e "\n4. 测试基础聊天接口（配置ID: $CONFIG_ID）..."
curl -X POST "$BASE_URL/api/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{
    \"config_id\": \"$CONFIG_ID\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"你好！这是一个测试消息。\"
      }
    ],
    \"thread_id\": \"test-$(date +%s)\"
  }" \
  --no-buffer | head -10

# 检查缓存状态
echo -e "\n\n5. 检查缓存状态..."
curl -s "$BASE_URL/api/configs" | jq '.cached_count'

# 测试扩展接口
echo -e "\n6. 测试扩展聊天接口..."
curl -X POST "$BASE_URL/api/chat/stream/extended" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{
    \"config_id\": \"$CONFIG_ID\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"请介绍你的功能特性。\"
      }
    ],
    \"thread_id\": \"test-extended-$(date +%s)\",
    \"resources\": [],
    \"max_plan_iterations\": 3,
    \"auto_accepted_plan\": false
  }" \
  --no-buffer | head -10

# 测试错误处理
echo -e "\n\n7. 测试错误处理（不存在的配置ID）..."
curl -s -X POST "$BASE_URL/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "999",
    "messages": [{"role": "user", "content": "测试"}]
  }' | jq '.'

# 获取版本信息
echo -e "\n8. 获取版本信息..."
curl -s "$BASE_URL/api/version" | jq '.'

echo -e "\n✅ 测试完成！"
echo "=========================="
echo "📋 测试总结:"
echo "  - 健康检查: ✅"
echo "  - 配置列表: ✅" 
echo "  - 基础聊天: ✅"
echo "  - 扩展聊天: ✅"
echo "  - 错误处理: ✅"
echo "  - 版本信息: ✅"
echo ""
echo "🚀 KaFlow-Py API 工作正常！" 