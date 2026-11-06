(() => {
    const TEXT_TARGET_TAGS = new Set(['DIV', 'SPAN', 'P', 'LI', 'INPUT', 'TEXTAREA']);
    const TEXT_SELECTOR = 'div, span, p, li, input, textarea';
    const LAYOUT_TARGET_SELECTOR = [
        'form',
        'button',
        'input',
        'textarea',
        'select',
        'label',
        'nav',
        'header',
        'footer',
        'section',
        'article',
        'aside',
        'main',
        'ul',
        'ol',
        '[class*="d-flex"]',
        '[class*="flex-"]',
        '[class*="justify-"]',
        '[class*="align-"]',
        '[class*="grid"]',
        '[class*="row"]',
        '[class*="col-"]',
        '[class*="-start"]',
        '[class*="-end"]',
    ].join(', ');
    const RTL_CHAR_REGEX = /[\u0600-\u06FF]/;
    const DIR_DATA_FLAG = 'autoDirManaged';
    const ALIGN_DATA_FLAG = 'autoTextAlignManaged';
    const LAYOUT_DATA_FLAG = 'autoLayoutManaged';
    const EXCLUDED_LAYOUT_TAGS = new Set(['SCRIPT', 'STYLE', 'LINK', 'META', 'TITLE']);

    const pendingElements = new Set();
    const layoutBaselineMap = new WeakMap();
    const classFlipMap = new WeakMap();
    const changedPropertiesMap = new WeakMap();
    let scheduled = false;
    let lastRootDir = null;

    function normaliseDirection(value) {
        return value && value.toLowerCase() === 'rtl' ? 'rtl' : 'ltr';
    }

    function rootDirection() {
        const html = document.documentElement;
        const body = document.body;
        const dir =
            html.getAttribute('dir') ||
            html.dir ||
            (body && (body.getAttribute('dir') || body.dir));
        return normaliseDirection(dir) || 'ltr';
    }

    function syncRootClass() {
        const dir = rootDirection();
        if (dir === lastRootDir) {
            return;
        }
        lastRootDir = dir;
        const root = document.documentElement;
        if (!root) {
            return;
        }
        root.classList.remove('ltr-layout', 'rtl-layout');
        root.classList.add(dir === 'rtl' ? 'rtl-layout' : 'ltr-layout');
    }

    function isTargetTextElement(node) {
        return node && node.nodeType === Node.ELEMENT_NODE && TEXT_TARGET_TAGS.has(node.tagName);
    }

    function getElementText(element) {
        if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
            const value = element.value && element.value.trim();
            if (value) {
                return value;
            }
            return (element.placeholder || '').trim();
        }
        return (element.textContent || '').trim();
    }

    function hasManualDirection(element) {
        return element.hasAttribute('dir') && element.dataset[DIR_DATA_FLAG] !== 'true';
    }

    function hasManualAlign(element) {
        return Boolean(element.style?.textAlign && element.dataset[ALIGN_DATA_FLAG] !== 'true');
    }

    function applyDirection(element, text) {
        const direction = RTL_CHAR_REGEX.test(text) ? 'rtl' : 'ltr';
        const align = direction === 'rtl' ? 'right' : 'left';

        if (element.getAttribute('dir') !== direction) {
            element.setAttribute('dir', direction);
        }
        if (!hasManualAlign(element) && element.style.textAlign !== align) {
            element.style.textAlign = align;
            element.dataset[ALIGN_DATA_FLAG] = 'true';
        }

        element.dataset[DIR_DATA_FLAG] = 'true';
        return direction;
    }

    function getElementDirection(element) {
        if (!element || element === document) {
            return rootDirection();
        }

        const own = element.getAttribute && (element.getAttribute('dir') || element.dir);
        if (own) {
            return normaliseDirection(own);
        }

        if (typeof element.closest === 'function') {
            const ancestor = element.closest('[dir]');
            if (ancestor) {
                const dir = ancestor.getAttribute('dir') || ancestor.dir;
                if (dir) {
                    return normaliseDirection(dir);
                }
            }
        }

        return element.parentElement ? getElementDirection(element.parentElement) : rootDirection();
    }

    function shouldManageLayout(element, computed) {
        if (!element || element.nodeType !== Node.ELEMENT_NODE) {
            return false;
        }
        if (EXCLUDED_LAYOUT_TAGS.has(element.tagName)) {
            return false;
        }
        if (!computed) {
            computed = getComputedStyle(element);
        }
        if (!computed || computed.display === 'none') {
            return false;
        }

        const display = computed.display;
        const isFlex =
            display === 'flex' ||
            display === 'inline-flex';
        const flexDirection = computed.flexDirection;
        const isFlexRow = isFlex && (flexDirection === 'row' || flexDirection === 'row-reverse');
        const isGrid =
            display === 'grid' ||
            display === 'inline-grid';
        const hasDirectionalSpacing =
            computed.marginLeft !== computed.marginRight ||
            computed.paddingLeft !== computed.paddingRight ||
            computed.borderTopLeftRadius !== computed.borderTopRightRadius ||
            computed.borderBottomLeftRadius !== computed.borderBottomRightRadius;
        const cssFloat = computed.cssFloat || computed.float || 'none';
        const hasDirectionalFloat = cssFloat !== 'none' && cssFloat !== 'inline-start' && cssFloat !== 'inline-end';
        const isControl = element.matches?.('button, input, textarea, select, form, label');
        const classList = element.classList;
        const hasDirectionalClass =
            !!classList &&
            (classList.contains('text-start') ||
                classList.contains('text-end') ||
                classList.contains('float-start') ||
                classList.contains('float-end') ||
                Array.from(classList).some((cls) => /^m[trblxy]?s-/.test(cls) || /^p[trblxy]?s-/.test(cls)));

        return (
            isFlexRow ||
            isGrid ||
            hasDirectionalSpacing ||
            hasDirectionalFloat ||
            isControl ||
            hasDirectionalClass ||
            layoutBaselineMap.has(element)
        );
    }

    function captureLayoutBaseline(element, computed, direction) {
        const style = element.style || {};
        const baseline = {
            inline: {
                marginLeft: style.marginLeft || '',
                marginRight: style.marginRight || '',
                paddingLeft: style.paddingLeft || '',
                paddingRight: style.paddingRight || '',
                borderTopLeftRadius: style.borderTopLeftRadius || '',
                borderTopRightRadius: style.borderTopRightRadius || '',
                borderBottomLeftRadius: style.borderBottomLeftRadius || '',
                borderBottomRightRadius: style.borderBottomRightRadius || '',
                flexDirection: style.flexDirection || '',
                justifyContent: style.justifyContent || '',
                alignContent: style.alignContent || '',
                gridAutoFlow: style.gridAutoFlow || '',
                justifyItems: style.justifyItems || '',
                justifySelf: style.justifySelf || '',
                float: style.cssFloat || style.float || '',
            },
            computed: {
                marginLeft: computed.marginLeft,
                marginRight: computed.marginRight,
                paddingLeft: computed.paddingLeft,
                paddingRight: computed.paddingRight,
                borderTopLeftRadius: computed.borderTopLeftRadius,
                borderTopRightRadius: computed.borderTopRightRadius,
                borderBottomLeftRadius: computed.borderBottomLeftRadius,
                borderBottomRightRadius: computed.borderBottomRightRadius,
                flexDirection: computed.flexDirection,
                justifyContent: computed.justifyContent,
                alignContent: computed.alignContent,
                display: computed.display,
                gridAutoFlow: computed.gridAutoFlow,
                justifyItems: computed.justifyItems,
                justifySelf: computed.justifySelf,
                float: computed.cssFloat || computed.float || 'none',
            },
            baseDirection: direction || rootDirection(),
        };

        layoutBaselineMap.set(element, baseline);
        element.dataset[LAYOUT_DATA_FLAG] = 'true';
        return baseline;
    }

    function setInlineStyle(element, property, value) {
        if (!element || !element.style) {
            return;
        }
        const normalized = value == null ? '' : String(value);
        if (element.style[property] !== normalized) {
            element.style[property] = normalized;
            recordChange(element, property);
        }
    }

    function setFloat(element, value) {
        if (!element || !element.style) {
            return;
        }
        const prop = 'cssFloat' in element.style ? 'cssFloat' : 'float';
        const newValue = value == null ? '' : String(value);
        if (element.style[prop] !== newValue) {
            element.style[prop] = newValue;
            recordChange(element, prop);
        }
    }

    function recordChange(element, property) {
        let set = changedPropertiesMap.get(element);
        if (!set) {
            set = new Set();
            changedPropertiesMap.set(element, set);
        }
        set.add(property);
    }

    function restoreProperty(element, property, value) {
        const changed = changedPropertiesMap.get(element);
        if (!changed || !changed.has(property) || !element || !element.style) {
            return;
        }
        element.style[property] = value != null ? String(value) : '';
        changed.delete(property);
        if (!changed.size) {
            changedPropertiesMap.delete(element);
        }
    }

    function restoreFloat(element, baseline) {
        const prop = 'cssFloat' in element.style ? 'cssFloat' : 'float';
        restoreProperty(element, prop, baseline.inline.float || '');
    }

    function flipInlineAlignment(value) {
        if (!value) {
            return value;
        }
        const normalized = value.trim();
        switch (normalized) {
            case 'left':
                return 'right';
            case 'right':
                return 'left';
            case 'flex-start':
                return 'flex-end';
            case 'flex-end':
                return 'flex-start';
            case 'start':
                return 'end';
            case 'end':
                return 'start';
            case 'self-start':
                return 'self-end';
            case 'self-end':
                return 'self-start';
            default:
                return normalized;
        }
    }

    function mirrorSpacing(element, baseline) {
        const { computed } = baseline;
        if (computed.marginLeft !== computed.marginRight) {
            setInlineStyle(element, 'marginLeft', computed.marginRight);
            setInlineStyle(element, 'marginRight', computed.marginLeft);
        }
        if (computed.paddingLeft !== computed.paddingRight) {
            setInlineStyle(element, 'paddingLeft', computed.paddingRight);
            setInlineStyle(element, 'paddingRight', computed.paddingLeft);
        }
        if (computed.borderTopLeftRadius !== computed.borderTopRightRadius) {
            setInlineStyle(element, 'borderTopLeftRadius', computed.borderTopRightRadius);
            setInlineStyle(element, 'borderTopRightRadius', computed.borderTopLeftRadius);
        }
        if (computed.borderBottomLeftRadius !== computed.borderBottomRightRadius) {
            setInlineStyle(element, 'borderBottomLeftRadius', computed.borderBottomRightRadius);
            setInlineStyle(element, 'borderBottomRightRadius', computed.borderBottomLeftRadius);
        }

        const cssFloat = computed.float;
        if (cssFloat === 'left') {
            setFloat(element, 'right');
        } else if (cssFloat === 'right') {
            setFloat(element, 'left');
        } else if (cssFloat === 'inline-start') {
            setFloat(element, 'inline-end');
        } else if (cssFloat === 'inline-end') {
            setFloat(element, 'inline-start');
        }
    }

    function restoreSpacing(element, baseline) {
        const { inline, computed } = baseline;
        restoreProperty(element, 'marginLeft', inline.marginLeft || computed.marginLeft);
        restoreProperty(element, 'marginRight', inline.marginRight || computed.marginRight);
        restoreProperty(element, 'paddingLeft', inline.paddingLeft || computed.paddingLeft);
        restoreProperty(element, 'paddingRight', inline.paddingRight || computed.paddingRight);
        restoreProperty(
            element,
            'borderTopLeftRadius',
            inline.borderTopLeftRadius || computed.borderTopLeftRadius
        );
        restoreProperty(
            element,
            'borderTopRightRadius',
            inline.borderTopRightRadius || computed.borderTopRightRadius
        );
        restoreProperty(
            element,
            'borderBottomLeftRadius',
            inline.borderBottomLeftRadius || computed.borderBottomLeftRadius
        );
        restoreProperty(
            element,
            'borderBottomRightRadius',
            inline.borderBottomRightRadius || computed.borderBottomRightRadius
        );
        restoreFloat(element, baseline);
    }

    function mirrorFlow(element, baseline) {
        const { computed } = baseline;
        const display = computed.display;

        if (display === 'flex' || display === 'inline-flex') {
            const flexDirection = computed.flexDirection;
            if (flexDirection === 'row') {
                setInlineStyle(element, 'flexDirection', 'row-reverse');
            } else if (flexDirection === 'row-reverse') {
                setInlineStyle(element, 'flexDirection', 'row');
            }

            const flippedJustify = flipInlineAlignment(computed.justifyContent);
            if (flippedJustify && flippedJustify !== computed.justifyContent) {
                setInlineStyle(element, 'justifyContent', flippedJustify);
            }
            const flippedAlignContent = flipInlineAlignment(computed.alignContent);
            if (flippedAlignContent && flippedAlignContent !== computed.alignContent) {
                setInlineStyle(element, 'alignContent', flippedAlignContent);
            }
        } else if (display === 'grid' || display === 'inline-grid') {
            const flippedJustifyItems = flipInlineAlignment(computed.justifyItems);
            if (flippedJustifyItems && flippedJustifyItems !== computed.justifyItems) {
                setInlineStyle(element, 'justifyItems', flippedJustifyItems);
            }
            const flippedJustifyContent = flipInlineAlignment(computed.justifyContent);
            if (flippedJustifyContent && flippedJustifyContent !== computed.justifyContent) {
                setInlineStyle(element, 'justifyContent', flippedJustifyContent);
            }
            const flippedJustifySelf = flipInlineAlignment(computed.justifySelf);
            if (flippedJustifySelf && flippedJustifySelf !== computed.justifySelf) {
                setInlineStyle(element, 'justifySelf', flippedJustifySelf);
            }
        }
    }

    function restoreFlow(element, baseline) {
        const { inline, computed } = baseline;
        restoreProperty(
            element,
            'flexDirection',
            inline.flexDirection || computed.flexDirection
        );
        restoreProperty(
            element,
            'justifyContent',
            inline.justifyContent || computed.justifyContent
        );
        restoreProperty(
            element,
            'alignContent',
            inline.alignContent || computed.alignContent
        );
        restoreProperty(
            element,
            'justifyItems',
            inline.justifyItems || computed.justifyItems
        );
        restoreProperty(
            element,
            'justifySelf',
            inline.justifySelf || computed.justifySelf
        );
        restoreProperty(
            element,
            'gridAutoFlow',
            inline.gridAutoFlow || computed.gridAutoFlow
        );
    }

    function applyClassSwap(classList, from, to) {
        if (typeof classList.replace === 'function') {
            classList.replace(from, to);
        } else {
            classList.remove(from);
            classList.add(to);
        }
    }

    function getClassSwap(cls, direction) {
        if (direction === 'rtl') {
            if (cls.endsWith('-start')) {
                return cls.replace(/-start$/, '-end');
            }
            if (cls.startsWith('ms-')) {
                return cls.replace(/^ms-/, 'me-');
            }
            if (cls.startsWith('ps-')) {
                return cls.replace(/^ps-/, 'pe-');
            }
        } else {
            if (cls.endsWith('-end')) {
                return cls.replace(/-end$/, '-start');
            }
            if (cls.startsWith('me-')) {
                return cls.replace(/^me-/, 'ms-');
            }
            if (cls.startsWith('pe-')) {
                return cls.replace(/^pe-/, 'ps-');
            }
        }
        return null;
    }

    function flipDirectionalClasses(element, direction) {
        if (!element || !element.classList || element.classList.length === 0) {
            return;
        }

        let record = classFlipMap.get(element);
        if (!record) {
            record = { swapped: [], active: false };
            classFlipMap.set(element, record);
        }

        const targetDirection = normaliseDirection(direction);

        if (targetDirection === 'rtl') {
            if (record.active) {
                return;
            }
            const replacements = [];
            Array.from(element.classList).forEach((cls) => {
                const swap = getClassSwap(cls, 'rtl');
                if (swap && !element.classList.contains(swap)) {
                    applyClassSwap(element.classList, cls, swap);
                    replacements.push({ from: cls, to: swap });
                }
            });
            if (replacements.length) {
                record.swapped = replacements;
                record.active = true;
            }
        } else {
            if (!record.active || !record.swapped.length) {
                return;
            }
            record.swapped.forEach(({ from, to }) => {
                if (element.classList.contains(to)) {
                    applyClassSwap(element.classList, to, from);
                }
            });
            record.swapped = [];
            record.active = false;
        }
    }

    function applyLayout(element, direction) {
        if (!element || element.nodeType !== Node.ELEMENT_NODE) {
            return;
        }

        const computed = getComputedStyle(element);
        if (!layoutBaselineMap.has(element) && !shouldManageLayout(element, computed)) {
            return;
        }

        const targetDirection = normaliseDirection(direction || getElementDirection(element));
        const baseline =
            layoutBaselineMap.get(element) ||
            captureLayoutBaseline(element, computed, targetDirection);

        if (!baseline.baseDirection) {
            baseline.baseDirection = targetDirection;
        }

        if (targetDirection === baseline.baseDirection) {
            restoreSpacing(element, baseline);
            restoreFlow(element, baseline);
        } else {
            mirrorSpacing(element, baseline);
            mirrorFlow(element, baseline);
        }

        flipDirectionalClasses(element, targetDirection);
    }

    function processTextElement(element) {
        if (!isTargetTextElement(element)) {
            return;
        }

        const text = getElementText(element);
        let direction = null;

        if (text && !hasManualDirection(element)) {
            direction = applyDirection(element, text);
        } else if (element.hasAttribute('dir')) {
            direction = normaliseDirection(element.getAttribute('dir'));
        }

        if (!direction) {
            direction = getElementDirection(element);
        }

        applyLayout(element, direction);
    }

    function processLayoutCandidates(root) {
        if (!root || root.nodeType !== Node.ELEMENT_NODE) {
            return;
        }

        const candidates = new Set();

        if (shouldManageLayout(root)) {
            candidates.add(root);
        }

        root.querySelectorAll(LAYOUT_TARGET_SELECTOR).forEach((element) => {
            if (shouldManageLayout(element)) {
                candidates.add(element);
            }
        });

        candidates.forEach((element) => {
            applyLayout(element, getElementDirection(element));
        });
    }

    function processTree(root) {
        if (!root || root.nodeType !== Node.ELEMENT_NODE) {
            return;
        }

        if (isTargetTextElement(root)) {
            processTextElement(root);
        }

        root.querySelectorAll(TEXT_SELECTOR).forEach(processTextElement);
        processLayoutCandidates(root);
    }

    function flushPending() {
        const items = Array.from(pendingElements);
        pendingElements.clear();
        items.forEach(processTree);
        syncRootClass();
        scheduled = false;
    }

    function scheduleProcess(node) {
        if (!node) {
            return;
        }

        let element = node;
        if (node.nodeType === Node.TEXT_NODE) {
            element = node.parentElement;
        }

        if (element && element.nodeType === Node.ELEMENT_NODE) {
            pendingElements.add(element);
        }

        if (!scheduled) {
            scheduled = true;
            requestAnimationFrame(flushPending);
        }
    }

    function observeMutations() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(scheduleProcess);
                    if (mutation.target) {
                        scheduleProcess(mutation.target);
                    }
                } else if (mutation.type === 'characterData') {
                    scheduleProcess(mutation.target);
                } else if (mutation.type === 'attributes' && mutation.attributeName === 'dir') {
                    scheduleProcess(mutation.target);
                    if (
                        mutation.target === document.documentElement ||
                        mutation.target === document.body
                    ) {
                        scheduleProcess(document.body);
                    }
                }
            });
        });

        const config = {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ['dir'],
        };

        if (document.body) {
            observer.observe(document.body, config);
        }
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['dir'],
        });

        return observer;
    }

    function init() {
        if (!document.body) {
            return;
        }

        processTree(document.body);
        syncRootClass();
        observeMutations();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }

    window.applyAutoTextDirection = () => {
        scheduleProcess(document.body);
    };

    window.syncDirectionalLayout = (direction) => {
        if (direction) {
            const normalised = normaliseDirection(direction);
            if (document.documentElement.getAttribute('dir') !== normalised) {
                document.documentElement.setAttribute('dir', normalised);
            }
            if (document.body && document.body.getAttribute('dir') !== normalised) {
                document.body.setAttribute('dir', normalised);
            }
        }
        scheduleProcess(document.body);
    };
})();
