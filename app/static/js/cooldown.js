const COOLDOWNS = [30, 60, 180, 300]; // seconds
const RESET_THRESHOLD_MS = 60 * 60 * 1000; // 60 minutes

document.addEventListener("DOMContentLoaded", () => {
    const boxes = document.querySelectorAll(".form-box");

    let box = null;
    let form = null;
    let btn = null;

    for (const candidate of boxes) {
        const candidateForm = candidate.closest("form");
        const candidateBtn = candidateForm?.querySelector("button");

        if (candidateForm && candidateBtn) {
            box = candidate;
            form = candidateForm;
            btn = candidateBtn;
            break;
        }
    }

    if (!box || !form || !btn) {
        console.log("No valid form-box with submit button found");
        return;
    }

    const keyBase = `cooldown_${location.pathname}_${form.action}`;
    const ATTEMPTS_KEY = `${keyBase}_attempts`;
    const UNTIL_KEY = `${keyBase}_until`;

    // Handle active cooldown on page refresh
    const initialUntil = Number(localStorage.getItem(UNTIL_KEY)) || 0;
    if (initialUntil > Date.now()) {
        startCooldown(btn, initialUntil);
    }

    form.addEventListener("submit", (e) => {
        const now = Date.now();
        const lastUntil = Number(localStorage.getItem(UNTIL_KEY)) || 0;
        let attempts = Number(localStorage.getItem(ATTEMPTS_KEY)) || 0;

        // 1. THE RESET LOGIC
        // If the last cooldown ended more than 20 minutes ago, reset attempts
        if (lastUntil > 0 && (now - lastUntil) > RESET_THRESHOLD_MS) {
            attempts = 0;
        }

        // 2. CALCULATE COOLDOWN
        const index = Math.min(attempts, COOLDOWNS.length - 1);
        const cooldownMs = COOLDOWNS[index] * 1000;
        const newUntil = now + cooldownMs;

        // 3. UPDATE STATE
        attempts++;
        localStorage.setItem(ATTEMPTS_KEY, attempts.toString());
        localStorage.setItem(UNTIL_KEY, newUntil.toString());

        startCooldown(btn, newUntil);
    });
});

function startCooldown(btn, until) {
    btn.disabled = true;
    const update = () => {
        const remaining = Math.ceil((until - Date.now()) / 1000);
        if (remaining <= 0) {
            btn.disabled = false;
            btn.textContent = "Submit";
            return true;
        }
        btn.textContent = `Wait ${remaining}s`;
        return false;
    };

    if (!update()) {
        const interval = setInterval(() => {
            if (update()) clearInterval(interval);
        }, 1000);
    }
}