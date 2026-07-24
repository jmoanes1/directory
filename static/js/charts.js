/**
 * Employee Directory - Dashboard Charts (HTML Canvas)
 */

(function () {
    'use strict';

    if (!window.chartData) return;

    const colors = {
        primary: '#6366f1',
        palette: ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#64748b'],
        grid: getComputedStyle(document.documentElement).getPropertyValue('--border-color').trim() || '#e2e8f0',
        text: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#94a3b8'
    };

    function drawBarChart(canvasId, labels, values) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = 280 * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = '280px';
        ctx.scale(dpr, dpr);

        const W = rect.width;
        const H = 280;

        if (!labels.length) {
            ctx.clearRect(0, 0, W, H);
            ctx.fillStyle = colors.text;
            ctx.font = '14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No department data available', W / 2, H / 2);
            return;
        }
        const padding = { top: 20, right: 20, bottom: 60, left: 50 };
        const chartW = W - padding.left - padding.right;
        const chartH = H - padding.top - padding.bottom;
        const maxVal = Math.max(...values, 1);
        const barWidth = chartW / values.length * 0.6;
        const gap = chartW / values.length * 0.4;

        ctx.clearRect(0, 0, W, H);

        // Grid lines
        ctx.strokeStyle = colors.grid;
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(W - padding.right, y);
            ctx.stroke();
        }

        // Bars with gradient
        values.forEach((val, i) => {
            const barH = (val / maxVal) * chartH;
            const x = padding.left + i * (barWidth + gap) + gap / 2;
            const y = padding.top + chartH - barH;

            const grad = ctx.createLinearGradient(x, y, x, y + barH);
            grad.addColorStop(0, colors.palette[i % colors.palette.length]);
            grad.addColorStop(1, colors.palette[(i + 1) % colors.palette.length] + '99');
            ctx.fillStyle = grad;
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(x, y, barWidth, barH, [6, 6, 0, 0]);
            } else {
                ctx.rect(x, y, barWidth, barH);
            }
            ctx.fill();

            ctx.fillStyle = colors.text;
            ctx.font = '600 11px Inter, sans-serif';
            ctx.textAlign = 'center';
            if (val > 0) ctx.fillText(val, x + barWidth / 2, y - 6);

            ctx.save();
            ctx.translate(x + barWidth / 2, H - padding.bottom + 12);
            ctx.rotate(-0.35);
            ctx.textAlign = 'right';
            ctx.font = '10px Inter, sans-serif';
            ctx.fillText(labels[i].substring(0, 14), 0, 0);
            ctx.restore();
        });
    }

    function drawLineChart(canvasId, labels, values) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = 260 * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = '260px';
        ctx.scale(dpr, dpr);

        const W = rect.width;
        const H = 260;
        const padding = { top: 20, right: 20, bottom: 50, left: 50 };
        const chartW = W - padding.left - padding.right;
        const chartH = H - padding.top - padding.bottom;

        if (!values.length) {
            ctx.fillStyle = colors.text;
            ctx.font = '14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No hiring data available', W / 2, H / 2);
            return;
        }

        const maxVal = Math.max(...values, 1);
        ctx.clearRect(0, 0, W, H);

        // Grid
        ctx.strokeStyle = colors.grid;
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(W - padding.right, y);
            ctx.stroke();
        }

        // Area fill under line
        const points = values.map((val, i) => ({
            x: padding.left + (i / Math.max(values.length - 1, 1)) * chartW,
            y: padding.top + chartH - (val / maxVal) * chartH,
        }));

        if (points.length > 1) {
            const areaGrad = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
            areaGrad.addColorStop(0, 'rgba(99, 102, 241, 0.25)');
            areaGrad.addColorStop(1, 'rgba(99, 102, 241, 0)');
            ctx.fillStyle = areaGrad;
            ctx.beginPath();
            ctx.moveTo(points[0].x, padding.top + chartH);
            points.forEach(p => ctx.lineTo(p.x, p.y));
            ctx.lineTo(points[points.length - 1].x, padding.top + chartH);
            ctx.closePath();
            ctx.fill();
        }

        // Line
        ctx.strokeStyle = colors.primary;
        ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round';
        ctx.beginPath();
        points.forEach((p, i) => {
            i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
        });
        ctx.stroke();

        // Points & labels
        points.forEach((p, i) => {
            ctx.fillStyle = '#fff';
            ctx.beginPath();
            ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = colors.primary;
            ctx.beginPath();
            ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = colors.text;
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(labels[i] || '', p.x, H - padding.bottom + 15);
        });
    }

    const STATUS_LABELS = {
        active: 'Active', inactive: 'Inactive',
        on_leave: 'On Leave', terminated: 'Terminated'
    };

    function buildStatusLegend(data) {
        const legendEl = document.getElementById('statusLegend');
        if (!legendEl) return;
        legendEl.innerHTML = data.map((item, i) => `
            <div class="dash-legend-item">
                <span class="dash-legend-left">
                    <span class="dash-legend-dot" style="background:${colors.palette[i % colors.palette.length]}"></span>
                    ${STATUS_LABELS[item.employment_status] || item.employment_status}
                </span>
                <span class="dash-legend-count">${item.count}</span>
            </div>
        `).join('');
    }

    function drawDoughnutChart(canvasId, data) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        if (!data.length) {
            const ctx = canvas.getContext('2d');
            const rect = canvas.parentElement.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = 220;
            ctx.fillStyle = colors.text;
            ctx.font = '14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No status data', rect.width / 2, 110);
            buildStatusLegend([]);
            return;
        }

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = 220 * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = '220px';
        ctx.scale(dpr, dpr);

        const W = rect.width;
        const H = 220;
        const cx = W / 2;
        const cy = H / 2 - 10;
        const radius = 72;
        const innerRadius = 50;
        const total = data.reduce((sum, d) => sum + d.count, 0) || 1;

        ctx.clearRect(0, 0, W, H);

        let startAngle = -Math.PI / 2;
        data.forEach((item, i) => {
            const sliceAngle = (item.count / total) * Math.PI * 2;
            ctx.fillStyle = colors.palette[i % colors.palette.length];
            ctx.beginPath();
            ctx.arc(cx, cy, radius, startAngle, startAngle + sliceAngle);
            ctx.arc(cx, cy, innerRadius, startAngle + sliceAngle, startAngle, true);
            ctx.closePath();
            ctx.fill();
            startAngle += sliceAngle;
        });

        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#0f172a';
        ctx.font = 'bold 22px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(total, cx, cy + 4);
        ctx.font = '11px Inter, sans-serif';
        ctx.fillStyle = colors.text;
        ctx.fillText('Total', cx, cy + 20);

        buildStatusLegend(data);
    }

    document.addEventListener('DOMContentLoaded', () => {
        const dept = window.chartData.dept || [];
        drawBarChart(
            'deptChart',
            dept.map(d => d.name),
            dept.map(d => d.emp_count)
        );

        const hire = window.chartData.hire || [];
        drawLineChart(
            'hireChart',
            hire.map(h => h.month),
            hire.map(h => h.count)
        );

        drawDoughnutChart('statusChart', window.chartData.status || []);

        window.addEventListener('resize', () => {
            drawBarChart('deptChart', dept.map(d => d.name), dept.map(d => d.emp_count));
            drawLineChart('hireChart', hire.map(h => h.month), hire.map(h => h.count));
            drawDoughnutChart('statusChart', window.chartData.status || []);
        });
    });
})();
