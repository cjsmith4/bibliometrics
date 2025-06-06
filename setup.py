from pathlib import Path

from setuptools import find_namespace_packages, setup

# Load packages from requirements.txt
BASE_DIR = Path(__file__).parent
with open(Path(BASE_DIR, "requirements.txt")) as file:
    required_packages = [ln.strip() for ln in file.readlines()]

docs_packages = ["mkdocs==1.3.1", "mkdocstrings==0.18.1"]

style_packages = ["black==22.6.0", "flake8==5.0.2", "isort==5.10.1"]

dev_packages = ["mlflow", "pip-tools", "pandas"]

# Define our package
setup(
    name="bibliometrics_1",
    version=0.1,
    description="Publication metrics app",
    author="Caitlin Smith",
    author_email="caitlinjsmith@uabmc.edu",
    url="https://github.com/cjsmith4/bibliometrics",
    python_requires=">=3.7",
    packages=find_namespace_packages(),
    install_requires=[required_packages],
    extras_require={"dev": docs_packages + style_packages + dev_packages, "docs": docs_packages},
)
