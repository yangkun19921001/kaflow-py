#!/bin/bash

# KaFlow-Py API 测试脚本
# 使用 curl 测试所有 API 接口

BASE_URL="http://localhost:8102"

echo "🚀 KaFlow-Py API 测试脚本"
echo "=========================="

CONFIG_ID=$1
USER_INPUT=$2

# 检查参数
if [ -z "$CONFIG_ID" ] || [ -z "$USER_INPUT" ]; then
    echo "用法: $0 <CONFIG_ID> <USER_INPUT>"
    echo "示例: $0 3 '分别看下这台设备的路由配置和内存信息,设备ID: a028e0ba12656e613afac286244960ad'"
    echo "注意: CONFIG_ID 应该是整数，不要加引号"
    exit 1
fi

echo "配置ID: $CONFIG_ID"
echo "用户输入: $USER_INPUT"
echo ""

# 1. 健康检查
echo "1. 健康检查..."
curl -v -s "$BASE_URL/health" | jq '.'
echo ""

# 2. 获取配置列表
echo "2. 获取配置列表..."
curl -v -s "$BASE_URL/api/configs" | jq '.configs[] | {id, name, cached}'
echo ""

# 3. 测试聊天流式接口
echo "3. 测试聊天流式接口..."
echo "执行命令:"
echo "curl -X POST '$BASE_URL/api/chat/stream' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Accept: text/event-stream' \\"
echo "  -d '{\"config_id\": $CONFIG_ID, \"messages\": [{\"role\": \"user\", \"content\": \"$USER_INPUT\"}]}' \\"
echo "  --no-buffer"
echo ""

# 执行流式请求 - 注意这里 config_id 不加引号，作为整数传递
curl -v -X POST "$BASE_URL/api/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{\"config_id\": $CONFIG_ID, \"messages\": [{\"role\": \"user\", \"content\": \"$USER_INPUT\"}]}" \
  --no-buffer
