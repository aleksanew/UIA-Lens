

async function showFilterOptions(self){

    await fetch("/api/v1/filters/laplace_edge", {
        method: "POST"
    });
}

async function featureDetection(){
    const data = { block_size: 10, ksize: 3, k:0.02 };
    await fetch("/api/v1/filters/feature_detection", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
}

async function grayscale(){
    await fetch("/api/v1/filters/grayscale", {
        method: "POST"
    });
}

async function hueShift(){
    const data = { value: 30 };
    await fetch("/api/v1/filters/hue_shift", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
}