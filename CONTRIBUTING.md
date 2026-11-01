# Contributing to SONORA Studio

Thank you for your interest in contributing to **SONORA Studio**! We welcome community contributions, bug reports, feature suggestions, and improvements to help make SONORA the most powerful, offline-first desktop audio studio for Windows.

---

## 🛠️ Development Setup

1. **Prerequisites:**
   - Windows 10 or 11 (64-bit recommended)
   - Python 3.10, 3.11, 3.12, or 3.15+ (64-bit)
   - Git

2. **Clone the repository:**
   ```bash
   git clone https://github.com/Venarus/sonora-studio.git
   cd sonora-studio
   ```

3. **Create and activate a virtual environment (optional but recommended):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **Run the application:**
   ```powershell
   python main.py
   ```

---

## 🧪 Testing Guidelines

Before submitting any Pull Request, ensure that all test suites pass without error:

```powershell
python -m unittest discover tests
```

To run a specific test suite:
```powershell
python -m unittest tests.test_dsp_and_ai
python -m unittest tests.test_editor_and_file
python -m unittest tests.test_integration
```

---

## 📐 Code Style & Conventions

- **PEP 8:** Follow standard Python formatting conventions.
- **Type Annotations:** Use Python type hints (`Optional`, `Tuple`, `List`, `Dict`) where applicable.
- **Thread Safety:** Never call GUI operations directly from real-time audio callback threads. Decouple audio and GUI via atomic variables or Qt signal/slots.
- **Non-Destructive Processing:** Any audio alteration or noise cleaning must preserve the user's original raw recording by default.
- **Commit Messages:** Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
  - `feat:` A new feature or capability
  - `fix:` A bug fix or patch
  - `refactor:` Code reorganization without behavioral change
  - `docs:` Documentation improvements
  - `style:` Visual or layout enhancements
  - `test:` Adding or updating tests
  - `chore:` Build scripts, dependencies, or maintenance

---

## 🚀 Submitting a Pull Request

1. Fork the repository and create your feature branch:
   ```bash
   git checkout -b feat/my-new-audio-tool
   ```
2. Commit your changes with descriptive commit messages.
3. Push to your fork:
   ```bash
   git push origin feat/my-new-audio-tool
   ```
4. Open a Pull Request on GitHub against the `main` branch with a clear description of the problem solved or feature added.
