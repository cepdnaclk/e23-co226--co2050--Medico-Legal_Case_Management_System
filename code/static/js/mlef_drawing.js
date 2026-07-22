document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("anatomicalCanvas");
    const ctx = canvas.getContext("2d");

    let isDrawing = false;
    let x = 0;
    let y = 0;

    ctx.strokeStyle = "#e74c3c";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

    canvas.addEventListener("mousedown", (e) => {
        x = e.offsetX;
        y = e.offsetY;
        isDrawing = true;
    });

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

    window.addEventListener("mouseup", () => {
        if (isDrawing) {
            isDrawing = false;
        }
    });

    document.getElementById("clearBtn").addEventListener("click", () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    });

    document.getElementById("saveDrawingBtn").addEventListener("click", () => {
        const base64Image = canvas.toDataURL("image/png");
        console.log("Image Data Ready for Upload:", base64Image);
        alert("Drawing captured! Use 'Save Form' to save everything to the database.");
    });

    function collectFormData() {
        const caseId = document.getElementById("case_id").value;
        if (!caseId) {
            alert("Please select a case before saving.");
            return null;
        }

        const getVal = (name) => {
            const el = document.querySelector(`[name="${name}"]`);
            return el ? el.value : '';
        };
        const getChecked = (name) => {
            const el = document.querySelector(`[name="${name}"]`);
            return el ? el.checked : false;
        };

        return {
            case_id: parseInt(caseId),
            exam_date_time_place: getVal('exam_date_time_place'),
            date_of_birth: getVal('date_of_birth'),
            age: getVal('age'),
            identification_no: getVal('identification_no'),
            police_station: getVal('police_station'),
            date_of_issue: getVal('date_of_issue'),
            mlef_number: getVal('mlef_number'),
            examinee_name_address: getVal('examinee_name_address'),
            sex: getVal('sex'),
            police_age: getVal('police_age'),
            reason_for_examination: getVal('reason_for_examination'),
            produced_by: getVal('produced_by'),
            internal_injuries: getVal('internal_injuries'),
            bodily_harm: {
                contusion: getChecked('harm_contusion'),
                fracture: getChecked('harm_fracture'),
                stab: getChecked('harm_stab'),
                cut: getChecked('harm_cut'),
                dislocation: getChecked('harm_dislocation'),
                burns: getChecked('harm_burns'),
                laceration: getChecked('harm_laceration'),
                firearm: getChecked('harm_firearm'),
                none: getChecked('harm_none'),
                bite: getChecked('harm_bite'),
                explosive: getChecked('harm_explosive')
            },
            causative_weapon: {
                blunt: getChecked('weapon_blunt'),
                sharp: getChecked('weapon_sharp'),
                firearm: getChecked('weapon_firearm'),
                explosive: getChecked('weapon_explosive'),
                others: getChecked('weapon_others')
            },
            category_of_hurt: {
                non_grievous: getChecked('hurt_non_grievous'),
                grievous: getChecked('hurt_grievous'),
                fatal: getChecked('hurt_fatal')
            },
            anatomical_drawing: canvas.toDataURL("image/png")
        };
    }

    document.getElementById("saveFormBtn").addEventListener("click", () => {
        const data = collectFormData();
        if (!data) return;

        const btn = document.getElementById("saveFormBtn");
        btn.disabled = true;
        btn.textContent = "Saving...";

        fetch("/save_mlef", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                alert("MLEF form saved successfully!");
                window.location.href = "/view_cases";
            } else {
                alert("Error: " + (result.error || "Unknown error"));
                btn.disabled = false;
                btn.textContent = "Save Form";
            }
        })
        .catch(err => {
            alert("Network error: " + err.message);
            btn.disabled = false;
            btn.textContent = "Save Form";
        });
    });

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

    document.getElementById("discardBtn").addEventListener("click", () => {
        if (confirm("Discard the MLEF form and return to the dashboard?")) {
            window.location.href = "/dashboard";
        }
    });
});
