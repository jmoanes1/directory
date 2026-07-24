/**
 * Company calendar — light enhancements for day cells.
 */
(function () {
    "use strict";

    document.querySelectorAll(".cal-day").forEach((dayCell) => {
        const events = dayCell.querySelectorAll(".cal-event");
        if (events.length <= 2) return;

        dayCell.classList.add("cal-day--busy");
        events.forEach((eventEl, index) => {
            if (index > 1) {
                eventEl.classList.add("cal-event--compact");
            }
        });
    });
})();
