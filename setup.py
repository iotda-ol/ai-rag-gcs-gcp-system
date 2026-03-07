"""Package setup for the GCP Vertex AI RAG system."""

from setuptools import find_packages, setup

setup(
    name="ai-rag-gcs-gcp-system",
    version="0.1.0",
    description="GCP Vertex AI RAG system with GCS and Secret Manager",
    packages=find_packages(where=".", include=["src", "src.*"]),
    python_requires=">=3.11",
    install_requires=[
        "google-cloud-aiplatform[preview,rag]>=1.63.0",
        "google-cloud-storage>=2.16.0",
        "google-cloud-secret-manager>=2.20.0",
        "vertexai>=1.63.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=5.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "rag=src.main:main",
        ]
    },
)
