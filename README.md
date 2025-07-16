# 🧪 Pytest Commands

## ▶️ Run Tests Normally

```sh
pytest
```

> Executes all automatically discovered tests (for example, files named test**.py) in**.

## 📁 Run tests from a specific folder

```sh
pytest <folder/>
```

> Runs all test files inside folder/.

## ✅ Run Tests with Coverage

```sh
pytest --cov=src tests/
```

> Runs all tests located in the `tests/` directory and collects code coverage on the `src/` directory.

## 📄 Generate an HTML Coverage Report

```sh
pytest --cov=src --cov-report html
```

> Runs tests and generates a visual HTML report (`htmlcov/index.html`) to explore coverage interactively in a browser.

## 📊 Show Coverage in Terminal (Verbose)

```sh
pytest --cov=src --cov-report=term-missing -v
```

> Displays a detailed coverage summary in the terminal, including which lines were missed (`term-missing`) and adds verbose test output (`-v`).
