// dashboard.js

document.addEventListener("DOMContentLoaded", () => {
    setTodayDate();
    initFadeIn();
    initTransactionsToggle();
    drawCashflowChart();
});

function setTodayDate() {
    const el = document.getElementById("today-date");
    if (!el) return;

    const now = new Date();
    const formatted = now.toLocaleDateString(undefined, {
        weekday: "short",
        day: "2-digit",
        month: "short",
        year: "numeric"
    });

    el.textContent = formatted;
}

function initFadeIn() {
    const sections = Array.from(document.querySelectorAll(".js-fade"));
    sections.forEach((section, index) => {
        setTimeout(() => {
            section.classList.add("is-visible");
        }, 140 + index * 160);
    });
}

function initTransactionsToggle() {
    const shell = document.getElementById("transactions-shell");
    const toggle = document.getElementById("toggle-transactions");
    if (!shell || !toggle) return;

    const rows = Array.from(shell.querySelectorAll("tbody tr"));
    const maxVisible = 5;

    // initial collapsed state: show first 5
    rows.forEach((row, index) => {
        if (index >= maxVisible) {
            row.classList.add("is-hidden");
        }
    });

    // lock initial height for smooth first animation
    const initialHeight = shell.getBoundingClientRect().height;
    shell.style.height = initialHeight + "px";
    requestAnimationFrame(() => {
        shell.style.height = "";
    });

    toggle.addEventListener("click", () => {
        const isCollapsed = toggle.dataset.state !== "expanded";
        animateTableHeight(shell, rows, maxVisible, isCollapsed);
        toggle.dataset.state = isCollapsed ? "expanded" : "collapsed";
        toggle.textContent = isCollapsed ? "Show less" : "Show all";
    });
}

function animateTableHeight(shell, rows, maxVisible, expanding) {
    const startHeight = shell.getBoundingClientRect().height;

    if (expanding) {
        rows.forEach(row => row.classList.remove("is-hidden"));
    } else {
        rows.forEach((row, index) => {
            if (index >= maxVisible) row.classList.add("is-hidden");
        });
    }

    const endHeight = shell.getBoundingClientRect().height;

    shell.style.height = startHeight + "px";
    // force reflow
    void shell.offsetHeight;

    shell.style.transition = "height 260ms ease";
    shell.style.height = endHeight + "px";

    shell.addEventListener(
        "transitionend",
        () => {
            shell.style.height = "";
            shell.style.transition = "";
        },
        { once: true }
    );
}

function drawCashflowChart() {
    const canvas = document.getElementById("cashflow-chart");
    if (!canvas || !canvas.getContext) return;

    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const logicalWidth = canvas.width;
    const logicalHeight = canvas.height;

    canvas.width = logicalWidth * dpr;
    canvas.height = logicalHeight * dpr;
    ctx.scale(dpr, dpr);

    const centerX = logicalWidth / 2;
    const centerY = logicalHeight / 2;
    const radius = Math.min(centerX, centerY) - 8;

    const income = 1800;
    const expenses = 1320;
    const net = 480;

    const segments = [
        { label: "Income", value: income, color: "rgba(34,197,94,0.9)" },
        { label: "Expenses", value: expenses, color: "rgba(248,113,113,0.95)" },
        { label: "Net", value: net, color: "rgba(59,130,246,0.9)" }
    ];

    const total = segments.reduce((sum, s) => sum + s.value, 0);
    if (total <= 0) return;

    let startAngle = -Math.PI / 2;

    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    segments.forEach(segment => {
        const sliceAngle = (segment.value / total) * Math.PI * 2;
        const endAngle = startAngle + sliceAngle;

        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        ctx.closePath();
        ctx.fillStyle = segment.color;
        ctx.fill();

        startAngle = endAngle;
    });

    // Cut inner circle to create donut
    const innerRadius = radius * 0.58;
    ctx.save();
    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Fill inner area with panel background for softer look
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
}
