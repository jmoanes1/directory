/**
 * Profile page — avatar preview & remove
 */
(function () {
    'use strict';

    const form = document.getElementById('profileForm');
    if (!form) return;

    const fileInput = form.querySelector('.avatar-file-input');
    const removeBtn = document.getElementById('avatarRemoveBtn');
    const clearInput = document.getElementById('avatarClear');
    const initials = form.dataset.initials || '?';

    function getPreviewNodes() {
        return [
            document.querySelector('#profilePhotoPreview .avatar'),
            document.getElementById('avatarUploadPreview'),
        ].filter(Boolean);
    }

    function renderAvatar(el, imageUrl) {
        if (!el) return;
        el.innerHTML = '';
        if (imageUrl) {
            const img = document.createElement('img');
            img.src = imageUrl;
            img.alt = '';
            el.appendChild(img);
        } else {
            el.textContent = initials;
        }
    }

    function setPreviews(imageUrl) {
        getPreviewNodes().forEach(function (el) {
            renderAvatar(el, imageUrl);
        });
    }

  fileInput?.addEventListener('change', function () {
        const file = this.files && this.files[0];
        if (!file) return;
        if (clearInput) clearInput.value = '0';
        const url = URL.createObjectURL(file);
        setPreviews(url);
        if (removeBtn) removeBtn.hidden = false;
    });

    removeBtn?.addEventListener('click', function () {
        if (fileInput) fileInput.value = '';
        if (clearInput) clearInput.value = '1';
        setPreviews(null);
        removeBtn.hidden = true;
    });
})();
