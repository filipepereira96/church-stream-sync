# Contributing to Church Stream Sync

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 📋 Code of Conduct

This project adopts a code of conduct. By participating, you agree to maintain a respectful and collaborative environment.

## 🚀 How to Contribute

### Reporting Bugs

If you found a bug, open an issue with:
- **Clear description** of the problem
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Screenshots** (if applicable)
- **Windows version** and relevant **logs**

### Suggesting Improvements

To suggest improvements:
- Check if there isn't already a similar issue
- Clearly describe the proposed improvement
- Explain why it would be useful
- Provide usage examples, if possible

### Pull Requests

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/filipepereira96/church-stream-sync.git`
3. **Create a branch** for your feature: `git checkout -b feature/MyFeature`
4. **Make your changes**
5. **Test** your changes
6. **Commit** following the standard: `git commit -m "feat: add feature X"`
7. **Push** to your branch: `git push origin feature/MyFeature`
8. Open a **Pull Request**

## 📝 Code Standards

### Python

- Follow **PEP 8**
- Use **type hints** when possible
- Docstrings in **all public functions**
- Maximum **88 characters** per line (Black formatter)

Example:
```python
def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of the numbers
    """
    return a + b
```

### Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Refactoring
- `test:` - Tests
- `chore:` - Maintenance

Example:
```
feat: add support for multiple audio PCs
fix: fix timeout error in shutdown
docs: update installation guide
```

## 🧪 Testing

Before submitting a PR:

1. **Manually test** the changes
2. **Verify** existing functionality wasn't broken
3. **Build** the executables: `python build/build.py`
4. **Test** the executables in a clean environment

## 📚 Documentation

When adding features:
- Update **README.md**
- Add usage examples
- Update **USER_GUIDE.md** if it affects operators
- Add docstrings in the code

## 🏗️ Project Structure

```
src/
├── core/       # Core logic
├── gui/        # Graphical interface
└── utils/      # Utilities

installer/      # Installation system
build/          # Build scripts
docs/           # Additional documentation
```

## 🔄 Review Process

Pull Requests go through:
1. **Code analysis** - Quality verification
2. **Tests** - Functionality and regression
3. **Documentation** - Clarity and completeness
4. **Build** - GitHub Actions must pass

## 💡 Tips

- Keep PRs **small and focused**
- **One feature per PR**
- **Update** your branch with `main` before PR
- **Respond** to review comments
- **Be patient** - reviews can take a few days

## 🎯 Contribution Areas

Looking for where to contribute?

- [ ] Automated tests (pytest)
- [ ] Linux/macOS support
- [ ] Web configuration interface
- [ ] Push notifications (Discord/Telegram)
- [ ] Statistics dashboard
- [ ] Performance improvements
- [ ] Translation to other languages

## ❓ Questions

- **Issues:** For bug and feature discussion
- **Discussions:** For general questions
- **Pull Requests:** For code and documentation

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** 🙏
