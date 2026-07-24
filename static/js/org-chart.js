/**
 * Organization chart — clean SVG tree visualization
 */
(function () {
    'use strict';
    if (!window.orgTreeData) return;

    const svg = document.getElementById('orgChartSvg');
    if (!svg) return;

    const NODE_W = 176;
    const NODE_H = 72;
    const GAP_X = 24;
    const GAP_Y = 72;
    const PAD = 32;

    function cssVar(name, fallback) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function theme() {
        return {
            surface: cssVar('--bg-surface', '#ffffff'),
            border: cssVar('--border-color', '#e5e7eb'),
            primary: cssVar('--color-primary', '#1e3a8a'),
            primaryLight: cssVar('--color-primary-light', 'rgba(30, 58, 138, 0.08)'),
            text: cssVar('--text-primary', '#1f2937'),
            textMuted: cssVar('--text-muted', '#9ca3af'),
            textSecondary: cssVar('--text-secondary', '#6b7280'),
            line: cssVar('--border-color', '#d1d5db'),
        };
    }

    function truncate(text, max) {
        const value = String(text || '');
        return value.length > max ? `${value.slice(0, max - 1)}…` : value;
    }

    /** Assign _x / _y grid positions for balanced tree layout. */
    function layoutTree(nodes) {
        const slots = [];

        function measure(node) {
            const children = node.children || [];
            if (!children.length) {
                node._subtreeWidth = 1;
                return 1;
            }
            let width = 0;
            children.forEach((child) => { width += measure(child); });
            node._subtreeWidth = width;
            return width;
        }

        function position(node, depth, leftSlot) {
            const children = node.children || [];
            if (!children.length) {
                node._x = leftSlot;
                node._y = depth;
                slots.push(node);
                return leftSlot + 1;
            }

            let slot = leftSlot;
            children.forEach((child) => {
                slot = position(child, depth + 1, slot);
            });

            const first = children[0];
            const last = children[children.length - 1];
            node._x = (first._x + last._x) / 2;
            node._y = depth;
            slots.push(node);
            return slot;
        }

        nodes.forEach((root) => measure(root));
        let offset = 0;
        nodes.forEach((root) => {
            position(root, 0, offset);
            offset += root._subtreeWidth;
        });

        return slots;
    }

    function renderTree(data) {
        const colors = theme();
        svg.innerHTML = '';

        if (!data || !data.length) {
            svg.setAttribute('viewBox', '0 0 400 120');
            svg.setAttribute('height', '120');
            svg.innerHTML = `<text x="200" y="60" text-anchor="middle" fill="${colors.textMuted}" font-size="14" font-family="var(--font-family)">No hierarchy data available</text>`;
            return;
        }

        const nodes = layoutTree(data);

        nodes.forEach((node) => {
            if (!node.children || !node.children.length) return;
            node.children.forEach((child) => {
                const x1 = node._x * (NODE_W + GAP_X) + NODE_W / 2 + PAD;
                const y1 = node._y * (NODE_H + GAP_Y) + NODE_H + PAD;
                const x2 = child._x * (NODE_W + GAP_X) + NODE_W / 2 + PAD;
                const y2 = child._y * (NODE_H + GAP_Y) + PAD;

                const midY = y1 + (GAP_Y - NODE_H) / 2;
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute(
                    'd',
                    `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`
                );
                path.setAttribute('fill', 'none');
                path.setAttribute('stroke', colors.line);
                path.setAttribute('stroke-width', '1.5');
                path.setAttribute('stroke-linecap', 'round');
                path.setAttribute('stroke-linejoin', 'round');
                svg.appendChild(path);
            });
        });

        nodes.forEach((node) => {
            const x = node._x * (NODE_W + GAP_X) + PAD;
            const y = node._y * (NODE_H + GAP_Y) + PAD;
            const isManager = (node.children || []).length > 0;

            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('class', 'org-node');
            g.setAttribute('transform', `translate(${x},${y})`);
            g.style.cursor = 'pointer';
            g.addEventListener('click', () => {
                window.location.href = `/employees/${node.id}/`;
            });

            const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            bg.setAttribute('class', 'org-node-bg');
            bg.setAttribute('width', NODE_W);
            bg.setAttribute('height', NODE_H);
            bg.setAttribute('rx', '10');
            bg.setAttribute('fill', colors.surface);
            bg.setAttribute('stroke', isManager ? colors.primary : colors.border);
            bg.setAttribute('stroke-width', isManager ? '1.5' : '1');
            g.appendChild(bg);

            if (isManager) {
                const accent = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                accent.setAttribute('width', NODE_W);
                accent.setAttribute('height', '3');
                accent.setAttribute('rx', '10');
                accent.setAttribute('fill', colors.primary);
                g.appendChild(accent);
            }

            const initialsBg = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            initialsBg.setAttribute('cx', '22');
            initialsBg.setAttribute('cy', NODE_H / 2 + (isManager ? 1 : 0));
            initialsBg.setAttribute('r', '14');
            initialsBg.setAttribute('fill', isManager ? colors.primaryLight : colors.border);
            initialsBg.setAttribute('opacity', isManager ? '1' : '0.35');
            g.appendChild(initialsBg);

            const initials = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            initials.setAttribute('x', '22');
            initials.setAttribute('y', NODE_H / 2 + (isManager ? 5 : 4));
            initials.setAttribute('text-anchor', 'middle');
            initials.setAttribute('fill', isManager ? colors.primary : colors.textSecondary);
            initials.setAttribute('font-size', '10');
            initials.setAttribute('font-weight', '600');
            initials.textContent = truncate(node.initials || node.name.slice(0, 2), 2);
            g.appendChild(initials);

            const name = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            name.setAttribute('x', '44');
            name.setAttribute('y', '28');
            name.setAttribute('fill', colors.text);
            name.setAttribute('font-size', '12');
            name.setAttribute('font-weight', '600');
            name.textContent = truncate(node.name, 18);
            g.appendChild(name);

            const posText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            posText.setAttribute('x', '44');
            posText.setAttribute('y', '44');
            posText.setAttribute('fill', colors.textSecondary);
            posText.setAttribute('font-size', '10');
            posText.textContent = truncate(node.position, 22);
            g.appendChild(posText);

            const dept = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            dept.setAttribute('x', '44');
            dept.setAttribute('y', '58');
            dept.setAttribute('fill', colors.textMuted);
            dept.setAttribute('font-size', '9');
            dept.textContent = truncate(node.department, 24);
            g.appendChild(dept);

            svg.appendChild(g);
        });

        const maxX = Math.max(...nodes.map((n) => n._x)) * (NODE_W + GAP_X) + NODE_W + PAD * 2;
        const maxY = Math.max(...nodes.map((n) => n._y)) * (NODE_H + GAP_Y) + NODE_H + PAD * 2;
        svg.setAttribute('viewBox', `0 0 ${maxX} ${maxY}`);
        svg.setAttribute('height', String(Math.min(maxY, 640)));
    }

    renderTree(window.orgTreeData);

    document.getElementById('rootFilter')?.addEventListener('change', function () {
        const root = this.value;
        const url = root ? `/employees/org-chart/data/?root=${root}` : '/employees/org-chart/data/';
        fetch(url)
            .then((r) => r.json())
            .then((d) => renderTree(d.tree))
            .catch(() => {
                window.Toast?.show('Could not load org chart data.', 'error');
            });
    });
})();
