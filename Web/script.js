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
  randomStringDisplayed: false,
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
const CONFIG = {
  randomStrings: [
    "搜索罗布奥特曼的经典台词",
    "寻找爱染诚的身影",
    "搜索你想要的内容",
  ],
};
class UIController {
  static updateSearchFormPosition(isSearching) {
    const searchForm = document.getElementById("searchForm");
    const randomStringDisplay = document.getElementById("randomStringDisplay");
    if (isSearching) {
      searchForm.classList.add("searching");
      if (!AppState.randomStringDisplayed) this.showRandomString();
    } else {
      searchForm.classList.remove("searching");
      this.clearRandomString();
    }
  }
  static showRandomString() {
    if (!AppState.randomStringDisplayed) {
      const randomStringDisplay = document.getElementById(
        "randomStringDisplay",
      );
      const randomIndex = Math.floor(
        Math.random() * CONFIG.randomStrings.length,
      );
      randomStringDisplay.textContent = CONFIG.randomStrings[randomIndex];
      AppState.randomStringDisplayed = true;
      randomStringDisplay.classList.remove("fade-out");
      randomStringDisplay.classList.add("fade-in");
    }
  }
  static clearRandomString() {
    const randomStringDisplay = document.getElementById("randomStringDisplay");
    randomStringDisplay.classList.remove("fade-in");
    randomStringDisplay.classList.add("fade-out");
    setTimeout(() => {
      randomStringDisplay.textContent = "";
      AppState.randomStringDisplayed = false;
    }, 300);
  }
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
  const minRatio = parseInt(document.getElementById("minRatio").value) || 50;
  const minSimilarity =
    parseFloat(document.getElementById("minSimilarity").value) || 0;
  const searchForm = document.getElementById("searchForm");
  searchForm.classList.add("searching");
  startNaturalLoadingBar();

  try {
    const results = await SearchController.performSearch(
      query,
      minRatio,
      minSimilarity,
    );

    if (results && results.status === "success") {
      // 爱染诚画面优先 / 仅显示含爱染诚画面（高级选项）
      const aisomeFirst = document.getElementById("aisomeFirst")?.checked !== false;
      const aisomeOnly = document.getElementById("aisomeOnly")?.checked === true;
      let data = results.data.slice();
      if (aisomeOnly) data = data.filter((r) => r.aisome);
      if (aisomeFirst) {
        data.sort((a, b) => {
          if ((b.aisome || 0) !== (a.aisome || 0)) return (b.aisome || 0) - (a.aisome || 0);
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
    } else {
      throw new Error("Invalid search results format");
    }
  } catch (error) {
    console.error("Search error:", error);
    document.getElementById("errorDisplay").textContent =
      `搜索失败: ${error.message}`;
    document.getElementById("errorDisplay").style.display = "block";
    completeLoadingBar();
  } finally {
    enableKeywordTags();
    searchForm.classList.remove("searching");
  }
}
// 归档统计随语料实时计算 —— 原先写死在 index.html 里(显示"归档 4929 条"), 而语料经多轮
// 审核已增至 7206 条, 页面数字长期偏小。这类数字不应有第二个来源。
async function refreshArchiveStats() {
  const el = document.querySelector(".hero-stats");
  if (!el || !window.subtitleDB) return;
  try {
    if (!window.subtitleDB.isLoaded) await window.subtitleDB.load();
    const db = window.subtitleDB.db || [];
    if (!db.length) return;
    const eps = new Set(db.map((r) => String(r.f || "").slice(0, 4)));
    // 裸库记录用 d 表示"该帧命中爱染诚人脸集"; 检索结果里才被映射成 aisome(db_search.js)
    const aisome = db.filter((r) => r.d).length;
    el.textContent = `全 ${eps.size} 集 · 归档 ${db.length} 条 · 爱染诚登场 ${aisome} 条`;
  } catch (error) {
    /* 统计失败不影响检索, 保留 HTML 里的兜底文案 */
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
      if (e.key === "Enter") {
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
  const keywordsContainer = document.getElementById("keywordsContainer");

  document.getElementById("errorDisplay").style.display = "none";

  if (!append) {
    resultsDiv.innerHTML = "";
    AppState.displayedCount = 0;
    keywordsContainer.innerHTML = "";
    keywordsContainer.classList.remove("show");
  }

  if (!append && data.data.length > 0 && data.data[0].type === "keywords") {
    const keywords = data.data[0].keywords;
    if (keywords && keywords.length > 0) {
      keywordsContainer.innerHTML = `
        <div class="keywords-tags">
          ${keywords.map(keyword => `<span class="keyword-tag">${keyword}</span>`).join("")}
        </div>
      `;
      keywordsContainer.classList.add("show");
      
      keywordsContainer.querySelectorAll('.keyword-tag').forEach(tag => {
        tag.addEventListener('click', () => {
          if (AppState.isSearching) return;
          
          const keyword = tag.textContent;
          document.getElementById('query').value = keyword;
          
          keywordsContainer.querySelectorAll('.keyword-tag').forEach(t => {
            t.classList.add('disabled');
          });
          
          document.getElementById('searchForm').dispatchEvent(new Event('submit'));
        });
      });
    }
    
    data.data = data.data.slice(1);
  }

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
                    <h3>${message}</h3>
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
      card.className = "result-card" + (result.aisome ? " is-aisome" : "");

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
            <span class="card-crystal" aria-hidden="true"></span>
            ${result.aisome ? `<span class="seal" aria-hidden="true">\u8bda</span>` : ""}
            <div class="result-content">
                <div class="result-text-block">
                    <h3>${episodeMatch ? `<span class="tag">${episodeMatch[1]}</span>${cleanFilename.replace(/P\d+/, "").trim()}` : cleanFilename}</h3>
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

/* 帧图放大预览模态:右上叉叉(圆形)、右下复制/下载(圆形,垂直分布) */
function openPreviewFrame(frameFile, infoText) {
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

  const close = () => {
    if (overlay.classList.contains("closing")) return;
    overlay.classList.add("closing");
    wrap.classList.add("closing");
    setTimeout(() => overlay.remove(), 210);
  };

  closeBtn.addEventListener("click", close);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener("keydown", function esc(e) {
    if (e.key === "Escape") {
      close();
      document.removeEventListener("keydown", esc);
    }
  });

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
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add("fade-out"), 1600);
  setTimeout(() => t.remove(), 2000);
}
function enableKeywordTags() {
  const keywordsContainer = document.getElementById("keywordsContainer");
  keywordsContainer.querySelectorAll('.keyword-tag').forEach(tag => {
    tag.classList.remove('disabled');
  });
}