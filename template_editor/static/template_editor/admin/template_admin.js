(function () {
    "use strict";

    const debounce = (fn, delay = 300) => {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    };

    function parseJson(textarea) {
        try {
            return JSON.parse(textarea.value || "{}");
        } catch (err) {
            textarea.classList.add("template-config-json--error");
            return null;
        }
    }

    function writeJson(textarea, data) {
        textarea.classList.remove("template-config-json--error");
        textarea.value = JSON.stringify(data, null, 2);
        const event = new Event("change", { bubbles: true });
        textarea.dispatchEvent(event);
    }

    function ensureFields(data) {
        if (!data || typeof data !== "object") {
            data = {};
        }
        if (!data.fields || typeof data.fields !== "object") {
            data.fields = {};
        }
        return data;
    }

    function buildTable(helper) {
        const textarea = document.getElementById(helper.dataset.configSource);
        if (!textarea) {
            return;
        }
        const tbody = helper.querySelector("tbody");
        const render = () => {
            const data = parseJson(textarea);
            if (!data) {
                tbody.innerHTML = "<tr><td colspan='8'>Invalid JSON</td></tr>";
                return;
            }
            const config = ensureFields(data);
            const entries = Object.entries(config.fields);
            if (!entries.length) {
                tbody.innerHTML = "<tr><td colspan='8'>No fields</td></tr>";
                return;
            }

            tbody.innerHTML = entries
                .map(
                    ([name, field]) =>
                        `<tr data-field="${name}">
                            <td><code>${name}</code></td>
                            <td>${field.x ?? "—"}</td>
                            <td>${field.y ?? "—"}</td>
                            <td>${field.size ?? "—"}</td>
                            <td><span class="color-chip" style="--chip:${field.color || "#000"}"></span>${field.color || "—"}</td>
                            <td>${field.align || "left"}</td>
                            <td>${field.max_width ?? "—"}</td>
                            <td class="actions">
                                <button type="button" class="button button-small js-edit-field">Edit</button>
                                <button type="button" class="button button-small js-remove-field">Remove</button>
                            </td>
                        </tr>`
                )
                .join("");
        };

        render();
        textarea.addEventListener("input", debounce(render, 200));

        helper.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof HTMLElement)) {
                return;
            }
            const row = target.closest("tr[data-field]");
            const data = ensureFields(parseJson(textarea) || {});
            if (!row) {
                if (target.classList.contains("js-add-field")) {
                    const name = window.prompt("Field name");
                    if (!name) {
                        return;
                    }
                    if (data.fields[name]) {
                        window.alert("A field with this name already exists.");
                        return;
                    }
                    data.fields[name] = { x: 0, y: 0, size: 32, color: "#000000", align: "left" };
                    writeJson(textarea, data);
                    render();
                } else if (target.classList.contains("js-sort-fields")) {
                    const sorted = Object.keys(data.fields)
                        .sort()
                        .reduce((acc, key) => {
                            acc[key] = data.fields[key];
                            return acc;
                        }, {});
                    data.fields = sorted;
                    writeJson(textarea, data);
                    render();
                } else if (target.classList.contains("js-format-json")) {
                    const parsed = parseJson(textarea);
                    if (parsed) {
                        writeJson(textarea, parsed);
                        render();
                    }
                }
                return;
            }

            const fieldName = row.dataset.field;
            if (!fieldName) {
                return;
            }

            if (target.classList.contains("js-remove-field")) {
                if (window.confirm(`Remove field "${fieldName}"?`)) {
                    delete data.fields[fieldName];
                    writeJson(textarea, data);
                    render();
                }
            } else if (target.classList.contains("js-edit-field")) {
                const field = data.fields[fieldName] || {};
                const x = window.prompt("X coordinate", field.x ?? 0);
                if (x === null) return;
                const y = window.prompt("Y coordinate", field.y ?? 0);
                if (y === null) return;
                const size = window.prompt("Font size", field.size ?? 32);
                if (size === null) return;
                const color = window.prompt("Color (hex)", field.color || "#000000");
                if (color === null) return;
                const align = window.prompt("Alignment (left/center/right)", field.align || "left");
                if (align === null) return;
                const maxWidth = window.prompt("Max width (optional)", field.max_width ?? "");
                const payload = {
                    x: Number(x) || 0,
                    y: Number(y) || 0,
                    size: Number(size) || 32,
                    color,
                    align: align || "left",
                };
                if (maxWidth) {
                    payload.max_width = Number(maxWidth) || undefined;
                } else {
                    delete payload.max_width;
                }
                data.fields[fieldName] = payload;
                writeJson(textarea, data);
                render();
            }
        });
    }

    function setupImageWidgets() {
        document.querySelectorAll(".template-image-widget input[type=file]").forEach((input) => {
            input.addEventListener("change", () => {
                const widget = input.closest(".template-image-widget");
                if (!widget) return;
                let preview = widget.querySelector(".template-image-thumb");
                if (!preview) return;
                if (preview.dataset && preview.dataset.objectUrl) {
                    URL.revokeObjectURL(preview.dataset.objectUrl);
                }
                const file = input.files && input.files[0];
                if (!file) {
                    preview.textContent = "No image";
                    preview.classList.add("template-image-thumb--empty");
                    if (preview.tagName.toLowerCase() === "img") {
                        preview.removeAttribute("src");
                    }
                    return;
                }
                const blobUrl = URL.createObjectURL(file);
                if (preview.tagName.toLowerCase() !== "img") {
                    const img = document.createElement("img");
                    img.className = "template-image-thumb";
                    preview.replaceWith(img);
                    preview = img;
                }
                preview.classList.remove("template-image-thumb--empty");
                preview.dataset.objectUrl = blobUrl;
                preview.src = blobUrl;
            });
        });
    }

    function getCsrfToken() {
        const value = document.cookie
            .split(";")
            .map((c) => c.trim())
            .find((c) => c.startsWith("csrftoken="));
        return value ? decodeURIComponent(value.split("=")[1]) : "";
    }

    function setupPreviewWidgets() {
        document.querySelectorAll(".js-template-preview").forEach((wrapper) => {
            const button = wrapper.querySelector(".js-refresh-preview");
            const img = wrapper.querySelector("img");
            const textarea = document.querySelector(".template-config-json");
            if (!button || !img || !textarea) {
                return;
            }
            const refresh = () => {
                const url = wrapper.dataset.previewUrl;
                if (!url) return;
                const formData = new FormData();
                formData.append("config", textarea.value);
                button.disabled = true;
                button.textContent = "Refreshing…";
                fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: formData,
                })
                    .then((response) => {
                        if (!response.ok) {
                            throw new Error("Failed to generate preview");
                        }
                        return response.blob();
                    })
                    .then((blob) => {
                        if (img.dataset.objectUrl) {
                            URL.revokeObjectURL(img.dataset.objectUrl);
                        }
                        const blobUrl = URL.createObjectURL(blob);
                        img.dataset.objectUrl = blobUrl;
                        img.src = blobUrl;
                    })
                    .catch((error) => {
                        console.error(error);
                        window.alert(error.message);
                    })
                    .finally(() => {
                        button.disabled = false;
                        button.textContent = "Refresh preview";
                    });
            };
            button.addEventListener("click", refresh);
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".template-config-helper").forEach((helper) => buildTable(helper));
        setupImageWidgets();
        setupPreviewWidgets();
    });
})();

