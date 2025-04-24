let failCount = 0;

$(document).ready(function() {
  $("#login-form").submit(function(e) {
    e.preventDefault();

    let email = $("#email-login").val();
    let password = $("#password-login").val();

    let data = JSON.stringify({ email: email, password: password });
    

    $.ajax({
      url: "/processlogin",
      type: "POST",
      contentType: "application/json",
      data: data,
      success: function(response) {
        // Ensure response is parsed as JSON
        let result = typeof response === "string" ? JSON.parse(response) : response;

        if (result.success) {
          window.location.href = "/schedule";
        } else {
          failCount++;
          $("#login-message").text(`Login failed. Attempt #${failCount}`);
        }
      },
      error: function() {
        failCount++;
        $("#login-message").text(`Login failed. Attempt #${failCount} (server error)`);
      }
    });
  });
});

document.addEventListener('DOMContentLoaded', function () {
    document.querySelector(".button-register").addEventListener("click", function () {
        window.location.href = "/register";
    });
});


