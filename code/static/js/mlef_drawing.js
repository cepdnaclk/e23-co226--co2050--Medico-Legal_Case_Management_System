document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("anatomicalCanvas");
    const ctx = canvas.getContext("2d");
    
    let isDrawing = false;
    let x = 0;
    let y = 0;

    // Set drawing style (Red pen to mimic medical markings)
    ctx.strokeStyle = "#e74c3c";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

    // Start drawing
    canvas.addEventListener("mousedown", (e) => {
        x = e.offsetX;
        y = e.offsetY;
        isDrawing = true;
    });

    // Draw lines
    canvas.addEventListener("mousemove", (e) => {
        if (isDrawing) {
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(e.offsetX, e.offsetY);
            ctx.stroke();
            x = e.offsetX;
            y = e.offsetY;
        }
    });

    // Stop drawing
    window.addEventListener("mouseup", () => {
        if (isDrawing) {
            isDrawing = false;
        }
    });

    // Clear Canvas Button
    document.getElementById("clearBtn").addEventListener("click", () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    });

    // Save Canvas Button (Ready for Supabase upload)
    document.getElementById("saveDrawingBtn").addEventListener("click", () => {
        // Extracts the drawing as a Base64 string
        const base64Image = canvas.toDataURL("image/png");
        console.log("Image Data Ready for Upload:", base64Image);
        alert("Drawing captured! Check console for Base64 data.");
    });

    // Save Form Button (placeholder behavior)
    document.getElementById("saveFormBtn").addEventListener("click", () => {
        const base64Image = canvas.toDataURL("image/png");
        console.log("Saving form and drawing:", base64Image);
        alert("Form saved locally. Implement server-side submission for permanent storage.");
    });

    // Reset Button clears all entered data and the canvas
    document.getElementById("resetBtn").addEventListener("click", () => {
        if (confirm("Reset all fields and drawing?")) {
            document.querySelectorAll('input[type="text"], input[type="date"], textarea').forEach((field) => {
                field.value = '';
            });
            document.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
                checkbox.checked = false;
            });
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    });

    // Discard Button returns to the dashboard if confirmed
    document.getElementById("discardBtn").addEventListener("click", () => {
        if (confirm("Discard the MLEF form and return to the dashboard?")) {
            window.location.href = "/dashboard";
        }
    });
});