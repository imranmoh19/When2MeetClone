document.addEventListener('DOMContentLoaded', function () {
    document.querySelector(".event-create").addEventListener("click", function () {
      window.location.href = "/event_create";
    });

    document.querySelector(".event-join").addEventListener("click", function () {
      window.location.href = "/event_join";
    });
});
