document.addEventListener("DOMContentLoaded", function(event) { 
    
    // background color of amount left field
    var allFields = document.querySelectorAll(".field-get_amount_left");
    var allFieldsArr = [...allFields];

    allFieldsArr.forEach(field => {
        var innerValue = parseFloat(field.innerHTML)
        percent = (innerValue /186) * 100
        field.style.backgroundColor = `rgb(${percent *2}, ${(100 - percent) *2}, 0)`

    })
});

