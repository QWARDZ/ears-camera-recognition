$(document).ready(function() {
    $('#departmentTable').DataTable();

    var departmentModal = document.getElementById("departmentModal");
    var departmentNameInput = document.getElementById("department_name");
    var departmentIdInput = document.getElementById("department_id");

    window.showAddDepartmentForm = function() {
        departmentNameInput.value = '';
        departmentIdInput.value = ''; 
        departmentModal.style.display = "block";
    };

    window.editDepartment = function(id, name) {
        departmentIdInput.value = id;
        departmentNameInput.value = name;
        departmentModal.style.display = "block";
    };

    window.closeModal = function() {
        departmentModal.style.display = "none";
    };

    window.onclick = function(event) {
        if (event.target == departmentModal) {
            departmentModal.style.display = "none";
        }
    };
});
