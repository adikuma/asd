import setuptools

setuptools.setup(
    name="git-asd",
    version="1.1.1",
    author="Aditya Kumar",
    description="a natural language git assistant for the terminal",
    url="https://github.com/adikuma/asd",
    packages=setuptools.find_packages(),
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.9",
    install_requires=[
        "langchain-core",
        "langchain-openai",
        "langchain-google-genai",
        "langgraph",
        "typer[all]",
        "rich",
        "rich-gradient",
        "ruff",
        "python-dotenv",
        "IPython",
        "questionary",
    ],
    entry_points={
        "console_scripts": [
            "asd=asd.cli:run",
        ],
    },
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
