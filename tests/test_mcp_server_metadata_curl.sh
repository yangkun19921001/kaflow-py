#!/bin/bash

# KaFlow-Py MCP Server Metadata API 测试脚本
# 测试 MCP 服务器元数据接口

BASE_URL="http://localhost:8102"

echo "🚀 KaFlow-Py MCP Server Metadata API 测试脚本"
echo "==============================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查参数
TEST_TYPE=${1:-"all"}

if [ "$TEST_TYPE" != "all" ] && [ "$TEST_TYPE" != "stdio" ] && [ "$TEST_TYPE" != "sse" ] && [ "$TEST_TYPE" != "error" ]; then
    echo "用法: $0 [all|stdio|sse|error]"
    echo ""
    echo "参数说明:"
    echo "  all    - 运行所有测试（默认）"
    echo "  stdio  - 仅测试 stdio 类型"
    echo "  sse    - 仅测试 sse 类型"
    echo "  error  - 仅测试错误处理"
    echo ""
    echo "示例:"
    echo "  $0           # 运行所有测试"
    echo "  $0 stdio     # 仅测试 stdio 类型"
    echo ""
    exit 1
fi

# 测试 stdio 类型
test_stdio() {
    echo -e "${BLUE}[测试 stdio]${NC} mcp-server-fetch (网页抓取工具)"
    echo "--------------------------------------"
    echo "请求: POST $BASE_URL/api/mcp/server/metadata"
    echo ""
    
    REQUEST_DATA='{
  "transport": "stdio",
  "command": "uvx",
  "args": ["mcp-server-fetch"],
  "timeout_seconds": 60
}'
    
    echo "请求数据:"
    echo "$REQUEST_DATA" | jq '.'
    echo ""
    
    echo "执行请求..."
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/mcp/server/metadata" \
      -H "Content-Type: application/json" \
      -d "$REQUEST_DATA")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    echo "HTTP 状态码: $HTTP_CODE"
    echo ""
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ 请求成功${NC}"
        echo ""
        echo "响应数据:"
        echo "$BODY" | jq '.'
        echo ""
        
        # 显示工具统计
        TOOL_COUNT=$(echo "$BODY" | jq '.tools | length')
        echo -e "${GREEN}找到 $TOOL_COUNT 个工具:${NC}"
        echo "$BODY" | jq -r '.tools[] | "  • \(.name): \(.description // "N/A")"'
        echo ""
    else
        echo -e "${RED}❌ 请求失败${NC}"
        echo "$BODY" | jq '.'
        echo ""
    fi
}

# 测试 sse 类型
test_sse() {
    echo -e "${BLUE}[测试 sse]${NC} SSE 类型 MCP 服务器"
    echo "--------------------------------------"
    echo "请求: POST $BASE_URL/api/mcp/server/metadata"
    echo ""
    
    REQUEST_DATA='{
  "transport": "sse",
  "url": "http://10.1.16.4:8000/mcp/sse",
  "timeout_seconds": 60
}'
    
    echo "请求数据:"
    echo "$REQUEST_DATA" | jq '.'
    echo ""
    
    echo "执行请求..."
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/mcp/server/metadata" \
      -H "Content-Type: application/json" \
      -d "$REQUEST_DATA")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    echo "HTTP 状态码: $HTTP_CODE"
    echo ""
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ 请求成功${NC}"
        echo ""
        echo "响应数据:"
        echo "$BODY" | jq '.'
        echo ""
        
        # 显示工具统计
        TOOL_COUNT=$(echo "$BODY" | jq '.tools | length')
        echo -e "${GREEN}找到 $TOOL_COUNT 个工具:${NC}"
        echo "$BODY" | jq -r '.tools[] | "  • \(.name): \(.description // "N/A")"'
        echo ""
    else
        echo -e "${YELLOW}⚠️  SSE 服务器未运行或连接失败${NC}"
        echo "$BODY" | jq '.'
        echo ""
        echo "提示: 确保 SSE MCP 服务器正在 http://localhost:3000/sse 运行"
        echo ""
    fi
}

# 测试错误处理
test_error_handling() {
    echo -e "${BLUE}[测试错误处理]${NC} 缺少必需参数"
    echo "--------------------------------------"
    echo "请求: POST $BASE_URL/api/mcp/server/metadata"
    echo ""
    
    # 测试 1: stdio 类型缺少 command
    REQUEST_DATA='{
  "transport": "stdio"
}'
    
    echo "测试 1: stdio 类型缺少 command 参数"
    echo "请求数据:"
    echo "$REQUEST_DATA" | jq '.'
    echo ""
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/mcp/server/metadata" \
      -H "Content-Type: application/json" \
      -d "$REQUEST_DATA")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    echo "HTTP 状态码: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "500" ]; then
        echo -e "${GREEN}✅ 正确返回错误状态码${NC}"
    else
        echo -e "${RED}❌ 应该返回错误状态码${NC}"
    fi
    
    echo "响应:"
    echo "$BODY" | jq '.'
    echo ""
    echo ""
    
    # 测试 2: 不支持的 transport 类型
    REQUEST_DATA='{
  "transport": "invalid_type",
  "command": "test"
}'
    
    echo "测试 2: 不支持的 transport 类型"
    echo "请求数据:"
    echo "$REQUEST_DATA" | jq '.'
    echo ""
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/mcp/server/metadata" \
      -H "Content-Type: application/json" \
      -d "$REQUEST_DATA")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    echo "HTTP 状态码: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "500" ]; then
        echo -e "${GREEN}✅ 正确返回错误状态码${NC}"
    else
        echo -e "${RED}❌ 应该返回错误状态码${NC}"
    fi
    
    echo "响应:"
    echo "$BODY" | jq '.'
    echo ""
}

# 运行测试
echo "测试模式: $TEST_TYPE"
echo ""

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "stdio" ]; then
    test_stdio
    echo ""
fi

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "sse" ]; then
    test_sse
    echo ""
fi

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "error" ]; then
    test_error_handling
    echo ""
fi

echo "==============================================="
echo -e "${GREEN}✅ 测试完成！${NC}"
echo ""

# 显示更多 MCP 服务器示例
echo "📝 其他常用 MCP 服务器测试命令:"
echo "--------------------------------------"
echo ""

echo "1. mcp-server-filesystem (文件系统操作):"
echo "curl -X POST '$BASE_URL/api/mcp/server/metadata' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"transport\": \"stdio\","
echo "    \"command\": \"uvx\","
echo "    \"args\": [\"mcp-server-filesystem\", \"/tmp\"],"
echo "    \"timeout_seconds\": 60"
echo "  }' | jq '.'"
echo ""

echo "2. mcp-server-github (GitHub 操作):"
echo "curl -X POST '$BASE_URL/api/mcp/server/metadata' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"transport\": \"stdio\","
echo "    \"command\": \"uvx\","
echo "    \"args\": [\"mcp-server-github\"],"
echo "    \"env\": {\"GITHUB_TOKEN\": \"your_token\"},"
echo "    \"timeout_seconds\": 60"
echo "  }' | jq '.'"
echo ""

echo "3. mcp-server-brave-search (Brave 搜索):"
echo "curl -X POST '$BASE_URL/api/mcp/server/metadata' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"transport\": \"stdio\","
echo "    \"command\": \"uvx\","
echo "    \"args\": [\"mcp-server-brave-search\"],"
echo "    \"env\": {\"BRAVE_API_KEY\": \"your_key\"},"
echo "    \"timeout_seconds\": 60"
echo "  }' | jq '.'"
echo ""

echo "4. mcp-server-postgres (PostgreSQL):"
echo "curl -X POST '$BASE_URL/api/mcp/server/metadata' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"transport\": \"stdio\","
echo "    \"command\": \"uvx\","
echo "    \"args\": [\"mcp-server-postgres\", \"postgresql://user:pass@localhost/db\"],"
echo "    \"timeout_seconds\": 60"
echo "  }' | jq '.'"
echo ""

