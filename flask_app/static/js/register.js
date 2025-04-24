let failCount = 0;

$(document).ready(function() {
    $("#register-form").submit(function(e) {
        e.preventDefault();

        let email = $("#email-login").val();
        let password = $("#password-login").val();

        let data = JSON.stringify({ email: email, password: password });

        $.ajax({
            url: "/register",
            type: "POST",
            contentType: "application/json",
            data: data,
            success: function(response) {
                if (response.success) {
                    window.location.href = "/schedule";  // Redirect to schedule page
                } else {
                    $("#register-message").text(response.error || 'Registration failed.');
                }
            },
            error: function(xhr, status, error) {
                let errorMessage = "Registration failed.";
            
                // Try to get a useful error message if available
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMessage = `Registration failed: ${xhr.responseJSON.error}`;
                } else if (xhr.responseText) {
                    try {
                        const parsed = JSON.parse(xhr.responseText);
                        if (parsed.error) errorMessage = `Registration failed: ${parsed.error}`;
                    } catch (e) {
                        // fallback to status code
                        errorMessage = `Registration failed: ${xhr.statusText}`;
                    }
                }
            
                $("#register-message").text(errorMessage);
            }
        });
    });
});
