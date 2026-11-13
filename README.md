# Quizly Backend

![Python](https://img.shields.io/badge/Python-3-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1.3-092E20?logo=django&logoColor=white)
![Django REST Framework](https://img.shields.io/badge/Django%20REST%20Framework-3.18.3-red)
![License](https://img.shields.io/badge/License-MIT-green)

Quizly turns YouTube videos into interactive multiple-choice quizzes. This repository provides the Django REST API: it downloads a video's audio, transcribes it with Whisper, asks Gemini to generate questions, and saves the validated quiz for its owner.

The [Quizly frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly) is maintained in a separate repository.

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Frontend pages](#frontend-pages)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Frontend configuration](#frontend-configuration)
- [Authentication](#authentication)
- [API reference](#api-reference)
- [Video processing and model settings](#video-processing-and-model-settings)
- [Testing](#testing)
- [Security and deployment](#security-and-deployment)
- [License](#license)

## Features

- Register, log in, refresh a session, and log out using JWT authentication.
- Generate a quiz from a YouTube URL.
- List, retrieve, update, and delete your own quizzes.
- Play generated multiple-choice quizzes in the separate frontend.

## How it works

1. Register and log in, then submit a YouTube URL.
2. The backend downloads an audio track and transcribes it using Whisper.
3. Gemini generates a title, description, and questions from the transcript.
4. The backend validates and saves the quiz and its questions together.
5. In the frontend, open the quiz, select answers, and review the score and correct answers.

Each generated quiz contains **10 questions** with **4 distinct options** and one matching correct answer per question. Generation runs synchronously, so the request may take some time. Quiz responses include the correct answers; this API is not designed to hide them from clients.

## Frontend pages

The following titles refer to the linked frontend repository, not pages served by this backend.

| Page | Browser title | Purpose |
| --- | --- | --- |
| Home | Quizly | Entry point with registration and login links |
| Registration | Quizly - Registration | Create an account |
| Login | Quizly - Login | Sign in |
| Library | Quizly-Library | Generate a quiz and view recent quizzes |
| Quiz overview | Quizly - Quiz | View a quiz and edit its title and description |
| Quiz | Quizly - Quiz | Answer questions, see results, review answers, or replay |

## Tech stack

| Component | Technology |
| --- | --- |
| API | Python, Django, Django REST Framework |
| Authentication | Simple JWT and cookie-based authentication |
| Database | SQLite |
| Audio download | yt-dlp |
| Transcription | OpenAI Whisper and FFmpeg |
| Quiz generation | Google Gemini |
| Tests | Django's test runner |

See [requirements.txt](requirements.txt) for the dependency versions.

## Project structure

```text
Quizly-Backend/
├── auth_app/          # Registration, JWT authentication, and token handling
├── core/              # Django settings and root URL configuration
├── quiz_app/          # Quiz models, API, and generation services
├── manage.py          # Django management commands
├── requirements.txt   # Python dependencies
└── LICENSE            # MIT license
```

## Getting started

### Prerequisites

- Git and a Python version compatible with the dependencies in [requirements.txt](requirements.txt).
- An internet connection and a Google Gemini API key with access to the configured model.
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your `PATH`.

On Windows, install FFmpeg with WinGet, then open a new terminal if needed:

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
```

If the version command fails, check your `PATH` and the FFmpeg installation instructions for your operating system.

### 1. Clone the backend

In an **empty directory**, run:

```bash
git clone git@github.com:gloedige/Quizly-Backend.git .
```

This SSH URL requires GitHub SSH access. The current directory is now the repository root.

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source .venv/bin/activate
```


### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment configuration(.env)

1. Copy the provided template file to create your local .env file:

macOS / Linux / Git Bash:

```bash
cp .env.template .env
```

Windows PowerShell:

```powershell
Copy-Item .env.template .env
```

Windows Command Prompt:

```cmd
copy .env.template .env
```

2. Open the newly created .env file and insert your actual credentials:

# Gemini API Key for quiz generation
GEMINI_API_KEY=dein_gemini_api_key_hier_einfügen

`GEMINI_API_KEY` is required for quiz generation. Never commit API keys or real credentials; `.env` is ignored by Git. Model availability and API access depend on your Google account.

### 5. Initialize the database and start the server

```bash
python manage.py migrate
python manage.py runserver
```

The development API is available at `http://127.0.0.1:8000/api/`. Migrations create the database schema but **do not create a guest account**. Register a user through the API or frontend before logging in.

## Frontend configuration

Clone and serve the [separate frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly) using a local web server. Its configuration file is `shared/js/config.js`; set `API_BASE_URL` to your backend's API URL, including `/api/`. The linked frontend defaults to `http://127.0.0.1:8000/api/`.

If your frontend version provides a guest login, create a corresponding user separately and adjust that version's guest-login configuration. Do not publish real credentials. The desired frontend page size is `PAGE_SIZE = 3`; check your frontend version before adding or using this setting. The backend does not currently configure pagination.

The frontend and API may run on different origins. The current backend does not configure CORS; browser requests from a separate origin therefore need appropriate CORS and credential settings, or a suitable same-origin reverse proxy. See the [authentication notes](#authentication) for cookie requirements.

## Authentication

Login sets `access_token` and `refresh_token` cookies with `HttpOnly`, `Secure`, and `SameSite=Lax` attributes. The access token expires after **10 minutes**; the refresh token expires after **one day**. Refreshing rotates the refresh token and blacklists the previous one. Logout clears the cookies and revokes the tokens.

For cookie-based requests, include cookies in the client, for example with `credentials: "include"` in browser requests. The authentication class also accepts a valid `Authorization: Bearer <access_token>` header, but refresh uses the refresh cookie and logout requires the access cookie. Users can access and modify only their own quizzes.

`Secure` cookies generally require HTTPS; browser handling of localhost exceptions can vary. For local testing, verify that your client stores and sends them, or use a properly configured local HTTPS setup. For cross-origin deployments, configure CORS and cookie policies appropriately; `SameSite=Lax` can restrict cross-site requests.

## API reference

All paths are relative to `http://127.0.0.1:8000` during local development.

| Method | Endpoint | Authentication | Description |
| --- | --- | --- | --- |
| `POST` | `/api/register/` | Public | Create an account |
| `POST` | `/api/login/` | Public | Log in and set authentication cookies |
| `POST` | `/api/token/refresh/` | Refresh cookie | Rotate the refresh token and set new cookies |
| `POST` | `/api/logout/` | Access cookie | Revoke tokens and clear cookies |
| `GET` | `/api/quizzes/` | Access token | List your quizzes |
| `POST` | `/api/quizzes/` | Access token | Generate and save a quiz from a YouTube URL |
| `GET` | `/api/quizzes/{id}/` | Access token | Retrieve your quiz and its questions |
| `PATCH` | `/api/quizzes/{id}/` | Access token | Update its title and/or description |
| `DELETE` | `/api/quizzes/{id}/` | Access token | Delete your quiz |

### Example requests

Register with `POST /api/register/`:

```json
{
	"username": "example_user",
	"email": "user@example.com",
	"password": "replace-with-a-password",
	"confirmed_password": "replace-with-a-password"
}
```

Log in with `POST /api/login/`:

```json
{
	"username": "example_user",
	"password": "replace-with-a-password"
}
```

Generate a quiz with `POST /api/quizzes/`:

```json
{
	"url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

Replace `VIDEO_ID` with a valid 11-character YouTube video ID. Creation returns the quiz with its questions when generation succeeds. A generation failure returns a `400` response; check the video, environment, model availability, and server diagnostics.

Update a quiz with `PATCH /api/quizzes/{id}/`:

```json
{
	"title": "Updated quiz title",
	"description": "Updated quiz description."
}
```

## Video processing and model settings

The limits and default Gemini model are defined in [quiz_app/services.py](quiz_app/services.py):

| Setting | Default | Meaning |
| --- | --- | --- |
| `MAX_VIDEO_LENGTH` | `600` | Maximum video duration: 10 minutes |
| `MAX_VIDEO_SIZE` | `30M` | Select an audio track under 30 MB based on available size metadata; not the total video file size |
| `AI_MODEL_VERSION` | `gemini-3.8-flash` | Default Gemini model; overridden by `GEMINI_MODEL` |
| `WHISPER_MODEL` | `base` | Default Whisper model; overridden by the environment variable |

Audio is stored temporarily and removed after processing. Whisper may download its model on first use; transcription can be resource-intensive, especially on a CPU. yt-dlp may emit warnings when YouTube JavaScript challenges cannot be solved. See the [yt-dlp EJS documentation](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for supported runtimes and challenge-solver options; these are not automatically enabled by this project.

## Testing

Run the backend test suite from the repository root:

```bash
python manage.py test
```

To test manually with Postman, register and log in first, verify that the client stores and sends the authentication cookies, then call the quiz endpoints. Creating a real quiz also requires a working Gemini key, accessible video, and the processing dependencies described above.

## Security and deployment

The current Django settings are intended for local development, not production. Before deployment, configure a secure secret key, disable debug mode, set allowed hosts, enable HTTPS, and configure CORS and cookie policies for your environment. Keep secrets outside version control and follow the [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/).

## License

Distributed under the [MIT License](LICENSE).