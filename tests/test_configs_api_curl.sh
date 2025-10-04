#!/bin/bash

# KaFlow-Py Configs API 测试脚本
# 测试配置列表相关接口

BASE_URL="http://localhost:8102"

echo "🚀 KaFlow-Py Configs API 测试脚本"
echo "===================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 健康检查
echo -e "${BLUE}[测试 1/5]${NC} 健康检查"
echo "--------------------------------------"
echo "请求: GET $BASE_URL/health"
echo ""
curl -s "$BASE_URL/health" | jq '.'
echo ""
echo ""

# 2. 获取版本信息
echo -e "${BLUE}[测试 2/5]${NC} 获取版本信息"
echo "--------------------------------------"
echo "请求: GET $BASE_URL/api/version"
echo ""
curl -s "$BASE_URL/api/version" | jq '.'
echo ""
echo ""

# 3. 获取完整配置列表
echo -e "${BLUE}[测试 3/5]${NC} 获取完整配置列表"
echo "--------------------------------------"
echo "请求: GET $BASE_URL/api/configs"
echo ""
CONFIGS_RESPONSE=$(curl -s "$BASE_URL/api/configs")
echo "$CONFIGS_RESPONSE" | jq '.'
echo ""
echo ""

# 4. 获取配置列表统计信息
echo -e "${BLUE}[测试 4/5]${NC} 配置统计信息"
echo "--------------------------------------"
echo "总配置数: $(echo "$CONFIGS_RESPONSE" | jq -r '.total')"
echo "已缓存配置数: $(echo "$CONFIGS_RESPONSE" | jq -r '.cached_count')"
echo "时间戳: $(echo "$CONFIGS_RESPONSE" | jq -r '.timestamp')"
echo ""
echo ""

# 5. 显示所有配置的简要信息
echo -e "${BLUE}[测试 5/5]${NC} 配置详细列表"
echo "--------------------------------------"
echo "$CONFIGS_RESPONSE" | jq -r '.configs[] | "ID: \(.id) | 名称: \(.name) | 文件: \(.file_name) | 已缓存: \(.cached) | Agents: \(.agents_count) | 节点: \(.nodes_count)"'
echo ""
echo ""

# 6. 显示特定配置的详细信息（如果有配置）
CONFIG_COUNT=$(echo "$CONFIGS_RESPONSE" | jq -r '.total')
if [ "$CONFIG_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}示例：第一个配置的详细信息${NC}"
    echo "--------------------------------------"
    echo "$CONFIGS_RESPONSE" | jq '.configs[0]'
    echo ""
    
    FIRST_CONFIG_ID=$(echo "$CONFIGS_RESPONSE" | jq -r '.configs[0].id')
    echo -e "${GREEN}提示：您可以使用配置 ID '$FIRST_CONFIG_ID' 来测试聊天接口${NC}"
    echo "命令示例:"
    echo "  ./test_chat_stream_api_curl.sh $FIRST_CONFIG_ID '你好'"
    echo ""
else
    echo -e "${YELLOW}⚠️  没有找到任何配置文件${NC}"
    echo "请在 src/core/config/ 目录下添加配置文件（需要包含 id 字段）"
    echo ""
fi

echo "===================================="
echo -e "${GREEN}✅ 测试完成！${NC}"
echo ""

# 显示 curl 命令示例
echo "📝 手动测试命令:"
echo "--------------------------------------"
echo "# 获取配置列表"
echo "curl -s '$BASE_URL/api/configs' | jq '.'"
echo ""
echo "# 获取配置列表（仅显示 ID 和名称）"
echo "curl -s '$BASE_URL/api/configs' | jq '.configs[] | {id, name, cached}'"
echo ""
echo "# 获取配置列表（仅显示统计）"
echo "curl -s '$BASE_URL/api/configs' | jq '{total, cached_count, timestamp}'"
echo ""

