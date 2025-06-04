document.addEventListener('DOMContentLoaded', function() {
    // Image preview functionality
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            const preview = document.getElementById('image-preview');
            
            if (file && preview) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.innerHTML = `
                        <img src="${e.target.result}" 
                             class="profile-image-preview" 
                             alt="Bildvorschau">
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    });
    
    // Auto-calculate valid_until date
    const issuedDateInput = document.querySelector('input[name="issued_date"]');
    if (issuedDateInput) {
        issuedDateInput.addEventListener('change', function() {
            const issuedDate = new Date(this.value);
            if (issuedDate) {
                const validUntil = new Date(issuedDate);
                validUntil.setFullYear(validUntil.getFullYear() + 5);
                
                const validUntilDisplay = document.getElementById('valid-until-display');
                if (validUntilDisplay) {
                    validUntilDisplay.textContent = `Gültig bis: ${validUntil.toLocaleDateString('de-DE')}`;
                }
            }
        });
    }
});
