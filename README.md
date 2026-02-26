🍕 AI-Powered Restaurant Assistant (RAG + Agent + Voice)

An intelligent restaurant assistant built with LLM + RAG + structured order handling.

This project allows users to:
	•	🔎 Ask questions about the menu (ingredients, price, categories)
	•	🥗 Request diet-based recommendations (vegan, vegetarian, gluten-free, etc.)
	•	🛒 Create and modify orders using natural language
	•	🔊 Receive voice responses (Text-to-Speech)
	•	🧠 Maintain conversational memory

⸻

🚀 Tech Stack
	•	FastAPI – Backend API
	•	LangChain – LLM orchestration
	•	OpenAI (GPT-4o-mini) – Language model
	•	FAISS – Vector search (RAG)
	•	gTTS – Text-to-Speech
	•	Pandas – Menu data processing
	•	HTML + CSS + JavaScript – Lightweight frontend

⸻

🧠 System Architecture

🔹 Normal Queries

User → RAG Retrieval → LLM → Response

🔹 Diet / Allergen Queries

User → Full Menu Context → LLM (evidence-based filtering)

🔹 Order Creation

User → LLM JSON output → Order Manager → Updated State

📂 Project Structure
.
├── app1/
│   ├── main.py
│   ├── rag.py
│   ├── orders.py
│   ├── intent.py
│   ├── schemas.py
├── data1/
│   └── menu1.csv
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── requirements.txt
├── .env.example
└── README.md

▶️ Run the Application
uvicorn app1.main:app --reload

💬 Example Queries
	•	“Menüde ne var?”
	•	“En az 3 vegan yemek öner”
	•	“Glutensiz tatlı var mı?”
	•	“2 adet Margarita sipariş etmek istiyorum”
	•	“Siparişimin özeti nedir?”

🧠 Key Features

✔ Retrieval-Augmented Generation (RAG)

Ensures responses are grounded in the actual menu dataset.

✔ Evidence-Based Diet Filtering

For vegan / vegetarian / gluten-free queries, the assistant:
	•	Uses full menu context
	•	Justifies suggestions with ingredient evidence
	•	Avoids hallucinated items

✔ Structured Order Handling

Order actions are returned in strict JSON format:

✔ Voice Output

Responses are converted into speech using gTTS.

📌 Future Improvements
	•	Docker support
	•	Database-backed order storage
	•	Admin panel for menu updates
	•	Real-time WebSocket communication
	•	Multi-language support(only Turkish rn)

👩‍💻 Author

Gaye Çetindere
AI Engineer | LLM Systems | RAG Architectures