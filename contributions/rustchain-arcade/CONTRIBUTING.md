# Contributing to RustChain Arcade

Thank you for your interest in contributing to RustChain Arcade! This guide will help you get started with contributing to this retro gaming + blockchain mining project.

## 🚀 Quick Start

1. **Fork the repository**
2. **Clone your fork**: `git clone https://github.com/YOUR_USERNAME/rustchain-arcade.git`
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Make your changes**
5. **Test your changes**
6. **Commit and push**: `git commit -m "feat: add your feature" && git push origin feature/your-feature-name`
7. **Open a Pull Request**

## 🛠️ Development Setup

### Prerequisites

- Python 3.10+
- Raspberry Pi (optional, for testing retro gaming features)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/Scottcjn/rustchain-arcade.git
cd rustchain-arcade

# Install dependencies
pip install -r requirements.txt

# Run the arcade miner
python arcade_miner.py
```

## 🎮 Project Overview

RustChain Arcade combines retro gaming with blockchain mining:
- Mine RTC tokens while playing retro games
- RetroAchievements integration
- Proof of Play mechanism
- Cartridge Relics collection
- Saturday Morning Quests

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=arcade_miner tests/
```

## 📝 Code Style

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write docstrings for public functions
- Keep functions focused and small

## 🐛 Reporting Issues

- Use the GitHub issue tracker
- Search for existing issues before creating a new one
- Provide clear reproduction steps
- Include expected vs actual behavior

## 💡 Feature Requests

- Open an issue with the "enhancement" label
- Describe the use case
- Explain why this feature would be useful

## 🔀 Pull Request Process

1. Ensure your PR description clearly describes the change
2. Reference any related issues
3. Make sure all tests pass
4. Update documentation if needed
5. Wait for review from maintainers

## 🏆 RetroAchievements Integration

When contributing to the RetroAchievements features:
- Test with actual retro games when possible
- Verify achievement unlocks are tracked correctly
- Ensure RTC rewards are calculated properly

## 📦 Cartridge Relics

For Cartridge Relics contributions:
- Document the rarity system
- Test relic generation
- Verify blockchain recording

## ❓ Questions?

- Open a discussion on GitHub
- Join the RustChain Discord: https://discord.gg/cafc4nDV

## 📜 Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all backgrounds and experience levels.

---

**Task Reference**: [#1605](https://github.com/Scottcjn/rustchain-bounties/issues/1605) - Add a CONTRIBUTING.md to any repo missing one

**Bounty**: 1 RTC
