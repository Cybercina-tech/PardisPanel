(() => {
  const root = document.getElementById("editor-root");
  if (!root) {
    return;
  }

  const canvas = document.getElementById("canvas");
  const elementsContainer = document.getElementById("elements");
  const addTextBtn = document.getElementById("addTextBtn");
  const addImageBtn = document.getElementById("addImageBtn");
  const saveBtn = document.getElementById("saveBtn");
  const imageInput = document.getElementById("imageUpload");
  const settingsPanel = document.getElementById("settingsPanel");
  const noSelection = document.getElementById("noSelection");
  const contentField = document.getElementById("elementContent");
  const fontSizeField = document.getElementById("elementFontSize");
  const colorField = document.getElementById("elementColor");
  const typeField = document.getElementById("elementType");
  const canvasOverlay = document.getElementById("canvasOverlay");

  const apiUrl = root.dataset.apiUrl;
  const backgroundUrl = root.dataset.backgroundUrl;

  if (!apiUrl) {
    console.error("Template editor requires an API endpoint.");
    return;
  }

  const state = {
    canvasSize: { width: 800, height: 450 },
    elements: [],
    selectedId: null,
    dragging: null,
    resizing: null,
    dirty: false,
  };

  const CSRF_COOKIE_NAME = "csrftoken";

  const utils = {
    clamp(value, min, max) {
      return Math.min(Math.max(value, min), max);
    },
    pxToPercent(value, total) {
      return (value / total) * 100;
    },
    percentToPx(percent, total) {
      return (percent / 100) * total;
    },
    getCsrfToken() {
      if (document.cookie) {
        const tokens = document.cookie.split(";").map((c) => c.trim());
        for (const token of tokens) {
          if (token.startsWith(`${CSRF_COOKIE_NAME}=`)) {
            return decodeURIComponent(token.split("=")[1]);
          }
        }
      }
      return "";
    },
    generateTempId() {
      if (window.crypto && typeof window.crypto.randomUUID === "function") {
        return `temp-${window.crypto.randomUUID()}`;
      }
      return `temp-${Math.random().toString(36).slice(2, 8)}-${Date.now()}`;
    },
  };

  function setCanvasBackground(url) {
    if (!url) {
      applyCanvasDimensions();
      canvas.classList.add("is-ready");
      return;
    }
    const img = new Image();
    img.onload = () => {
      state.canvasSize.width = img.naturalWidth;
      state.canvasSize.height = img.naturalHeight;
      applyCanvasDimensions();
      canvas.classList.add("is-ready");
    };
    img.onerror = () => {
      applyCanvasDimensions();
      canvas.classList.add("is-ready");
    };
    img.src = url;
    canvas.style.backgroundImage = `url(${url})`;
  }

  function applyCanvasDimensions() {
    canvas.style.setProperty("--canvas-width", `${state.canvasSize.width}px`);
    canvas.style.setProperty("--canvas-height", `${state.canvasSize.height}px`);
  }

  function selectElement(id) {
    if (state.selectedId === id) {
      return;
    }
    state.selectedId = id;
    updateSelectionUI();
  }

  function updateSelectionUI() {
    elementsContainer.querySelectorAll(".element").forEach((el) => {
      el.classList.toggle("is-selected", el.dataset.id === state.selectedId);
    });

    const selectedData = state.elements.find(
      (el) => el.localId === state.selectedId
    );

    if (!selectedData) {
      settingsPanel.classList.remove("is-visible");
      noSelection.classList.add("is-visible");
      fontSizeField.disabled = true;
      colorField.disabled = true;
      fontSizeField.closest(".panel-field")?.classList.add("is-disabled");
      colorField.closest(".panel-field")?.classList.add("is-disabled");
      return;
    }

    settingsPanel.classList.add("is-visible");
    noSelection.classList.remove("is-visible");

    contentField.value = selectedData.content || "";
    fontSizeField.value = selectedData.font_size || 16;
    colorField.value = selectedData.color || "#000000";
    typeField.value = selectedData.type;

    if (selectedData.type === "image") {
      contentField.setAttribute("placeholder", "Image data (base64 or URL)");
    } else {
      contentField.setAttribute("placeholder", "Element text content");
    }

    const isText = selectedData.type === "text";
    fontSizeField.disabled = !isText;
    colorField.disabled = !isText;
    fontSizeField.closest(".panel-field")?.classList.toggle("is-disabled", !isText);
    colorField.closest(".panel-field")?.classList.toggle("is-disabled", !isText);
  }

  function createHandle(direction) {
    const handle = document.createElement("span");
    handle.className = `resize-handle resize-${direction}`;
    handle.dataset.direction = direction;
    return handle;
  }

  function renderElement(data) {
    let element = elementsContainer.querySelector(
      `.element[data-id="${data.localId}"]`
    );

    if (!element) {
      element = document.createElement("div");
      element.className = "element fade-in";
      element.dataset.id = data.localId;
      element.dataset.type = data.type;

      const contentWrapper = document.createElement("div");
      contentWrapper.className = "element-body";
      element.appendChild(contentWrapper);

      const handles = ["top-left", "top-right", "bottom-left", "bottom-right"];
      handles.forEach((direction) => element.appendChild(createHandle(direction)));

      elementsContainer.appendChild(element);
    }

    const contentWrapper = element.querySelector(".element-body");
    element.dataset.type = data.type;

    if (data.type === "text") {
      element.classList.remove("element-image");
      element.classList.add("element-text");
      contentWrapper.textContent = data.content || "New Text";
      contentWrapper.style.fontSize = `${data.font_size || 16}px`;
      contentWrapper.style.color = data.color || "#ffffff";
      contentWrapper.style.transform = "scale(1)";
      element.dataset.scale = "1";
    } else {
      element.classList.remove("element-text");
      element.classList.add("element-image");
      const imageContent = data.content;
      const imageScale = data.scale || 1;
      element.dataset.scale = imageScale;
      contentWrapper.style.transform = `scale(${imageScale})`;
      if (imageContent && imageContent.startsWith("data:")) {
        contentWrapper.style.backgroundImage = `url(${imageContent})`;
      } else if (imageContent) {
        contentWrapper.style.backgroundImage = `url(${imageContent})`;
      } else {
        contentWrapper.style.backgroundImage = "none";
      }
    }

    const canvasWidth = state.canvasSize.width;
    const canvasHeight = state.canvasSize.height;

    const left = utils.percentToPx(data.x ?? 0, canvasWidth);
    const top = utils.percentToPx(data.y ?? 0, canvasHeight);

    element.style.transform = `translate(${left}px, ${top}px)`;

    element.classList.toggle("is-selected", data.localId === state.selectedId);
  }

  function renderAllElements() {
    elementsContainer.innerHTML = "";
    state.elements.forEach((element) => renderElement(element));
    updateSelectionUI();
  }

  function markDirty() {
    state.dirty = true;
    saveBtn.classList.add("is-dirty");
  }

  function handlePointerDown(event) {
    const target = event.target.closest(".element");
    const handle = event.target.closest(".resize-handle");

    if (!target || handle) {
      return;
    }

    event.preventDefault();
    selectElement(target.dataset.id);

    const pointerId = event.pointerId;
    const { left, top } = target.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();

    state.dragging = {
      pointerId,
      elementId: target.dataset.id,
      offsetX: event.clientX - left,
      offsetY: event.clientY - top,
      canvasRect,
    };

    canvasOverlay.classList.add("is-active");
    target.setPointerCapture(pointerId);
  }

  function handlePointerMove(event) {
    if (!state.dragging) {
      return;
    }

    const { pointerId, elementId, offsetX, offsetY, canvasRect } =
      state.dragging;
    if (event.pointerId !== pointerId) {
      return;
    }

    const elementData = state.elements.find(
      (el) => el.localId === elementId
    );
    if (!elementData) {
      return;
    }

    const canvasWidth = state.canvasSize.width;
    const canvasHeight = state.canvasSize.height;

    const newLeftPx = utils.clamp(
      event.clientX - canvasRect.left - offsetX,
      0,
      canvasWidth
    );
    const newTopPx = utils.clamp(
      event.clientY - canvasRect.top - offsetY,
      0,
      canvasHeight
    );

    elementData.x = utils.clamp(
      utils.pxToPercent(newLeftPx, canvasWidth),
      0,
      100
    );
    elementData.y = utils.clamp(
      utils.pxToPercent(newTopPx, canvasHeight),
      0,
      100
    );

    renderElement(elementData);
    markDirty();
  }

  function handlePointerUp(event) {
    const pointerId = event.pointerId;
    if (state.dragging?.pointerId === pointerId) {
      const target = elementsContainer.querySelector(
        `.element[data-id="${state.dragging.elementId}"]`
      );
      if (target) {
        target.releasePointerCapture(pointerId);
      }
      state.dragging = null;
      canvasOverlay.classList.remove("is-active");
    }

    if (state.resizing?.pointerId === pointerId) {
      const target = elementsContainer.querySelector(
        `.element[data-id="${state.resizing.elementId}"]`
      );
      if (target) {
        target.releasePointerCapture(pointerId);
      }
      state.resizing = null;
      canvasOverlay.classList.remove("is-active");
    }
  }

  function handleResizePointerDown(event) {
    const handle = event.target.closest(".resize-handle");
    if (!handle) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    const element = handle.closest(".element");
    if (!element) {
      return;
    }

    selectElement(element.dataset.id);

    const pointerId = event.pointerId;
    const elementRect = element.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();

    state.resizing = {
      pointerId,
      elementId: element.dataset.id,
      startWidth: elementRect.width,
      startHeight: elementRect.height,
      startX: event.clientX,
      startY: event.clientY,
      direction: handle.dataset.direction,
      canvasRect,
    };

    element.setPointerCapture(pointerId);
    canvasOverlay.classList.add("is-active");
  }

  function handleResizePointerMove(event) {
    if (!state.resizing || event.pointerId !== state.resizing.pointerId) {
      return;
    }

    const { elementId, startWidth, startHeight, startX, startY, direction } =
      state.resizing;

    const elementData = state.elements.find(
      (el) => el.localId === elementId
    );
    if (!elementData) {
      return;
    }

    const deltaX = event.clientX - startX;
    const deltaY = event.clientY - startY;

    let scaleFactor = 1;
    if (direction.includes("right")) {
      scaleFactor = (startWidth + deltaX) / startWidth;
    } else if (direction.includes("left")) {
      scaleFactor = (startWidth - deltaX) / startWidth;
    } else if (direction.includes("bottom")) {
      scaleFactor = (startHeight + deltaY) / startHeight;
    } else if (direction.includes("top")) {
      scaleFactor = (startHeight - deltaY) / startHeight;
    }

    scaleFactor = utils.clamp(scaleFactor, 0.5, 3);

    const elementEl = elementsContainer.querySelector(
      `.element[data-id="${elementId}"]`
    );
    if (!elementEl) {
      return;
    }

    const contentEl = elementEl.querySelector(".element-body");

    if (elementData.type === "text") {
      const newFontSize = utils.clamp(
        Math.round((elementData.font_size || 16) * scaleFactor),
        8,
        200
      );
      elementData.font_size = newFontSize;
      contentEl.style.fontSize = `${newFontSize}px`;
      fontSizeField.value = newFontSize;
    } else {
      const currentScale = parseFloat(
        elementEl.dataset.scale || "1"
      );
      const newScale = utils.clamp(currentScale * scaleFactor, 0.3, 3);
      elementEl.dataset.scale = newScale.toFixed(2);
      contentEl.style.transform = `scale(${newScale})`;
      elementData.scale = newScale;
    }

    markDirty();
  }

  function addElement(type, content) {
    const newElement = {
      id: null,
      localId: utils.generateTempId(),
      type,
      content: content || (type === "text" ? "New Text" : ""),
      x: 40,
      y: 30,
      font_size: 18,
      color: "#ffffff",
      scale: 1,
    };

    state.elements.push(newElement);
    renderElement(newElement);
    selectElement(newElement.localId);
    markDirty();
  }

  async function loadTemplate() {
    try {
      const response = await fetch(apiUrl, {
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error(`Failed to load template: ${response.statusText}`);
      }
      const data = await response.json();

      state.elements = (data.elements || []).map((element) => ({
        ...element,
        localId: element.id?.toString() ?? utils.generateTempId(),
        scale: element.scale ?? 1,
      }));

      setCanvasBackground(data.background);
      renderAllElements();
    } catch (error) {
      console.error(error);
    }
  }

  async function saveTemplate() {
    const payload = {
      elements: state.elements.map((element) => ({
        id: element.id,
        type: element.type,
        content: element.content,
        x: element.x,
        y: element.y,
        font_size: element.font_size,
        color: element.color,
      })),
    };

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
      const response = await fetch(apiUrl, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": utils.getCsrfToken(),
        },
        body: JSON.stringify(payload),
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error(`Failed to save template: ${response.statusText}`);
      }

      const data = await response.json();
      state.elements = (data.elements || []).map((element) => ({
        ...element,
        localId: element.id?.toString() ?? utils.generateTempId(),
        scale: element.scale ?? 1,
      }));
      renderAllElements();
      state.dirty = false;
      saveBtn.classList.remove("is-dirty");
    } catch (error) {
      console.error(error);
      alert("Unable to save template. Please try again.");
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Template";
    }
  }

  function onCanvasClick(event) {
    if (event.target === canvas || event.target === elementsContainer) {
      state.selectedId = null;
      updateSelectionUI();
    }
  }

  function initializeEventListeners() {
    elementsContainer.addEventListener("pointerdown", handlePointerDown);
    elementsContainer.addEventListener("pointerdown", handleResizePointerDown);
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointermove", handleResizePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    elementsContainer.addEventListener("click", (event) => {
      const element = event.target.closest(".element");
      if (element) {
        selectElement(element.dataset.id);
      }
    });

    addTextBtn.addEventListener("click", () => addElement("text"));

    addImageBtn.addEventListener("click", () => {
      imageInput.click();
    });

    imageInput.addEventListener("change", (event) => {
      const file = event.target.files?.[0];
      if (!file) {
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        addElement("image", reader.result);
        imageInput.value = "";
      };
      reader.readAsDataURL(file);
    });

    saveBtn.addEventListener("click", () => {
      saveTemplate();
    });

    canvas.addEventListener("click", onCanvasClick);
    elementsContainer.addEventListener("click", onCanvasClick);

    contentField.addEventListener("input", (event) => {
      const selected = state.elements.find(
        (el) => el.localId === state.selectedId
      );
      if (!selected) {
        return;
      }
      selected.content = event.target.value;
      renderElement(selected);
      markDirty();
    });

    fontSizeField.addEventListener("input", (event) => {
      const selected = state.elements.find(
        (el) => el.localId === state.selectedId
      );
      if (!selected) {
        return;
      }
      selected.font_size = parseInt(event.target.value, 10) || 16;
      renderElement(selected);
      markDirty();
    });

    colorField.addEventListener("input", (event) => {
      const selected = state.elements.find(
        (el) => el.localId === state.selectedId
      );
      if (!selected) {
        return;
      }
      selected.color = event.target.value;
      renderElement(selected);
      markDirty();
    });

    typeField.addEventListener("change", (event) => {
      const selected = state.elements.find(
        (el) => el.localId === state.selectedId
      );
      if (!selected) {
        return;
      }

      selected.type = event.target.value;

      if (selected.type === "text") {
        selected.content = selected.content || "New Text";
        selected.font_size = selected.font_size || 18;
        selected.color = selected.color || "#ffffff";
      } else {
        selected.content = selected.content || "";
      }

      renderElement(selected);
      updateSelectionUI();
      markDirty();
    });
  }

  function init() {
    applyCanvasDimensions();
    setCanvasBackground(backgroundUrl);
    initializeEventListeners();
    loadTemplate();
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && state.dirty) {
      saveBtn.classList.add("pulse");
    } else {
      saveBtn.classList.remove("pulse");
    }
  });

  init();
})();

