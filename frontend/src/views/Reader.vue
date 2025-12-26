<template>
  <div class="flex flex-col gap-8">
    <div v-if="loading" class="text-center py-12 text-muted-foreground text-lg">
      加载中...
    </div>

    <div v-else-if="items.length === 0" class="text-center py-16 px-8 text-muted-foreground">
      <p class="my-2 text-lg">暂无RSS条目</p>
      <p class="text-sm text-muted-foreground/70">前往管理页面添加RSS源</p>
    </div>

    <div v-else class="flex flex-col gap-6">
      <Card v-for="item in items" :key="item.id"
        class="cursor-pointer transition-all hover:shadow-lg hover:-translate-y-0.5"
        @click="toggleDescription(item.id)">
        <CardHeader>
          <h3 class="text-xl font-semibold m-0 mb-2 leading-snug">
            {{ item.title || "无标题" }}
          </h3>
          <div class="flex gap-4 text-sm text-muted-foreground flex-wrap">
            <Badge variant="secondary">{{ getFeedName(item.feed_id) }}</Badge>
            <span class="text-muted-foreground/70">{{
              formatDate(item.published || item.created_at)
            }}</span>
          </div>
        </CardHeader>

        <CardContent>
          <!-- AI 总结部分（引用样式） -->
          <blockquote v-if="item.ai_summary"
            class="my-4 pl-4 border-l-4 border-primary/50 italic text-muted-foreground">
            <p class="leading-relaxed m-0">
              {{ item.ai_summary }}
            </p>
          </blockquote>

          <!-- 原文部分（默认隐藏，点击 card 时显示） -->
          <div v-if="item.description && expandedDescriptions[item.id]" class="my-4 relative">
            <div
              class="text-muted-foreground leading-relaxed text-sm [&_p]:mb-2 [&_p:last-child]:mb-0 overflow-hidden relative"
              v-html="formatDescription(item.description)" @click.stop></div>
          </div>

          <div class="flex justify-between items-center mt-4 pt-4 border-t">
            <a :href="item.link" target="_blank" rel="noopener noreferrer" @click.stop="openItem(item)"
              class="text-primary no-underline font-medium transition-colors hover:text-primary/80">
              阅读原文 →
            </a>
            <span v-if="item.author" class="text-sm text-muted-foreground">作者: {{ item.author }}</span>
          </div>
        </CardContent>
      </Card>
    </div>

    <div v-if="total > items.length" class="text-center py-8">
      <Button @click="loadMore" :disabled="loadingMore">
        {{ loadingMore ? "加载中..." : `加载更多 (${items.length}/${total})` }}
      </Button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from "vue";
import { useRoute } from "vue-router";
import { itemsApi } from "../api";
import { format } from "date-fns";
import Button from "@/components/ui/button.vue";
import Card from "@/components/ui/card.vue";
import CardHeader from "@/components/ui/card-header.vue";
import CardContent from "@/components/ui/card-content.vue";
import Badge from "@/components/ui/badge.vue";

const route = useRoute();

// 从 App.vue 注入共享状态
const selectedFeedId = inject("selectedFeedId");
const sortBy = inject("sortBy");
const feeds = inject("feeds");
const sortedFeeds = inject("sortedFeeds");

const items = ref([]);
const loading = ref(false);
const loadingMore = ref(false);
const total = ref(0);
const pageSize = 50;
const currentPage = ref(0);
const expandedDescriptions = ref({}); // 跟踪哪些条目的 description 已展开

const formatDate = (date) => {
  if (!date) return "未知";
  try {
    // 后端现在返回的时间格式是 ISO 8601 格式，带 UTC 时区标识（Z 后缀）
    // 例如: "2025-12-25T18:05:26Z" 或 "2025-12-25T18:05:26.355749Z"
    // 如果时间字符串没有时区信息，假设它是 UTC 时间并添加 Z
    let dateStr = date;
    if (typeof dateStr === "string") {
      // 如果时间字符串没有时区信息（没有 Z、+ 或 -），添加 Z 表示 UTC
      if (
        !dateStr.includes("Z") &&
        !dateStr.includes("+") &&
        !dateStr.match(/[+-]\d{2}:\d{2}$/)
      ) {
        dateStr = dateStr + "Z";
      }
    }
    // new Date() 会自动将 UTC 时间（带 Z）转换为用户本地时间
    const dateObj = new Date(dateStr);
    // 如果日期无效，返回未知
    if (isNaN(dateObj.getTime())) {
      console.warn("无效的日期:", date);
      return "未知";
    }
    // 使用 date-fns 格式化，format 函数会使用本地时区显示
    // dateObj 已经是本地时间对象（new Date 会自动将 UTC 转换为本地时间）
    return format(dateObj, "yyyy-MM-dd HH:mm");
  } catch (error) {
    console.error("日期格式化错误:", error, date);
    return "未知";
  }
};

const formatDescription = (html) => {
  if (!html) return "";

  // 保留 p 标签的段落结构，只清理危险标签
  let formatted = html
    // 移除 script 和 style 标签及其内容（安全考虑）
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "")
    // 移除可能有安全风险的标签
    .replace(
      /<(iframe|object|embed|form|input|button)[^>]*>[\s\S]*?<\/\1>/gi,
      ""
    )
    // 移除 onclick 等事件属性
    .replace(/\s+on\w+\s*=\s*["'][^"']*["']/gi, "");

  // 清理多余的空白，但保留段落结构
  formatted = formatted.replace(/>\s+</g, "><").trim();

  // 限制长度：最多500个字符（中文字符和英文字符都算1个）
  const textContent = formatted.replace(/<[^>]*>/g, ""); // 获取纯文本用于计算长度
  const charCount = textContent.length;

  if (charCount > 500) {
    // 如果超过500字符，截断到500字符
    let truncated = "";
    let textLength = 0;
    let i = 0;

    while (i < formatted.length && textLength < 500) {
      const char = formatted[i];

      if (char === "<") {
        // 处理 HTML 标签
        const tagEnd = formatted.indexOf(">", i);
        if (tagEnd !== -1) {
          truncated += formatted.substring(i, tagEnd + 1);
          i = tagEnd + 1;
        } else {
          break;
        }
      } else {
        truncated += char;
        textLength++;
        i++;
      }
    }

    // 确保 HTML 标签闭合，移除未闭合的标签
    formatted = truncated.replace(/<[^>]*$/, "");

    // 如果截断了，添加省略号
    if (textLength >= 500) {
      formatted += "...";
    }
  }

  return formatted;
};

const getFeedName = (feedId) => {
  const feed = feeds.value.find((f) => f.id === feedId);
  return feed ? feed.title || feed.url : `源 #${feedId}`;
};

const loadItems = async (reset = true) => {
  if (reset) {
    currentPage.value = 0;
    items.value = [];
  }

  loading.value = reset;
  loadingMore.value = !reset;

  try {
    const params = {
      limit: pageSize,
      offset: currentPage.value * pageSize,
    };
    if (selectedFeedId.value) {
      params.feed_id = selectedFeedId.value;
    }

    const res = await itemsApi.list(params);
    if (reset) {
      items.value = res.data.items;
    } else {
      items.value.push(...res.data.items);
    }
    total.value = res.data.total;
    currentPage.value++;

    // 调试：检查 AI 总结数据
    const itemsWithSummary = res.data.items.filter((item) => item.ai_summary);
    console.log(
      `📊 加载了 ${res.data.items.length} 个条目，其中 ${itemsWithSummary.length} 个有 AI 总结`
    );
    if (itemsWithSummary.length > 0) {
      console.log("✅ 有 AI 总结的条目示例:", itemsWithSummary[0]);
    } else if (res.data.items.length > 0) {
      console.log("⚠️ 没有 AI 总结，示例条目:", res.data.items[0]);
    }
  } catch (error) {
    console.error("Failed to load items:", error);
    alert("加载失败: " + (error.response?.data?.detail || error.message));
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
};

const loadMore = () => {
  loadItems(false);
};

const openItem = (item) => {
  window.open(item.link, "_blank", "noopener,noreferrer");
};

const toggleDescription = (itemId) => {
  expandedDescriptions.value[itemId] = !expandedDescriptions.value[itemId];
};

// 监听 selectedFeedId 变化，重新加载数据
watch(selectedFeedId, () => {
  loadItems(true);
});

onMounted(() => {
  // 如果从路由参数中获取了feed_id，加载该源的内容
  if (route.query.feed_id) {
    loadItems();
  } else {
    loadItems();
  }
});

// 监听路由变化，如果feed_id改变则重新加载
watch(
  () => route.query.feed_id,
  (newFeedId) => {
    if (newFeedId) {
      selectedFeedId.value = newFeedId.toString();
      loadItems(true);
    }
  }
);
</script>

<style scoped>
/* 响应式样式已移至 App.vue */
</style>
