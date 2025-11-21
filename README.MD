# 🌸 SereniTree — Your Digital Wellness Sanctuary

**SereniTree** is a pastel-themed Mood Journal web application designed to help users track, analyze, and gain insights into their daily moods. The app leverages **AI-powered sentiment analysis** to provide personalized emotional insights and trends.

[Live App](https://final-project-uym7.onrender.com) | [Pitch Deck](https://gamma.app/docs/SereniTree-Your-Digital-Wellness-Sanctuary-3craysc6v3hrqe5)

---

## 📝 Features

### Core Functionality

* **User Authentication**: Secure registration and login with JWT.
* **Journal Entries**: Create, edit, and track daily moods.
* **AI Sentiment Analysis**: Each entry is analyzed by the **SereniTree bot** for positivity, negativity, and neutrality.
* **Dashboard & Insights**:

  * Visualize mood trends using interactive charts.
  * Compare weekly averages and detect improvements or declines.
  * Quick overview of recent entries for reflection.
* **Pastel A+1 Theme**: Calm, soothing UI designed for comfort and readability.
* **Navigation**: Intuitive access between Dashboard and New Entry pages.

---

### Backend

* Node.js + Express API
* MongoDB for persistent storage
* Hugging Face API for AI sentiment scoring

### Frontend

* React.js with a soft pastel UI
* Responsive, accessible design
* Local and global state management

---

## 💻 Installation

1. Clone the repository:

```bash
git clone <github.com/GreenVika/Final-Project>
cd mood-journal-mern
```

2. Install dependencies:

```bash
# Backend
cd backend
npm install

# Frontend
cd ../frontend
npm install
```

3. Configure `.env`:

**Backend `.env` example:**

```
PORT=5000
MONGO_URI=<your_mongodb_uri>
HF_API_KEY=<your_huggingface_api_key>
```

4. Start the development servers:

```bash
# Backend
cd backend
npm start

# Frontend
cd ../frontend
npm start
```

Visit `http://localhost:3000` to view the app.

---

## 🎨 UI & Theme

* **Body Background**: Soft pastel pink `#ffe4e6`
* **Primary Buttons & Headings**: Lavender `#7c3aed`
* **Links**: Pastel Blue `#4f46e5`
* **Cards**: White with subtle shadows
* **Spacing**: Adequate padding and margins for forms, lists, and dashboard sections for readability and calm UX.

---

## 🤖 SereniTree Bot

* Powered by **Hugging Face AI** for sentiment analysis.
* Scores journal entries on positivity, negativity, and neutrality.
* Generates personalized insights, weekly trend comparisons, and suggestions.
* Includes robust fallback handling if the AI API fails.

---

## 📂 File Structure

```
mood-journal-mern/
├─ backend/
│  ├─ controllers/
│  ├─ models/
│  ├─ routes/
│  ├─ server.js
├─ frontend/
│  ├─ src/
│  │  ├─ components/
│  │  ├─ api.js
│  │  ├─ App.jsx
│  ├─ public/
├─ README.md
```

---

## 📊 Pitch Deck

You can explore the full project pitch here: [SereniTree Pitch Deck](https://gamma.app/docs/SereniTree-Your-Digital-Wellness-Sanctuary-3craysc6v3hrqe5)

**Key slides included:**

1. Project Overview & Tagline
2. Problem Statement
3. Solution Overview
4. Features & AI Bot
5. Technology Stack
6. UI Screenshots & Demo
7. Market & Impact
8. Future Enhancements
9. Team & Contact Info

---

## 🚀 Usage

1. Register or login to access your personalized dashboard.
2. Add daily journal entries and let **SereniTree** analyze your mood.
3. Review charts and weekly insights to track your emotional trends.
4. Use the **Dashboard** to view recent entries and insights at a glance.

---

## 📌 License & Acknowledgments

* Developed by **[GreenVika]**
* Powered by **MERN Stack** and **Hugging Face API**
* Inspired by mindfulness and digital wellness practices.
