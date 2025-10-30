// For some reason, default option isn't selected by default
document.getElementById("filterSelected").selectedIndex = 0;

const filterButton = document.getElementById("filterButton");
// Observe changes on element
const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
        if (mutation.attributeName === "class") {
            if (filterButton.classList.contains("active")) {
                document.querySelector(".filter-option-container").style.display = "block";
            } else {
                document.querySelector(".filter-option-container").style.display = "none";
            }
        }
    });
});
// Start observing the button for class changes
observer.observe(filterButton, { attributes: true });


const slider = document.getElementById("inpK");
const label = document.getElementById("sliderValue");
slider.addEventListener("input", () => {
  label.textContent = "K: " + slider.value;
});

function reloadActiveImage(){
    // Temporary implementation
    location.reload();
}

// Change which form to be displayed depending on the filter selected
function changeOptions(){
    let val = document.getElementById("filterSelected").value
    document.querySelectorAll(".filter-option").forEach(i => {
        i.style.display = "none";
    });
    let opt = document.getElementById(val)
    opt.style.display = "block"
}


async function hueShift(event){
    event.preventDefault();
    let hue = document.getElementById("inpHue").value

    const data = { value: hue };
    await fetch("/api/v1/filters/hue_shift", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    reloadActiveImage()
}

async function grayscale(event){
    event.preventDefault();
    await fetch("/api/v1/filters/grayscale", {
        method: "POST"
    });
    reloadActiveImage()
}

async function featureDetection(event){
    event.preventDefault();
    let bs = document.getElementById("inpBlockSize").value
    let ks = document.getElementById("inpKSize").value
    let k = document.getElementById("inpK").value
    const data = { block_size: parseInt(bs), ksize: parseInt(ks), k: parseFloat(k) };
    await fetch("/api/v1/filters/feature_detection", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    reloadActiveImage()
}


async function edgeDetection(event){
    event.preventDefault();
    let alg = document.getElementById("edgeAlg").value

    const data = { algorithm: alg };
    await fetch("/api/v1/filters/edge_detection", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    reloadActiveImage()
}

// Disable thresh input for algorithms that don't use it
function disableThresh(){
    let sel = document.getElementById("threshAlg").value
    let thresh = document.getElementById("inpThresh")

    if(sel === "otsu" || sel === "triangle"){
        thresh.disabled = true;
        thresh.style.backgroundColor = "gray"
    } else{
        thresh.disabled = false
        thresh.style.backgroundColor = "#334155"
    }
}

async function thresholding(event) {
    event.preventDefault();
    let alg = document.getElementById("threshAlg").value
    let t = document.getElementById("inpThresh").value

    const data = {type: alg, threshold: t};
    await fetch("/api/v1/filters/threshold", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    reloadActiveImage()
}

async function gaussBlur(event) {
    event.preventDefault();
    let k1 = document.getElementById("inpKSize1").value
    let k2 = document.getElementById("inpKSize2").value
    let sx = document.getElementById("inpSigmaX").value
    let sy = document.getElementById("inpSigmaY").value

    const data = {ksize1: k1, ksize2: k2, sigmaX: sx, sigmaY: sy };
    await fetch("/api/v1/filters/gauss_blur", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    reloadActiveImage()
}

async function medianBlur(event) {
    event.preventDefault();
    let k = document.getElementById("inpMedianKSize").value

    const data = {ksize: k};
    await fetch("/api/v1/filters/median_blur", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    reloadActiveImage()
}

async function bilateralBlur(event) {
    event.preventDefault();
    let d = document.getElementById("inpD").value
    let sc = document.getElementById("inpSigmaColor").value
    let ss = document.getElementById("inpSigmaSpace").value

    const data = {d: d, sigmaColor: sc, sigmaSpace: ss};
    await fetch("/api/v1/filters/bilateral_blur", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    reloadActiveImage()
}

createMatrix();
function createMatrix(){
    let n = document.getElementById("nMatrix").value;
    let m = document.getElementById("mMatrix").value;

    const matrix = document.getElementById("matrix");
    matrix.innerHTML = "";
    matrix.style.gridTemplateColumns = "repeat(" + n + ", auto)";

    for (let i = 0; i < n * m; i++) {
        const input = document.createElement("input");
        input.type = "number";
        input.required = true;
        input.value = "1";
        matrix.appendChild(input);
    }
}

async function customKernel(event) {
    event.preventDefault();
    let matrixConst = document.getElementById("matrixConst").value;
    let n = document.getElementById("nMatrix").value;
    let m = document.getElementById("mMatrix").value;
    let matrix = document.getElementById("matrix");
    let elements = Array.from(matrix.children);
    console.log(parseFloat(matrixConst))
    let array = [];

    for (let i = 0; i < m; i++) {
        let row = [];
        for (let j = 0; j < n; j++) {

            let index = i*n + j;
            let val = elements[index].value;
            row.push(parseInt(val));
        }
        array.push(row);
    }

    // const data = {constant: 2, array: array };
    // await fetch("/api/v1/filters/kernel_filter", {
    //     method: "POST",
    //     headers: {
    //         "Content-Type": "application/json"
    //     },
    //     body: JSON.stringify(data)
    // });
    // reloadActiveImage()
}


