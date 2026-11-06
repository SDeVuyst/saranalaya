document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".field-get_amount_left").forEach(function (field) {
        var node = field.querySelector("[data-target]");
        var remaining = parseFloat(node ? node.textContent : field.textContent);
        var target = node ? parseFloat(node.getAttribute("data-target")) : remaining;
        var color = "#dc2626";
        var text = "#fff";
        if (remaining <= 0) {
            color = "#16a34a";
        } else if (target > 0 && remaining < target) {
            color = "#facc15";
            text = "#422006";
        }
        field.style.backgroundColor = color;
        field.style.color = text;
        field.style.fontWeight = "700";
    });
});
