"""Installation-independent packaging tests (M5).

Parse pyproject.toml and assert project metadata, scripts, extras, and build config.
These tests pass in CI with only pytest+httpx+fastapi+uvicorn installed and the
conftest sys.path hack — they do not require the package to be installed.
"""

import tomllib
from pathlib import Path

import pytest


@pytest.fixture
def pyproject_path():
    """Return the absolute path to pyproject.toml."""
    return Path(__file__).resolve().parent.parent / "pyproject.toml"


@pytest.fixture
def pyproject(pyproject_path):
    """Parse and return pyproject.toml as a dict."""
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------

def test_project_name(pyproject):
    """Project name is artisan-companion."""
    assert pyproject["project"]["name"] == "artisan-companion"


def test_project_version(pyproject):
    """Project version is 0.1.0."""
    assert pyproject["project"]["version"] == "0.1.0"


def test_project_description(pyproject):
    """Project has a description."""
    assert "description" in pyproject["project"]
    assert isinstance(pyproject["project"]["description"], str)
    assert len(pyproject["project"]["description"]) > 0


def test_project_readme(pyproject):
    """Project readme is README.md."""
    assert pyproject["project"]["readme"] == "README.md"


def test_project_requires_python(pyproject):
    """Project requires Python >= 3.11."""
    assert pyproject["project"]["requires-python"] == ">=3.11"


def test_project_authors(pyproject):
    """Project has authors list with gpotdevin."""
    authors = pyproject["project"]["authors"]
    assert isinstance(authors, list)
    assert len(authors) >= 1
    author_names = [a["name"] for a in authors]
    assert "gpotdevin" in author_names


def test_project_license(pyproject):
    """Project license is MIT."""
    license_info = pyproject["project"]["license"]
    assert isinstance(license_info, dict)
    assert license_info["text"] == "MIT"


def test_project_keywords(pyproject):
    """Project has keywords list."""
    keywords = pyproject["project"]["keywords"]
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    assert "coffee" in keywords
    assert "artisan" in keywords


def test_project_classifiers(pyproject):
    """Project has classifiers list with Python versions and MIT license."""
    classifiers = pyproject["project"]["classifiers"]
    assert isinstance(classifiers, list)
    assert len(classifiers) > 0
    # Check for MIT license classifier
    assert any("MIT License" in c for c in classifiers)
    # Check for Python 3.11+ classifiers
    assert any("Programming Language :: Python :: 3.11" in c for c in classifiers)
    assert any("Programming Language :: Python :: 3.12" in c for c in classifiers)
    assert any("Programming Language :: Python :: 3.13" in c for c in classifiers)


def test_project_urls(pyproject):
    """Project has Repository URL."""
    urls = pyproject["project"]["urls"]
    assert isinstance(urls, dict)
    assert "Repository" in urls
    assert "github.com/gpotdevin/artisan_companion_app" in urls["Repository"]


# ---------------------------------------------------------------------------
# Entry points / scripts
# ---------------------------------------------------------------------------

def test_project_scripts_artisan_companion(pyproject):
    """Console script artisan-companion maps to app.__main__:main."""
    scripts = pyproject["project"]["scripts"]
    assert isinstance(scripts, dict)
    assert "artisan-companion" in scripts
    assert scripts["artisan-companion"] == "app.__main__:main"


# ---------------------------------------------------------------------------
# Optional dependencies (extras)
# ---------------------------------------------------------------------------

def test_optional_dependencies_app(pyproject):
    """The app extra contains fastapi and uvicorn with minimum versions."""
    extras = pyproject["project"]["optional-dependencies"]
    assert "app" in extras
    app_deps = extras["app"]
    assert isinstance(app_deps, list)
    # Check for fastapi and uvicorn with version pins
    dep_strings = " ".join(app_deps)
    assert "fastapi>=0.100" in dep_strings
    assert "uvicorn>=0.20" in dep_strings


def test_optional_dependencies_dev(pyproject):
    """The dev extra contains pytest and httpx."""
    extras = pyproject["project"]["optional-dependencies"]
    assert "dev" in extras
    dev_deps = extras["dev"]
    assert isinstance(dev_deps, list)
    assert "pytest" in dev_deps
    assert "httpx" in dev_deps


# ---------------------------------------------------------------------------
# Build system / package discovery
# ---------------------------------------------------------------------------

def test_build_system_backend(pyproject):
    """Build backend is setuptools.build_meta."""
    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"


def test_build_system_requires(pyproject):
    """Build requires setuptools >= 68."""
    requires = pyproject["build-system"]["requires"]
    assert isinstance(requires, list)
    assert any("setuptools>=68" in r for r in requires)


def test_packages_find_where(pyproject):
    """Packages are found in the src directory."""
    packages_find = pyproject["tool"]["setuptools"]["packages"]["find"]
    assert isinstance(packages_find, dict)
    assert "where" in packages_find
    where = packages_find["where"]
    assert isinstance(where, list)
    assert "src" in where
