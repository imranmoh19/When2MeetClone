let currentMode = "available";
let isDragging = false;

$(document).ready(function () {
  $("#availability-mode").on("change", function () {
    currentMode = $(this).val();
  });

  $(".slot").on("mousedown", function (e) {
    e.preventDefault();
    applyMode($(this));
    isDragging = true;
  });

  $(document).on("mouseup", function () {
    isDragging = false;
  });

  $(".slot").on("mouseover", function () {
    if (isDragging) {
      applyMode($(this));
    }
  });

  // Load existing availability data
  $.get("/get_availability", { event_id: eventId }, function (data) {
    data.forEach(function (entry) {
      const selector = `.slot[data-date='${entry.date}'][data-time='${entry.time}']`;
      $(selector).addClass(entry.mode);
    });
  });
});

function applyMode(cell) {
  cell.removeClass("available maybe unavailable").addClass(currentMode);

  const date = cell.data("date");
  const time = cell.data("time");

  $.post("/update_availability", {
    event_id: eventId,
    date: date,
    time: time,
    mode: currentMode
  });
}
