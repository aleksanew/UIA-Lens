async function toggleVisibility(btn, i) {
    const content = btn.textContent.trim();
    let layer = document.getElementById("layer" + i)
    if (content === "👁️"){
        btn.textContent = "🚫"
        layer.style.visibility = "hidden"
    } else if (content === "🚫"){
        btn.textContent = "👁️"
        layer.style.visibility = "visible"
    }

    const data = { index: i };
    await fetch("/api/v1/layers/update_visibility", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
}

async function setActive(div, i) {
    const activeItems = document.querySelectorAll('.layers-list .active');
    activeItems.forEach(item => item.classList.remove('active'));
    div.classList.add("active")

    const data = { index: i };
    await fetch("/api/v1/layers/update_active", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
}


async function addLayer(){
    await fetch("/api/v1/layers/add_layer", {
        method: "POST"
    });
    // Bad implementation, but is fast enough and I can't be bothered
    // to manually update html with js now
    location.reload();
}
async function deleteLayer(){
    await fetch("/api/v1/layers/delete_layer", {
        method: "POST"
    });
    // Bad implementation, but is fast enough and I can't be bothered
    // to manually update html with js now
    location.reload();
}
async function duplicateLayer(){
    await fetch("/api/v1/layers/duplicate_layer", {
        method: "POST"
    });
    // Bad implementation, but is fast enough and I can't be bothered
    // to manually update html with js now
    location.reload();
}
async function renameLayer(){
    // Get the first element with the class "my-class"
    const div = document.querySelector(".active");
    let btn = div.children[0]
    // Make not ugly
    const oldName = btn.textContent;
    let newName = prompt("New name");
    if (newName === null){
        btn.textContent = oldName;
        return
    }
    btn.textContent = newName;

    const data = { name: newName };
    await fetch("/api/v1/layers/rename_layer", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
}






