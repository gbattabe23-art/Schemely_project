// ================= NAVBAR SHADOW =================
window.addEventListener('scroll', () => {
  const nav = document.querySelector('.navbar');
  nav.style.boxShadow = window.scrollY > 50 
      ? '0 4px 8px rgba(0,0,0,0.2)' 
      : 'none';
});

// ================= MOBILE MENU =================
const menuIcon = document.getElementById('menu-icon');
const navLinks = document.querySelector('.navbar ul');

if (menuIcon) {
  menuIcon.addEventListener('click', () => {
    navLinks.classList.toggle('active');
  });
}

// ================= TAG BUTTON LOGIC =================
document.querySelectorAll(".tag-btn").forEach(btn => {
  btn.addEventListener("click", () => btn.classList.toggle("active"));
});

// ==================================================================
//                     ⭐ LOGIN API ⭐
// ==================================================================
document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.querySelector(".login-form");

  if (!loginForm) return;

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = loginForm.querySelector("input[type='email']").value.trim();
    const password = loginForm.querySelector("input[type='password']").value.trim();

    if (!email || !password) {
      alert("Please fill all fields.");
      return;
    }

    const res = await fetch("https://backendofse.onrender.com/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    alert(data.msg);

    if (data.ok) {
      window.location.href = "recommend.html"; 
    }
  });
});

// ==================================================================
//                     ⭐ SIGNUP API (MATCHED TO YOUR HTML) ⭐
// ==================================================================
document.addEventListener("DOMContentLoaded", () => {

  const signupForm = document.querySelector(".signup-form");
  if (!signupForm) return;

  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    // तुम्‍हारे form में 3 input हैं exactly इसी order में:
    // 1. Name, 2. Email, 3. Password
    const inputs = signupForm.querySelectorAll("input");
    const name = inputs[0].value.trim();
    const email = inputs[1].value.trim();
    const password = inputs[2].value.trim();

    // front-end validation
    if (!name || !email || !password) {
      alert("Account Not Created! Please fill all fields.");
      return;
    }

    try {
      const res = await fetch("https://backendofse.onrender.com/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password })
      });

      const data = await res.json();
      alert(data.msg);

      if (data.ok) {
        window.location.href = "recommend.html";
      }

    } catch (error) {
      alert("Account Not Created! Server Error.");
      console.error(error);
    }
  });
});

// ==================================================================
//                     ⭐ RECOMMEND FORM ⭐
// ==================================================================
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".recommend-form");
  const resultsSection = document.getElementById("results-section");
  const cardsGrid = document.getElementById("cards-grid");
  const resultsCount = document.getElementById("results-count");
  const pdfBtn = document.getElementById("download-pdf");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const selects = form.querySelectorAll("select");
    const payload = {
      age: parseInt(form.querySelector('input[type="number"]').value || 0),
      gender: selects[0].value.toLowerCase(),
      education: selects[1].value.toLowerCase(),
      area: selects[2].value.toLowerCase(),
      state: selects[3].value.toLowerCase(),
      tags: Array.from(document.querySelectorAll(".tag-btn.active"))
                .map(b => b.innerText.trim())
    };

    resultsSection.style.display = "block";
    resultsCount.innerText = "Finding schemes...";
    cardsGrid.innerHTML = "";

    try {
      const res = await fetch("https://seproject-t9fv.onrender.com/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      window.currentSchemes = data.results;

      resultsCount.innerText = `Found ${data.count} Schemes`;
      cardsGrid.innerHTML = "";

      if (data.count === 0) {
        cardsGrid.innerHTML = "<p>No relevant schemes found.</p>";
        pdfBtn.style.display = "none";
        return;
      }

      data.results.forEach((s, i) => {
        cardsGrid.innerHTML += `
          <div class="scheme-card">
            <div class="scheme-top">
              <span class="scheme-num">${i + 1}</span>
              <span class="scheme-state">${s.state}</span>
            </div>
            <h3 class="scheme-title">${s.scheme_name}</h3>
            <p class="scheme-summary">${s.summary}</p>
            <div class="scheme-cta">
              <a class="apply-btn" href="${s.link}" target="_blank">Apply Now</a>
            </div>
          </div>
        `;
      });

      pdfBtn.style.display = "inline-block";
      resultsSection.scrollIntoView({ behavior: "smooth" });

    } catch (err) {
      console.error(err);
      resultsCount.innerText = "Error fetching schemes.";
      cardsGrid.innerHTML = "<p>Server error. Try again.</p>";
    }
  });
});

// ==================================================================
//                     ⭐ DOWNLOAD PDF ⭐
// ==================================================================
const pdfButton = document.getElementById("download-pdf");

if (pdfButton) {
  pdfButton.addEventListener("click", async () => {
    if (!window.currentSchemes || window.currentSchemes.length === 0) {
      alert("No schemes to download!");
      return;
    }

    const res = await fetch("https://seproject-t9fv.onrender.com/download-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schemes: window.currentSchemes })
    });

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "schemes.pdf";
    a.click();
    window.URL.revokeObjectURL(url);  
  });
}
