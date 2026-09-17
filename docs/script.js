"use strict";
let mapping = {};
const dbStorage = {
  dbName: "vvSearchCache",
  dbVersion: 1,
  async init() {
    if (this._dbPromise) return this._dbPromise;
    this._dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);
      request.onerror = (event) => {
        reject(event.target.error);
      };
      request.onsuccess = (event) => {
        this.db = event.target.result;
        resolve(this.db);
      };
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains("indices"))
          db.createObjectStore("indices", { keyPath: "key" });
        if (!db.objectStoreNames.contains("mappings"))
          db.createObjectStore("mappings", { keyPath: "key" });
        if (!db.objectStoreNames.contains("databases"))
          db.createObjectStore("databases", { keyPath: "key" });
      };
    });
    return this._dbPromise;
  },
  async getItem(storeName, key) {
    try {
      await this.init();
      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(storeName, "readonly");
        const store = transaction.objectStore(storeName);
        const request = store.get(key);
        request.onsuccess = () => {
          resolve(request.result ? request.result.value : null);
        };
        request.onerror = (event) => {
          reject(event.target.error);
        };
      });
    } catch (error) {
      return null;
    }
  },
  async setItem(storeName, key, value) {
    try {
      await this.init();
      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(storeName, "readwrite");
        const store = transaction.objectStore(storeName);
        const request = store.put({ key, value });
        request.onsuccess = () => {
          resolve();
        };
        request.onerror = (event) => {
          reject(event.target.error);
        };
      });
    } catch (error) {
      throw error;
    }
  },
  async removeItem(storeName, key) {
    try {
      await this.init();
      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(storeName, "readwrite");
        const store = transaction.objectStore(storeName);
        const request = store.delete(key);
        request.onsuccess = () => {
          resolve();
        };
        request.onerror = (event) => {
          reject(event.target.error);
        };
      });
    } catch (error) {
      throw error;
    }
  },
  async getAllKeys(storeName) {
    try {
      await this.init();
      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(storeName, "readonly");
        const store = transaction.objectStore(storeName);
        const request = store.getAllKeys();
        request.onsuccess = () => {
          resolve(request.result);
        };
        request.onerror = (event) => {
          reject(event.target.error);
        };
      });
    } catch (error) {
      return [];
    }
  },
};
async function loadMapping() {
  try {
    const cachedMapping = await dbStorage.getItem("mappings", "mapping");
    if (cachedMapping) return cachedMapping;
    try {
      const localMapping = localStorage.getItem("mapping");
      if (localMapping) {
        const mappingData = JSON.parse(localMapping);
        try {
          await dbStorage.setItem("mappings", "mapping", mappingData);
          localStorage.removeItem("mapping");
        } catch (e) {}
        return mappingData;
      }
    } catch (e) {}
    const response = await fetch("./mapping.json", {
      referrerPolicy: "no-referrer",
      mode: "cors",
      credentials: "omit",
    });
    if (!response.ok) throw new Error("Failed to load mapping.json");
    const mappingData = await response.json();
    try {
      await dbStorage.setItem("mappings", "mapping", mappingData);
    } catch (e) {
      try {
        localStorage.setItem("mapping", JSON.stringify(mappingData));
      } catch (e) {}
    }
    return mappingData;
  } catch (error) {
    return {};
  }
}
const AppState = {
  isSearching: false,
  searchResults: [],
  currentPage: 1,
  itemsPerPage: 20,
  hasMoreResults: true,
  cachedResults: [],
  displayedCount: 0,
  showWatermark: true,
  dbLoaded: false,
  dbLoading: false,
};
/* UIController 与 CONFIG 已整条删除(2026-09-17)。
   依据是实测而非估计: updateSearchFormPosition 从来没有被任何地方调用过(全文件只有它
   自己的定义), 所以"随机提示语"这个功能其实从未生效过 —— #randomStringDisplay 一直
   是空的。那个元素现在改成检索结论行 #resultStatus, 由下面的 announce() 负责写。 */

/* 检索结论播报。
   为什么需要它: #resultStatus 是一个**常驻**的 role="status" aria-live="polite" 区域,
   读屏用户靠它得知"检索中"以及"结果是什么" —— 否则提交检索之后得不到任何反馈,
   包括"没有结果"这件事(审查里的一条 P2)。 */
function announce(text) {
  const el = document.getElementById("resultStatus");
  if (el) el.textContent = text || "";
}
class SearchController {
  static validateSearchInput(query) {
    return query && query.trim().length > 0;
  }

  static async performSearch(query, minRatio, minSimilarity) {
    // 纯本地搜索：字幕数据已随站点部署（./subtitle_db），无需远程 API
    if (window.subtitleDB && window.subtitleDB.isLoaded) {
      try {
        const localResults = await window.subtitleDB.search(
          query,
          minRatio,
          minSimilarity,
        );

        if (localResults && Array.isArray(localResults)) {
          return {
            status: "success",
            data: localResults,
            count: localResults.length,
          };
        } else if (
          localResults &&
          localResults.status === "success" &&
          Array.isArray(localResults.data)
        ) {
          return localResults;
        }
      } catch (error) {
        console.log("本地搜索失败", error);
        throw error;
      }
    }
    return { status: "success", data: [], count: 0 };
  }
}
async function handleSearch(event) {
  event.preventDefault();
  const query = document.getElementById("query").value.trim();
  if (!query) return;
  const minRatioRaw = parseInt(document.getElementById("minRatio").value, 10);
  const minSimilarityRaw = parseFloat(document.getElementById("minSimilarity").value);
  // 注意用 isFinite 而不是 ||: 用户输入 0 表示"不过滤", 用 || 会把 0 变成默认 50
  const minRatio = Number.isFinite(minRatioRaw) ? minRatioRaw : 50;
  const minSimilarity = Number.isFinite(minSimilarityRaw) ? minSimilarityRaw : 0;
  const searchForm = document.getElementById("searchForm");
  searchForm.classList.add("searching");
  startNaturalLoadingBar();
  announce("正在检索…");

  try {
    const results = await SearchController.performSearch(
      query,
      minRatio,
      minSimilarity,
    );

    if (results && results.status === "success") {
      // 爱染诚画面优先 / 仅显示含爱染诚画面（高级选项）
      const aizenFirst = document.getElementById("aizenFirst")?.checked !== false;
      const aizenOnly = document.getElementById("aizenOnly")?.checked === true;
      let data = results.data.slice();
      if (aizenOnly) data = data.filter((r) => r.aizen);
      if (aizenFirst) {
        data.sort((a, b) => {
          if ((b.aizen || 0) !== (a.aizen || 0)) return (b.aizen || 0) - (a.aizen || 0);
          if (b.match_ratio !== a.match_ratio) return b.match_ratio - a.match_ratio;
          return (b.exact_match || 0) - (a.exact_match || 0);
        });
      }
      // 注意：results 是 const，不能重赋值，用新对象承载处理后的结果
      const searchData = { status: "success", data, count: data.length };
      AppState.cachedResults = searchData.data;
      AppState.hasMoreResults = searchData.data.length > AppState.itemsPerPage;
      AppState.displayedCount = 0;

      displayResults(searchData);
      completeLoadingBar();
      // 结论既要给眼睛看, 也要播报给读屏(见 announce() 的说明)。
      // 无结果时 data 里是 db_search.js 包的那个 {count:0} 包装对象, 不是真的记录。
      const noResult = data.length === 1 && data[0] && data[0].count === 0;
      announce(noResult ? "没有匹配的档案" : `找到 ${data.length} 条档案`);
    } else {
      throw new Error("Invalid search results format");
    }
  } catch (error) {
    console.error("Search error:", error);
    document.getElementById("errorDisplay").textContent =
      `搜索失败: ${error.message}`;
    document.getElementById("errorDisplay").style.display = "block";
    announce(`检索失败: ${error.message}`);
    completeLoadingBar();
  } finally {
    searchForm.classList.remove("searching");
  }
}
// 归档统计随语料实时计算 —— 原先写死在 index.html 里(显示"归档 4929 条"), 而语料经多轮
// 审核已增至 6783 条, 页面数字长期偏小。这类数字不应有第二个来源。
// 取库时两条路: window.SUBTITLE_DB(script 注入) 或 subtitleDB.load()(fetch gzip)。
function getSubtitleDb() {
  if (window.SUBTITLE_DB && Array.isArray(window.SUBTITLE_DB)) {
    return window.SUBTITLE_DB;
  }
  if (window.subtitleDB && Array.isArray(window.subtitleDB.db)) {
    return window.subtitleDB.db;
  }
  return null;
}

async function refreshArchiveStats() {
  const el = document.querySelector(".hero-stats");
  if (!el || !window.subtitleDB) return;
  try {
    if (!getSubtitleDb()) {
      // 兜底: 别让统计一直停在"加载中"(DB 拿不到时不该显示任何条数)
      const timeout = new Promise((_, reject) =>
        setTimeout(() => reject(new Error("subtitle db load timeout")), 5000),
      );
      await Promise.race([window.subtitleDB.load(), timeout]);
    }
    const db = getSubtitleDb();
    if (!db || !db.length) return;
    const eps = new Set(db.map((r) => String(r.f || "").slice(0, 4)));
    // 裸库记录用 d 表示"该帧命中爱染诚人脸集"; 检索结果里才被映射成 aizen(db_search.js)
    const aizen = db.filter((r) => r.d).length;
    el.textContent = `全 ${eps.size} 集 · 归档 ${db.length} 条 · 爱染诚登场 ${aizen} 条`;
  } catch (error) {
    // 加载失败时给可辨认的占位, 而不是留一个过期的旧数字在页面上
    el.textContent = "全 — 集 · 归档 — 条 · 爱染诚登场 — 条";
    console.error("归档统计加载失败:", error);
  }
}

async function initializeApp() {
  try {
    await dbStorage.init().catch((error) => {});
    mapping = await loadMapping();
    initializeScrollListener();

    if (
      window.subtitleDB &&
      !window.subtitleDB.isLoaded &&
      !window.subtitleDB.isLoading
    ) {
      window.subtitleDB
        .load()
        .then(() => {
          AppState.dbLoaded = true;
        })
        .catch((error) => {
          setTimeout(() => {
            window.subtitleDB.load().catch((err) => {});
          }, 3000);
        });
    }
    refreshArchiveStats();

    document
      .getElementById("searchForm")
      .addEventListener("submit", async (e) => {
        e.preventDefault();
        if (AppState.isSearching) return;
        AppState.isSearching = true;
        try {
          await handleSearch(e);
        } finally {
          AppState.isSearching = false;
        }
      });

    document.getElementById("query").addEventListener("keydown", (e) => {
      // isComposing: 中文输入法选词时也会发 Enter, 不拦下来会把没打完的拼音当成检索词提交
      if (e.key === "Enter" && !e.isComposing && e.keyCode !== 229) {
        e.preventDefault();
        if (AppState.isSearching) return;
        document
          .getElementById("searchForm")
          .dispatchEvent(new Event("submit"));
      }
    });

    document
      .getElementById("refreshDiv")
      .addEventListener("click", function () {
        location.reload();
      });
  } catch (error) {}
}
document.addEventListener("DOMContentLoaded", () => {
  const loadingBar = document.getElementById("loadingBar");
  if (loadingBar) {
    loadingBar.style.width = "0%";
    loadingBar.style.display = "none";
  }
  initializeApp();
  const toggleButton = document.getElementById("toggleAdvancedOptions");
  const advancedOptions = document.getElementById("advancedOptions");
  toggleButton.addEventListener("click", () => {
    const isExpanded = advancedOptions.classList.contains("show");
    if (!isExpanded) {
      advancedOptions.style.transition = "none";
      advancedOptions.classList.add("show");
      const height = advancedOptions.scrollHeight;
      advancedOptions.classList.remove("show");
      void advancedOptions.offsetHeight;
      advancedOptions.style.transition = "";
      advancedOptions.style.maxHeight = height + "px";
      advancedOptions.classList.add("show");
    } else {
      advancedOptions.style.maxHeight = "0";
      advancedOptions.classList.remove("show");
    }
    toggleButton.classList.toggle("active");
    toggleButton.setAttribute("aria-expanded", !isExpanded);
  });
});
function displayResults(data, append = false) {
  const resultsDiv = document.getElementById("results");

  document.getElementById("errorDisplay").style.display = "none";

  if (!append) {
    resultsDiv.innerHTML = "";
    AppState.displayedCount = 0;
  }

  /* 关键词分支已整条删除(2026-09-17)。依据是实测: 它的唯一入口是
     `data.data[0].type === "keywords"`, 而 6667 条语料里没有任何一条带 type 字段,
     所以这段代码从未执行过 —— #keywordsContainer 永远是空的。
     那些标签本身也只是一堆只绑了 click、没有 tabindex 的 <span>, 真被激活就是一处
     键盘不可达的交互; 要恢复这个功能, 请连键盘可达性一起做, 别只把这段抄回来。 */

  if (data.data && data.data.length === 1 && data.data[0].count === 0) {
    const noResultData = data.data[0];
    console.log("No results case:", {
      message: noResultData.message,
      suggestions: noResultData.suggestions,
    });

    if (!append) {
      const message =
        noResultData.message ||
        `未找到与 "${document.getElementById("query").value.trim()}" 匹配的结果`;
      const suggestions = noResultData.suggestions || [
        "检查输入是否正确",
        `尝试降低最小匹配率（当前：${document.getElementById("minRatio").value}%）`,
        `尝试降低最小相似度（当前：${document.getElementById("minSimilarity").value}）`,
        "尝试使用更简短的关键词",
      ];

      resultsDiv.innerHTML = `
                <div class="error-message">
                    <h2>${message}</h2>
                    <p>建议：</p>
                    <ul>
                        ${suggestions.map((suggestion) => `<li>${suggestion}</li>`).join("")}
                    </ul>
                </div>`;
    }
    AppState.hasMoreResults = false;
    return;
  }

  const fragment = document.createDocumentFragment();
  const startIndex = AppState.displayedCount;
  const endIndex = Math.min(
    startIndex + AppState.itemsPerPage,
    data.data.length,
  );
  const newResults = data.data.slice(startIndex, endIndex);

  AppState.hasMoreResults = endIndex < data.data.length;

  const cards = newResults
    .map((result) => {
      if (!result || typeof result !== "object") return null;
      const card = document.createElement("div");
      card.className = "result-card" + (result.aizen ? " is-aizen" : "");

      const episodeMatch = result.filename
        ? result.filename.match(/\[P(\d+)\]/)
        : null;
      const timeMatch = result.timestamp
        ? result.timestamp.match(/^(\d+)m(\d+)s$/)
        : null;
      const cleanFilename = result.filename
        ? result.filename
            .replace(/\[P(\d+)\].*?\s+/, "P$1 ")
            .replace(/\.json$/, "")
            .trim()
        : "";

      const frameKey = `${result.filename}|${result.timestamp}`;
      const frameFile = window.FRAMES_MAP ? window.FRAMES_MAP[frameKey] : null;

      // 时间戳超链接:跳转 bilibili
      let jumpHref = "";
      if (timeMatch && episodeMatch && frameFile) {
        const totalSeconds =
          parseInt(timeMatch[1]) * 60 + parseInt(timeMatch[2]);
        jumpHref = getBilibiliUrl(result.filename, totalSeconds) || "";
      }

      const cardContent = `
            <div class="result-content">
                <div class="result-text-block">
                    <h2>${episodeMatch ? `<span class="tag">${episodeMatch[1]}</span>${cleanFilename.replace(/P\d+/, "").trim()}` : cleanFilename}</h2>
                    <p class="result-text">${result.text || ""}</p>
                    ${
                      result.timestamp
                        ? `
                    <p class="result-meta">
                        ${
                          jumpHref
                            ? `<a class="ts-link" href="${jumpHref}" target="_blank" rel="noopener noreferrer" title="\u8df3\u8f6c bilibili \u89c6\u9891">${result.timestamp}</a>`
                            : result.timestamp
                        }
                        \u00b7
                        \u5339\u914d\u5ea6 ${result.match_ratio ? parseFloat(result.match_ratio).toFixed(1) : 0}% \u00b7
                        \u76f8\u4f3c\u5ea6 ${result.similarity ? (result.similarity * 100).toFixed(1) : 0}%
                    </p>`
                        : ""
                    }
                </div>
                ${
                  frameFile
                    ? `<div class="frame-thumb frame-zoomable" data-frame="${frameFile}" data-info="${cleanFilename} \u00b7 ${result.timestamp || ""}" role="button" tabindex="0" title="\u70b9\u51fb\u653e\u5927"><img src="frames/${frameFile}" alt="${result.text || ""}" loading="lazy" onerror="this.parentNode.classList.add('frame-missing')"><span class="zoom-hint" aria-hidden="true">\U0001F50D</span></div>`
                    : `<div class="frame-thumb frame-placeholder"><span>\u65e0\u5e27\u56fe</span></div>`
                }
            </div>
        `;

      card.innerHTML = cardContent;
      // 帧图:点击放大预览
      const zoom = card.querySelector(".frame-zoomable");
      if (zoom) {
        const frameFile2 = zoom.getAttribute("data-frame");
        const info = zoom.getAttribute("data-info");
        zoom.addEventListener("click", (e) => {
          e.stopPropagation();
          openPreviewFrame(frameFile2, info);
        });
        zoom.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openPreviewFrame(frameFile2, info);
          }
        });
      }
      return card;
    })
    .filter(Boolean);

  cards.forEach((card) => fragment.appendChild(card));
  resultsDiv.appendChild(fragment);

  AppState.displayedCount = endIndex;

  if (AppState.hasMoreResults) {
    let trigger = document.getElementById("scroll-trigger");
    if (!trigger) {
      trigger = document.createElement("div");
      trigger.id = "scroll-trigger";
      trigger.style.cssText = "height: 20px; margin: 20px 0;";

      if (window.currentObserver) {
        window.currentObserver.observe(trigger);
      }
    }
    resultsDiv.appendChild(trigger);
  }
}
function startNaturalLoadingBar() {
  const loadingBar = document.getElementById("loadingBar");
  loadingBar.style.transition = "";
  loadingBar.style.width = "0%";
  loadingBar.style.display = "block";
  if (loadingBar.interval) clearInterval(loadingBar.interval);
  let progress = 0;
  const targetProgress = 95;
  let speed = 0.5;
  loadingBar.interval = setInterval(() => {
    if (progress < 30) speed = 0.8;
    else if (progress < 60) speed = 0.4;
    else if (progress < 80) speed = 0.2;
    else speed = 0.1;
    progress += speed;
    if (progress >= targetProgress) {
      clearInterval(loadingBar.interval);
      progress = targetProgress;
    }
    loadingBar.style.width = `${progress}%`;
  }, 50);
}
function completeLoadingBar() {
  const loadingBar = document.getElementById("loadingBar");
  clearInterval(loadingBar.interval);
  loadingBar.style.transition = "width 0.3s ease-out";
  loadingBar.style.width = "100%";
}
function initializeScrollListener() {
  if (window.currentObserver) window.currentObserver.disconnect();

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (
          entry.isIntersecting &&
          AppState.hasMoreResults &&
          !AppState.isSearching
        ) {
          if (AppState.cachedResults.length > AppState.displayedCount) {
            displayResults(
              {
                status: "success",
                data: AppState.cachedResults,
                count: AppState.cachedResults.length,
              },
              true,
            );
          }
        }
      });
    },
    { root: null, rootMargin: "200px", threshold: 0.1 },
  );

  window.currentObserver = observer;

  const oldTrigger = document.getElementById("scroll-trigger");
  if (oldTrigger) oldTrigger.remove();

  const trigger = document.createElement("div");
  trigger.id = "scroll-trigger";
  trigger.style.cssText = "height: 20px; margin: 20px 0;";
  document.getElementById("results").appendChild(trigger);

  observer.observe(trigger);
}
function handleCardClick(result) {
  const episodeMatch = result.filename.match(/\[P(\d+)\]/);
  const timeMatch = result.timestamp.match(/^(\d+)m(\d+)s$/);
  if (episodeMatch && timeMatch) {
    const minutes = parseInt(timeMatch[1]);
    const seconds = parseInt(timeMatch[2]);
    const totalSeconds = minutes * 60 + seconds;
    const url = getBilibiliUrl(result.filename, totalSeconds);
    if (url) {
      // 优先原生 <a> 跳转(不受弹窗拦截),降级 window.open
      const a = document.createElement("a");
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  }
}

/* 根据文件名解析 bilibili 番剧 URL(优先 mapping,降级为按集号推算) */
function getBilibiliUrl(filename, totalSeconds) {
  for (const [path, fn] of Object.entries(mapping || {})) {
    if (fn === filename) {
      return `https://www.bilibili.com${path}?t=${totalSeconds}`;
    }
  }
  // 降级:已知 ep396256 起连续对应 P01~P25
  const m = filename && filename.match(/\[P(\d+)\]/);
  if (m) {
    const n = parseInt(m[1], 10);
    if (n >= 1 && n <= 25) {
      const ep = 396255 + n;
      return `https://www.bilibili.com/bangumi/play/ep${ep}/?t=${totalSeconds}`;
    }
  }
  return null;
}

/* 帧图放大预览模态:右上叉叉(圆形)、右下复制/下载(圆形,垂直分布)
   焦点管理: 打开时记下触发元素并把焦点移进模态、Tab 锁在模态内、关闭后焦点还给触发元素。 */
function openPreviewFrame(frameFile, infoText) {
  // 记住是谁打开的, 关闭时把键盘焦点还回去(否则焦点会留在被遮挡的页面上)
  const prevFocus = document.activeElement;
  let overlay = document.getElementById("previewOverlay");
  if (overlay) overlay.remove();

  overlay = document.createElement("div");
  overlay.id = "previewOverlay";
  overlay.className = "preview-overlay";

  const imgSrc = `frames/${frameFile}`;
  overlay.innerHTML = `
      <div class="preview-wrap" role="dialog" aria-modal="true" aria-label="\u5e27\u56fe\u9884\u89c8">
        <img class="preview-img" src="${imgSrc}" alt="${infoText || frameFile}">
        ${infoText ? `<p class="preview-info mono">${infoText}</p>` : ""}
        <button type="button" class="preview-close" aria-label="\u5173\u95ed">
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3 L13 13 M13 3 L3 13"/></svg>
        </button>
        <div class="preview-side">
          <button type="button" class="preview-copy" title="\u590d\u5236\u56fe\u7247" aria-label="\u590d\u5236\u56fe\u7247">
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>
          </button>
          <button type="button" class="preview-download" title="\u4e0b\u8f7d\u56fe\u7247" aria-label="\u4e0b\u8f7d\u56fe\u7247">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12 M7 11l5 5 5-5 M4 19h16"/></svg>
          </button>
        </div>
      </div>
  `;

  document.body.appendChild(overlay);

  const wrap = overlay.querySelector(".preview-wrap");
  const closeBtn = overlay.querySelector(".preview-close");
  const copyBtn = overlay.querySelector(".preview-copy");
  const dlBtn = overlay.querySelector(".preview-download");

  // 预览打开时预加载:图片 → Canvas → PNG blob 缓存(点击复制时零解码,手势内一步写入)
  let pngBlobCache = null;
  (async () => {
    try {
      const img = new Image();
      img.src = imgSrc;   // 同源帧图
      await img.decode();
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      canvas.getContext("2d").drawImage(img, 0, 0);
      pngBlobCache = await new Promise((res) => canvas.toBlob(res, "image/png"));
    } catch (e) {
      pngBlobCache = null;
    }
  })();

  // 三条关闭路径(叉叉 / 点遮罩 / Esc)统一走这里: 复位焦点、上锁、摘掉键盘监听
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    overlay.classList.add("closing");
    wrap.classList.add("closing");
    document.body.classList.remove("preview-open");
    document.removeEventListener("keydown", onKeydown, true);
    if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
    setTimeout(() => overlay.remove(), 210);
  };

  // Tab 锁在模态内 —— 否则键盘用户能 Tab 到遮罩背后那几十个链接/按钮上
  const focusables = () => [closeBtn, copyBtn, dlBtn];
  function onKeydown(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      return;
    }
    if (e.key !== "Tab") return;
    const items = focusables().filter((el) => el && el.offsetParent !== null);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    const inside = items.indexOf(active) >= 0;
    // 只拦"会跑出模态"的两端, 中间的移动一律交回浏览器默认行为。
    // 原写法 `else if (!inside || active === first)` 在 active===first 且**正向** Tab
    // 时也命中, preventDefault 之后又把焦点设回 first —— 结果是焦点被钉死在关闭钮上。
    // 实测: 正向 Tab 连按 6 次落点全是 preview-close, 反向 Shift+Tab 连按 6 次全是
    // preview-download, 可达元素只有这两个, **预览窗里的"复制图片"按钮任何键盘路径
    // 都到不了**。这是焦点锁写反了, 不是"正确的自循环"。
    if (items.length === 1) {
      e.preventDefault();
      first.focus();
    } else if (!inside) {
      e.preventDefault();
      (e.shiftKey ? last : first).focus();
    } else if (e.shiftKey && active === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  }

  closeBtn.addEventListener("click", close);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  // 捕获阶段: 无论焦点落在哪里都能收到 Esc(之前挂在 document 冒泡阶段, 焦点在模态里也收不到)
  document.addEventListener("keydown", onKeydown, true);
  document.body.classList.add("preview-open");
  closeBtn.focus();

  // 复制图片到剪贴板:先给反馈,再尽力写(绝无"点了没反应")
  copyBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const secureCtx = window.isSecureContext === true;
    if (secureCtx && navigator.clipboard && window.ClipboardItem && pngBlobCache) {
      navigator.clipboard
        .write([new ClipboardItem({ "image/png": pngBlobCache })])
        .then(() => showToast("\u5df2\u590d\u5236\u56fe\u7247\u5230\u526a\u8d34\u677f"))
        .catch(() => {
          legacyCopy(imgSrc);
          showToast("\u5df2\u590d\u5236\u56fe\u7247\u5730\u5740");
        });
    } else if (navigator.clipboard) {
      navigator.clipboard
        .writeText(imgSrc)
        .then(() => showToast("\u5df2\u590d\u5236\u56fe\u7247\u5730\u5740"))
        .catch(() => {
          legacyCopy(imgSrc);
          showToast("\u5df2\u590d\u5236\u56fe\u7247\u5730\u5740");
        });
    } else {
      legacyCopy(imgSrc);
      showToast("\u5df2\u590d\u5236\u56fe\u7247\u5730\u5740");
    }
  });

  // 旧版降级:execCommand textarea 复制文本
  function legacyCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }

  // 下载图片
  dlBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const a = document.createElement("a");
    a.href = imgSrc;
    a.download = frameFile;
    document.body.appendChild(a);
    a.click();
    a.remove();
  });
}

/* 轻量提示 */
function showToast(msg) {
  let t = document.getElementById("appToast");
  if (t) t.remove();
  t = document.createElement("div");
  t.id = "appToast";
  t.className = "copy-toast";
  t.setAttribute("role", "status");
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add("fade-out"), 1600);
  setTimeout(() => t.remove(), 2000);
}
