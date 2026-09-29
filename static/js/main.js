document.addEventListener('DOMContentLoaded', function () {

    // --- Accordion toggle (product detail "Technical Specifications") ---
    document.querySelectorAll('.accordion-title').forEach(function (title) {
        title.addEventListener('click', function () {
            this.closest('.accordion-item').classList.toggle('active');
        });
    });

    // --- Catalog: "Product Type" checkboxes apply the filter right away ---
    document.querySelectorAll('[data-autosubmit]').forEach(function (input) {
        input.addEventListener('change', function () {
            document.getElementById(input.getAttribute('form')).submit();
        });
    });

    // --- Account page tabs (from the design mockup) ---
    var accountTabs = document.querySelectorAll('.account-tab');
    var tabPanes = document.querySelectorAll('.tab-pane');

    function openTab(selector) {
        var target = document.querySelector(selector);
        if (!target) {
            return;
        }
        accountTabs.forEach(function (tab) {
            tab.classList.toggle('active', tab.dataset.tabTarget === selector);
        });
        tabPanes.forEach(function (pane) {
            pane.classList.toggle('active', pane === target);
        });
    }

    accountTabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            openTab(this.dataset.tabTarget);
        });
    });
    if (accountTabs.length && window.location.hash) {
        openTab(window.location.hash);
    }

    // --- Staff product form: category tags (from the design mockup) ---
    document.querySelectorAll('.product-info-form .category-tags').forEach(function (container) {
        container.addEventListener('change', function (event) {
            container.querySelectorAll('.category-tag').forEach(function (tag) {
                tag.classList.toggle('active', tag.contains(event.target));
            });
        });
    });

    // --- Staff product form: image preview (from the design mockup) ---
    var uploadButton = document.getElementById('upload-image-btn');
    var fileInput = document.getElementById('image-upload-input');
    if (uploadButton && fileInput) {
        uploadButton.addEventListener('click', function () {
            fileInput.click();
        });
        fileInput.addEventListener('change', function (event) {
            var file = event.target.files[0];
            if (!file) {
                return;
            }
            var reader = new FileReader();
            var placeholder = document.querySelector('.image-upload-placeholder');
            reader.onload = function (e) {
                placeholder.innerHTML = '';
                placeholder.style.backgroundImage = "url('" + e.target.result + "')";
                placeholder.style.backgroundSize = 'cover';
                placeholder.style.backgroundPosition = 'center';
            };
            reader.readAsDataURL(file);
        });
    }

    // --- Buttons that need a confirmation (e.g. Delete product) ---
    document.querySelectorAll('[data-confirm]').forEach(function (button) {
        button.addEventListener('click', function (event) {
            if (!window.confirm(button.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

});
