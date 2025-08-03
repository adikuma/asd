import setuptools

setuptools.setup(
    name="asd",
    version="1.0.0",
    author="Aditya Kumar",
    description="a natural language git assistant for the terminal",
    url="https://github.com/adikuma/asd",
    packages=setuptools.find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "langchain-core",
        "langchain-openai",
        "langgraph",
        "typer[all]",
        "rich",
        "python-dotenv",
        "IPython",
    ],
    entry_points={
        "console_scripts": [
            "asd=asd.cli:run",
        ],
    },
)
