document.addEventListener("DOMContentLoaded", () => {

    // ⚠️ IMPORTANT: UPDATE THIS WITH YOUR RENDER URL
    const API_BASE_URL = "http://127.0.0.1:5001";

    // --- 1. DOM ELEMENTS ---
    const describeBtn = document.getElementById("desiDescribeBtn");
    const chatModal = document.getElementById("chatModal");
    const closeChatBtn = document.getElementById("closeChat");
    const chatMessages = document.getElementById("chatMessages");

    // Dynamic Elements
    let startOptions = document.getElementById("startOptions");
    let languageSelect = document.getElementById("languageSelect");

    // UI Sections
    const inputForm = document.getElementById("inputForm");
    const fileInput = document.getElementById("imageUploadInput");

    // Inputs
    const businessInput = document.getElementById("businessType");
    const adTypeInput = document.getElementById("adType");
    const productDescInput = document.getElementById("productDesc");
    const formatSelect = document.getElementById("formatSelect");

    // Buttons
    const sloganBtn = document.getElementById("generateSloganBtn");
    const posterBtn = document.getElementById("generatePosterBtn");
    const micBtn = document.getElementById("micBtn");

    // --- 2. SPEECH RECOGNITION LOGIC (NEW) ---
    if (micBtn) {
        // Check browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = false; // Stop after one sentence
            recognition.interimResults = false;

            // Language Mapping: Dropdown Value -> Speech Code
            const langMap = {
                'English': 'en-US',
                'Hindi': 'hi-IN',
                'Spanish': 'es-ES',
                'French': 'fr-FR',
                'German': 'de-DE',
                'Tamil': 'ta-IN',
                'Marathi': 'mr-IN'
            };

            micBtn.addEventListener("click", () => {
                if (micBtn.classList.contains("listening")) {
                    recognition.stop();
                } else {
                    // Set language based on current dropdown selection
                    const currentLang = document.getElementById("languageSelect").value;
                    recognition.lang = langMap[currentLang] || 'en-US';
                    recognition.start();
                }
            });

            recognition.onstart = () => {
                micBtn.classList.add("listening");
                productDescInput.placeholder = "Listening... Speak now!";
            };

            recognition.onend = () => {
                micBtn.classList.remove("listening");
                productDescInput.placeholder = "Describe product details...";
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                // Append text if input already has content
                if (productDescInput.value) {
                    productDescInput.value += " " + transcript;
                } else {
                    productDescInput.value = transcript;
                }
            };

            recognition.onerror = (event) => {
                console.error("Speech Error:", event.error);
                micBtn.classList.remove("listening");
            };
        } else {
            micBtn.style.display = "none"; // Hide mic if browser doesn't support it
            console.log("Web Speech API not supported in this browser.");
        }
    }

    // --- 3. MODE SWITCHING ---
    window.startManual = function () {
        startOptions = document.getElementById("startOptions");
        languageSelect = document.getElementById("languageSelect");
        const lang = languageSelect ? languageSelect.value : "English";

        if (startOptions) startOptions.style.display = "none";
        if (inputForm) inputForm.style.display = "flex";

        addMessage(`✍️ Manual Mode selected (${lang}).`, "user");
        addMessage("Okay! Fill in the form below.", "bot");
    };

    window.startUpload = function () {
        if (fileInput) fileInput.click();
    };

    // --- 4. HANDLE FILE UPLOAD (VISION) ---
    if (fileInput) {
        fileInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (startOptions) startOptions.style.display = "none";
            addMessage("📸 Uploading image...", "user");
            addMessage("Analyzing image details... 🧠", "bot");

            const formData = new FormData();
            formData.append("file", file);

            try {
                const res = await fetch(`${API_BASE_URL}/analyze-image`, { method: "POST", body: formData });
                const result = await res.json();

                if (result.status === "success") {
                    businessInput.value = result.business_type;
                    productDescInput.value = result.description;
                    inputForm.style.display = "flex";
                    addMessage(`I see: "${result.description}".`, "bot");
                    const lang = document.getElementById("languageSelect").value;
                    addMessage(`Form auto-filled! Ready to generate in ${lang}?`, "bot");
                } else {
                    addMessage("❌ Analysis failed: " + (result.error || "Unknown error"), "bot");
                    inputForm.style.display = "flex";
                }
            } catch (err) {
                console.error(err);
                addMessage("❌ Network Error. Is the backend running?", "bot");
                inputForm.style.display = "flex";
            }
        });
    }

    // --- 5. HELPER FUNCTIONS ---
    function addMessage(content, type = "bot", isImage = false) {
        const div = document.createElement("div");
        div.className = `message ${type}`;

        if (isImage) {
            const container = document.createElement("div");
            container.className = "image-container";

            const img = document.createElement("img");
            img.src = content;
            img.onload = () => { chatMessages.scrollTop = chatMessages.scrollHeight; };

            const downloadBtn = document.createElement("a");
            downloadBtn.href = content;
            downloadBtn.download = `DesiScribe_Ad_${Date.now()}.jpg`;
            downloadBtn.className = "download-icon";
            downloadBtn.innerHTML = '<i class="fa-solid fa-download"></i>';

            container.appendChild(img);
            container.appendChild(downloadBtn);
            div.appendChild(container);
        } else {
            div.textContent = content;
        }
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function getFormData() {
        const business = businessInput.value.trim();
        const desc = productDescInput.value.trim();

        // Safe access to elements in case of re-render
        const langEl = document.getElementById("languageSelect");
        const lang = langEl ? langEl.value : "English";
        const fmtEl = document.getElementById("formatSelect");
        const fmt = fmtEl ? fmtEl.value : "Square";

        if (!business || !desc) {
            alert("Please enter a Business Name and Product Description!");
            return null;
        }

        return {
            business_type: business,
            ad_type: adTypeInput.value,
            product_description: desc,
            language: lang,
            format: fmt
        };
    }

    // --- 6. GENERATION BUTTONS ---
    if (sloganBtn) {
        sloganBtn.addEventListener("click", async () => {
            const data = getFormData();
            if (!data) return;

            addMessage(`📝 Generating ${data.language} slogan...`, "user");
            sloganBtn.disabled = true;
            sloganBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

            try {
                const response = await fetch(`${API_BASE_URL}/generate-slogan`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                if (result.status === "success") {
                    addMessage(`✨ "${result.slogan}"`, "bot");
                } else {
                    addMessage("❌ Error: " + result.error, "bot");
                }
            } catch (err) {
                addMessage("❌ Network Error.", "bot");
            }
            sloganBtn.disabled = false;
            sloganBtn.innerHTML = '<i class="fa-solid fa-pen-nib"></i> Slogan';
        });
    }

    if (posterBtn) {
        posterBtn.addEventListener("click", async () => {
            const data = getFormData();
            if (!data) return;

            addMessage(`🎬 Designing ${data.format} ad...`, "user");
            posterBtn.disabled = true;
            posterBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

            try {
                const response = await fetch(`${API_BASE_URL}/generate-poster`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                if (result.status === "success") {
                    addMessage("✨ Design Ready!", "bot");
                    addMessage(result.image_url, "bot", true);
                    addMessage(`Slogan: "${result.slogan}"`, "bot");
                } else {
                    addMessage("❌ Error: " + (result.error || "Unknown"), "bot");
                }
            } catch (err) {
                addMessage("❌ Network Error.", "bot");
            }
            posterBtn.disabled = false;
            posterBtn.innerHTML = '<i class="fa-solid fa-clapperboard"></i> Generate';
        });
    }

    // --- 7. MODAL RESET ---
    if (describeBtn) {
        describeBtn.addEventListener("click", () => {
            chatModal.classList.add("active");
            if (inputForm) inputForm.style.display = "none";

            // Re-inject HTML to reset chat state
            chatMessages.innerHTML = `
                <div class="message bot">Hi! Pick a language & start! 👇</div>
                <div id="startOptions" class="option-container" style="flex-direction: column; gap: 15px;">
                    <select id="languageSelect" style="background: #1f2940; color: white; border: 1px solid #5876ff; padding: 10px; border-radius: 10px; width: 80%; margin: 0 auto;">
                        <option value="English">🇬🇧 English</option>
                        <option value="Hindi">🇮🇳 Hindi (हिंदी)</option>
                        <option value="Spanish">🇪🇸 Spanish</option>
                        <option value="French">🇫🇷 French</option>
                        <option value="German">🇩🇪 German</option>
                        <option value="Tamil">🇮🇳 Tamil</option>
                        <option value="Marathi">🇮🇳 Marathi</option>
                    </select>
                    <div style="display: flex; gap: 10px; justify-content: center;">
                        <button onclick="startManual()" class="option-btn">✍️ Enter Details</button>
                        <button onclick="startUpload()" class="option-btn">📸 Upload Photo</button>
                    </div>
                </div>
            `;
            startOptions = document.getElementById("startOptions");
            languageSelect = document.getElementById("languageSelect");
        });
    }

    if (closeChatBtn) {
        closeChatBtn.addEventListener("click", () => {
            chatModal.classList.remove("active");
        });
    }
});