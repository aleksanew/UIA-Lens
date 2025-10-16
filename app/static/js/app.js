// Handles browser logic and connects to Flask API via fetch().

(function(){
    const stack = document.querySelector('.image-stack');
    if (!stack) return;

    let zoom = 1;
    const MIN = 0.2, MAX = 5.0, STEP = 0.10;

    const slider = document.querySelector('.zoom input[type="range"]');
    const outBtn = document.querySelector('.zoom [data-zoom="out"]');
    const inBtn = document.querySelector('.zoom [data-zoom="in"]');
    const valueEl = document.querySelector('.zoom .zoom-value');

    function applyZoom(newZoom, pivot){
        zoom = Math.min(MAX, Math.max(MIN, newZoom));
        if (pivot) {
            stack.style.transformOrigin = `${pivot.x}px ${pivot.y}px`;
        } else {
            stack.style.transformOrigin = 'center center';
        }
        stack.style.transform = `scale(${zoom})`;

        if (slider) slider.value = Math.round(zoom * 100);
        if (valueEl) valueEl.textContent = `${Math.round(zoom * 100)}%`;
    }

    stack.addEventListener('wheel', (e) => {
        e.preventDefault();
        const rect = stack.getBoundingClientRect();
        const pivot = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        const factor = e.deltaY < 0 ? (1 + STEP) : (1 - STEP);
        applyZoom(zoom * factor, pivot);
    }, { passive: false });

    if (slider){
        slider.min = 20;
        slider.max = 500;
        slider.step = 1;
        slider.addEventListener('input', () => {
            applyZoom(parseInt(slider.value, 10) / 100);
        });
    }

    if (inBtn) inBtn.addEventListener('click', () => applyZoom(zoom * (1 + STEP)));
    if (outBtn) outBtn.addEventListener('click', () => applyZoom(zoom * (1 - STEP)));

    window.EditorZoom = {
        get: () => zoom,
        set: (z) => applyZoom(z),
        in: () => applyZoom(zoom * (1 + STEP)),
        out: () => applyZoom(zoom * (1 - STEP))
    };

    applyZoom(1);
})();